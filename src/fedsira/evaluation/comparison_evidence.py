import hashlib

from fedsira.artifacts.paths import artifact_slot_directory, artifact_staging_root
from fedsira.artifacts.store import (
    ArtifactConfigurationComponent,
    ArtifactConfigurationScope,
    ArtifactDependency,
    ArtifactManifest,
    ArtifactReuseDecision,
    ArtifactSlot,
    configuration_scope_dependency,
    publish_artifact,
    read_current_artifact,
)
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactInstanceLabel,
    ArtifactProducer,
    ComparisonFamily,
    ExperimentName,
)
from fedsira.domain.types import (
    ArtifactDigest,
    ComparisonName,
    FailureMessage,
    FramingField,
    FrozenDomainModel,
    ProcedureIdentity,
    SchemaVersion,
)
from fedsira.evaluation.comparisons import (
    ComparisonDefinition,
    ComparisonFamilyResult,
    build_comparison_registry,
)
from fedsira.experiments.engine import PersistedExecutionRecord
from fedsira.runtime import current_application_context, framed_bytes

COMPARISON_EVIDENCE_SCHEMA_VERSION: SchemaVersion = "fedsira|comparison_evidence|2"
COMPARISON_EVIDENCE_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|statistical_comparison|2"


def _last_registered_definition(
    definitions: tuple[ComparisonDefinition, ...],
    comparison_name: ComparisonName,
) -> ComparisonDefinition | None:
    found: ComparisonDefinition | None = None
    for definition in definitions:
        if definition.comparison_name == comparison_name:
            found = definition
    return found


class PersistedComparisonEvidence(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    metric_evidence_digest: ArtifactDigest
    families: tuple[ComparisonFamilyResult, ...]


def metric_evidence_digest(
    records: tuple[PersistedExecutionRecord, ...],
) -> ArtifactDigest:
    fields: list[FramingField] = []
    for record in sorted(records, key=lambda item: item.semantic_key):
        fields.extend((record.semantic_key, record.terminal_state))
        if record.provenance is None:
            fields.extend(("", "", ""))
        else:
            fields.extend(
                (
                    record.provenance.configuration_digest,
                    record.provenance.dataset_manifest_hash,
                    record.provenance.code_revision or "",
                )
            )
        fields.extend(record.scoring_artifact_ids)
        for metric_name, metric_value in record.metrics:
            fields.extend(
                (
                    metric_name,
                    "" if metric_value is None else repr(metric_value),
                )
            )
    return hashlib.sha256(framed_bytes(*fields)).hexdigest()


def comparison_evidence_slot(experiment: ExperimentName) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        instance=ArtifactInstanceLabel.COMPARISONS,
        experiment=experiment,
    )


def _statistical_configuration_dependency() -> ArtifactDependency:
    scientific_config = current_application_context().scientific_config
    config = scientific_config.metrics_and_statistics
    return configuration_scope_dependency(
        ArtifactConfigurationScope(
            scope="statistical-analysis",
            components=(
                ArtifactConfigurationComponent(
                    name=ArtifactDependencyLabel.STATISTICAL_ANALYSIS,
                    configuration=(
                        f"{config.model_dump_json(exclude={'publication_rounding'})}"
                        f"\nanalysis_seed={scientific_config.seeds_and_determinism.analysis_seed}"
                    ),
                ),
            ),
        )
    )


def publish_comparison_evidence(
    experiment: ExperimentName,
    records: tuple[PersistedExecutionRecord, ...],
    families: tuple[ComparisonFamilyResult, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    payload = (
        PersistedComparisonEvidence(
            schema_version=COMPARISON_EVIDENCE_SCHEMA_VERSION,
            experiment=experiment,
            metric_evidence_digest=metric_evidence_digest(records),
            families=families,
        )
        .model_dump_json()
        .encode("utf-8")
    )
    slot = comparison_evidence_slot(experiment)
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.EVALUATION_PRODUCER,
        payload=payload,
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.METRIC_EVIDENCE,
                digest=metric_evidence_digest(records),
            ),
            _statistical_configuration_dependency(),
        ),
        procedure_identity=COMPARISON_EVIDENCE_PROCEDURE_IDENTITY,
        slot_directory=current_application_context().repository_root
        / artifact_slot_directory(slot),
        staging_root=current_application_context().repository_root / artifact_staging_root(),
    )


def current_comparison_evidence(
    experiment: ExperimentName,
    records: tuple[PersistedExecutionRecord, ...],
) -> tuple[ArtifactManifest, PersistedComparisonEvidence] | None:
    slot = comparison_evidence_slot(experiment)
    current = read_current_artifact(
        current_application_context().repository_root / artifact_slot_directory(slot)
    )
    if current is None:
        return None
    manifest, payload = current
    if _statistical_configuration_dependency() not in manifest.dependencies:
        return None
    evidence = PersistedComparisonEvidence.model_validate_json(payload)
    if (
        evidence.schema_version != COMPARISON_EVIDENCE_SCHEMA_VERSION
        or evidence.experiment != experiment
        or evidence.metric_evidence_digest != metric_evidence_digest(records)
    ):
        return None
    return manifest, evidence


def comparison_evidence_failures(
    experiment: ExperimentName,
    records: tuple[PersistedExecutionRecord, ...],
) -> tuple[FailureMessage, ...]:
    current = current_comparison_evidence(experiment, records)
    if current is not None:
        evidence = current[1]
        expected_definitions = tuple(
            definition
            for definition in build_comparison_registry()
            if definition.experiment == experiment
        )
        expected_families: list[ComparisonFamily] = []
        for definition in expected_definitions:
            if definition.family not in expected_families:
                expected_families.append(definition.family)
        actual_families = tuple(item.family for item in evidence.families)
        if len(actual_families) != len(set(actual_families)) or set(actual_families) != set(
            expected_families
        ):
            return (
                f"{experiment}: persisted comparison evidence does not contain "
                "the complete registered family set",
            )
        for family_result in evidence.families:
            expected = tuple(
                definition
                for definition in expected_definitions
                if definition.family is family_result.family
            )
            actual_names = tuple(
                result.definition.comparison_name for result in family_result.comparisons
            )
            expected_names = tuple(definition.comparison_name for definition in expected)
            if (
                len(actual_names) != len(set(actual_names))
                or set(actual_names) != set(expected_names)
                or any(
                    _last_registered_definition(expected, result.definition.comparison_name)
                    != result.definition
                    for result in family_result.comparisons
                )
            ):
                return (
                    f"{experiment}/{family_result.family}: persisted comparison evidence "
                    "does not match the complete registered comparison set",
                )
        return ()
    expected = any(
        definition.experiment == experiment for definition in build_comparison_registry()
    )
    if not expected:
        return ()
    slot = comparison_evidence_slot(experiment)
    existing = read_current_artifact(
        current_application_context().repository_root / artifact_slot_directory(slot)
    )
    if (
        existing is not None
        and _statistical_configuration_dependency() not in existing[0].dependencies
    ):
        return (f"{experiment}: persisted comparison evidence has stale statistical configuration",)
    if existing is None:
        return (f"{experiment}: required comparison evidence is missing",)

    return (f"{experiment}: persisted comparison evidence is stale for current execution records",)
