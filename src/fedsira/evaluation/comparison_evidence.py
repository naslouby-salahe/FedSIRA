import hashlib

from fedsira.artifacts.paths import artifact_slot_directory, artifact_staging_root
from fedsira.artifacts.store import (
    ArtifactDependency,
    ArtifactManifest,
    ArtifactReuseDecision,
    ArtifactSlot,
    publish_artifact,
    read_current_artifact,
)
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactInstanceLabel,
    ArtifactProducer,
    ExperimentName,
)
from fedsira.domain.types import (
    ArtifactDigest,
    FailureMessage,
    FramingField,
    FrozenDomainModel,
    ProcedureIdentity,
    SchemaVersion,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.experiments.engine import PersistedExecutionRecord
from fedsira.runtime import REPOSITORY_ROOT, framed_bytes

COMPARISON_EVIDENCE_SCHEMA_VERSION: SchemaVersion = "fedsira|comparison_evidence|1"
COMPARISON_EVIDENCE_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|statistical_comparison|1"


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
        ),
        procedure_identity=COMPARISON_EVIDENCE_PROCEDURE_IDENTITY,
        slot_directory=REPOSITORY_ROOT / artifact_slot_directory(slot),
        staging_root=REPOSITORY_ROOT / artifact_staging_root(),
    )


def read_comparison_evidence(experiment: ExperimentName) -> PersistedComparisonEvidence | None:
    slot = comparison_evidence_slot(experiment)
    current = read_current_artifact(REPOSITORY_ROOT / artifact_slot_directory(slot))
    if current is None:
        return None
    _manifest, payload = current
    return PersistedComparisonEvidence.model_validate_json(payload)


def comparison_evidence_failures(
    experiment: ExperimentName,
    records: tuple[PersistedExecutionRecord, ...],
) -> tuple[FailureMessage, ...]:
    evidence = read_comparison_evidence(experiment)
    if evidence is None:
        return ()
    observed = metric_evidence_digest(records)
    if evidence.metric_evidence_digest != observed:
        return (
            f"{experiment}: persisted comparison evidence is stale "
            f"({evidence.metric_evidence_digest} != {observed})",
        )
    return ()
