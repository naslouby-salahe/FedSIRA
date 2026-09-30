from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from io import StringIO
from pathlib import Path

from fedsira.artifacts.paths import (
    artifact_slot_directory,
    artifact_staging_root,
    current_repository_root,
    experiment_metric_evidence_root,
    experiment_metric_evidence_slot,
)
from fedsira.artifacts.store import (
    ArtifactDependency,
    ArtifactManifest,
    ArtifactReuseDecision,
    ArtifactSlot,
    publish_artifact,
    read_current_artifact,
)
from fedsira.domain.enums import (
    AdmissionState,
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactInstanceLabel,
    ArtifactLifecycleState,
    ArtifactProducer,
    ComparisonMetric,
    ExperimentName,
    FigureName,
    ReportColumnName,
    TableName,
)
from fedsira.domain.types import (
    ArtifactDigest,
    ArtifactPayloadBytes,
    BooleanValue,
    ByteCount,
    EvidenceCycleIndex,
    FrozenDomainModel,
    MethodName,
    MetricName,
    Probability,
    ProcedureIdentity,
    RelativePathText,
    ReportCellText,
    ReportEvidenceName,
    RepositoryPath,
    RowCount,
    ScenarioName,
    SchemaVersion,
    ScientificCellCount,
    ScientificCellSemanticKeyTuple,
)
from fedsira.evaluation.claim_support import ClaimDerivationInputs
from fedsira.evaluation.comparison_evidence import (
    COMPARISON_EVIDENCE_PROCEDURE_IDENTITY,
    COMPARISON_EVIDENCE_SCHEMA_VERSION,
    PersistedComparisonEvidence,
    comparison_evidence_slot,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.evaluation.summaries import ClaimSummary, claim_summary_from_inputs
from fedsira.experiments.definitions import (
    AGGREGATE_METRICS_PARQUET_NAME,
    EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME,
    SEED_METRICS_PARQUET_NAME,
    STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
    experiment_by_name,
)
from fedsira.reporting.aggregate import (
    AggregateMetricEvidenceRow,
    SeedMetricEvidenceRow,
    read_aggregate_metric_evidence,
    read_seed_metric_evidence,
)
from fedsira.reporting.state_trajectory import (
    EvidenceStateFraction,
    read_state_trajectory_fractions,
)
from fedsira.reporting.tables import (
    RenderedAggregateCellLineage,
    RenderedComparisonCellLineage,
    RenderedComparisonLineage,
    RenderedTable,
    comparison_source_semantic_keys,
    format_aggregate_statistic,
    format_comparison_displayed_value,
    render_statistical_summary_table,
)
from fedsira.runtime import current_application_context

PUBLICATION_SCHEMA_VERSION: SchemaVersion = "fedsira|publication|3"
TABLE_FIGURE_SOURCE_DATA_SCHEMA_VERSION: SchemaVersion = "fedsira|publication|9"
TABLE_FIGURE_SOURCE_DATA_PROCEDURE_IDENTITY: ProcedureIdentity = (
    "fedsira|table_figure_source_data|9"
)
TABLE_FIGURE_REPORT_EXPORT_PROCEDURE_IDENTITY: ProcedureIdentity = (
    "fedsira|table_figure_report_export|2"
)
METRIC_EVIDENCE_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|metric_evidence|5"
CLAIM_DECISION_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|claim_decision|2"


class ArtifactIdentityReference(FrozenDomainModel):
    slot: ArtifactSlot
    identity: ArtifactDigest


class ResolvedComparisonLineage(FrozenDomainModel):
    lineage: RenderedComparisonLineage
    source_artifact: ArtifactIdentityReference


class ResolvedAggregateCellLineage(FrozenDomainModel):
    lineage: RenderedAggregateCellLineage
    source_artifact: ArtifactIdentityReference
    configuration_digest: ArtifactDigest | None = None
    dataset_manifest_hash: ArtifactDigest | None = None


class ResolvedComparisonCellLineage(FrozenDomainModel):
    lineage: RenderedComparisonCellLineage
    source_artifact: ArtifactIdentityReference


class RenderedTableIdentity(FrozenDomainModel):
    table: TableName
    row_count: RowCount
    content_digest: ArtifactDigest
    comparison_lineage: tuple[ResolvedComparisonLineage, ...] = ()
    comparison_cell_lineage: tuple[ResolvedComparisonCellLineage, ...] = ()
    aggregate_lineage: tuple[ResolvedAggregateCellLineage, ...] = ()


class RenderedFigureIdentity(FrozenDomainModel):
    figure: FigureName
    content_bytes: ByteCount
    content_digest: ArtifactDigest
    point_lineage: tuple[RenderedFigurePointLineage, ...] = ()


class RenderedFigurePointLineage(FrozenDomainModel):
    experiment: ExperimentName
    source_artifact: ArtifactIdentityReference
    evidence_name: ReportEvidenceName
    evidence_digest: ArtifactDigest
    condition: ScenarioName
    cycle: EvidenceCycleIndex
    state: AdmissionState
    instance_count: ScientificCellCount
    instance_total: ScientificCellCount
    fraction: Probability
    source_cell_semantic_keys: ScientificCellSemanticKeyTuple


class ReportEvidenceIdentity(FrozenDomainModel):
    evidence_name: ReportEvidenceName
    content_digest: ArtifactDigest


ParsedCsvRows = tuple[list[ReportCellText], ...]


class TableFigureSourceDataPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName | None
    execution_digest: ArtifactDigest
    upstream_artifacts: tuple[ArtifactIdentityReference, ...]
    tables: tuple[RenderedTableIdentity, ...]
    figures: tuple[RenderedFigureIdentity, ...]
    evidence: tuple[ReportEvidenceIdentity, ...]
    verified_aggregate_metrics: tuple[AggregateMetricEvidenceRow, ...]
    verified_seed_metrics: tuple[SeedMetricEvidenceRow, ...]


class TableFigureExportPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName | None
    source_data_identity: ArtifactDigest
    exported_paths: tuple[RelativePathText, ...]


class MetricEvidenceIdentity(FrozenDomainModel):
    evidence_name: ReportEvidenceName
    content_bytes: ByteCount
    content_digest: ArtifactDigest


class MetricEvidencePayload(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    execution_digest: ArtifactDigest
    evidence: tuple[MetricEvidenceIdentity, ...]


class ClaimStateArtifactPayload(FrozenDomainModel):
    schema_version: SchemaVersion
    claim_inputs: ClaimDerivationInputs
    claim_summary: ClaimSummary


def claim_evidence_digest(inputs: ClaimDerivationInputs) -> ArtifactDigest:
    encoded = json.dumps(
        inputs.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _state_trajectory_point_lineage(
    state_trajectory: tuple[EvidenceStateFraction, ...],
    metric_artifacts: tuple[ArtifactIdentityReference, ...],
) -> tuple[RenderedFigurePointLineage, ...]:
    if not state_trajectory:
        return ()
    artifact_matches = tuple(
        (reference.slot.experiment, reference)
        for reference in metric_artifacts
        if reference.slot.experiment is not None
    )
    result: list[RenderedFigurePointLineage] = []
    evidence_digests: list[tuple[ExperimentName, ArtifactDigest]] = []
    for point in state_trajectory:
        if point.experiment is None or not point.source_cell_semantic_keys:
            raise ValueError("state-trajectory figure point is missing source-cell lineage")
        source_artifact: ArtifactIdentityReference | None = None
        for experiment_name, reference in artifact_matches:
            if experiment_name == point.experiment:
                source_artifact = reference
        if source_artifact is None:
            raise ValueError(
                f"state-trajectory point has no current metric artifact: {point.experiment}"
            )
        evidence_path = (
            experiment_metric_evidence_root(point.experiment)
            / STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME
        )
        if not evidence_path.is_file():
            raise ValueError(
                f"state-trajectory point source evidence is missing: {point.experiment}"
            )
        evidence_digest: ArtifactDigest | None = None
        for experiment_name, digest in evidence_digests:
            if experiment_name == point.experiment:
                evidence_digest = digest
        if evidence_digest is None:
            evidence_digest = content_digest(str(evidence_path))
            evidence_digests.append((point.experiment, evidence_digest))
        result.append(
            RenderedFigurePointLineage(
                experiment=point.experiment,
                source_artifact=source_artifact,
                evidence_name=STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
                evidence_digest=evidence_digest,
                condition=point.condition,
                cycle=point.cycle,
                state=point.state,
                instance_count=point.instance_count,
                instance_total=point.instance_total,
                fraction=point.fraction,
                source_cell_semantic_keys=point.source_cell_semantic_keys,
            )
        )
    return tuple(result)


def content_digest(path: RepositoryPath) -> ArtifactDigest:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def publish_metric_evidence(
    experiment: ExperimentName,
    execution_digest: ArtifactDigest,
    evidence_paths: tuple[RepositoryPath, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    evidence = tuple(
        MetricEvidenceIdentity(
            evidence_name=Path(path).name,
            content_bytes=Path(path).stat().st_size,
            content_digest=content_digest(path),
        )
        for path in evidence_paths
    )
    if not evidence or len({item.evidence_name for item in evidence}) != len(evidence):
        raise ValueError(f"{experiment}: metric evidence must be nonempty with unique filenames")
    payload = MetricEvidencePayload(
        schema_version=PUBLICATION_SCHEMA_VERSION,
        experiment=experiment,
        execution_digest=execution_digest,
        evidence=evidence,
    )
    slot = experiment_metric_evidence_slot(experiment)
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.EVALUATION_PRODUCER,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.EXECUTION_EVIDENCE,
                digest=execution_digest,
            ),
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=item.evidence_name,
                    digest=item.content_digest,
                )
                for item in evidence
            ),
        ),
        procedure_identity=METRIC_EVIDENCE_PROCEDURE_IDENTITY,
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )


def read_metric_evidence(
    experiment: ExperimentName,
) -> tuple[ArtifactManifest, MetricEvidencePayload] | None:
    slot = experiment_metric_evidence_slot(experiment)
    current = read_current_artifact(current_repository_root() / artifact_slot_directory(slot))
    if current is None:
        return None
    manifest, payload = current
    typed_payload = MetricEvidencePayload.model_validate_json(payload)
    if (
        manifest.family is not ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT
        or manifest.slot != slot
        or manifest.producer is not ArtifactProducer.EVALUATION_PRODUCER
        or manifest.procedure_identity != METRIC_EVIDENCE_PROCEDURE_IDENTITY
        or typed_payload.schema_version != PUBLICATION_SCHEMA_VERSION
        or typed_payload.experiment != experiment
    ):
        return None
    return manifest, typed_payload


def claim_state_artifact_slot() -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.CLAIM_STATE_ARTIFACT,
        instance=ArtifactInstanceLabel.CLAIM_DECISIONS,
    )


def _current_claim_upstream_manifests(
    published_manifests: tuple[ArtifactManifest, ...],
) -> tuple[ArtifactManifest, ...]:
    upstream_families: frozenset[ArtifactFamily] = frozenset(
        (
            ArtifactFamily.FINAL_GATE_DECISION,
            ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        )
    )
    candidate_slots: list[ArtifactSlot] = []
    for manifest in published_manifests:
        if manifest.family not in upstream_families:
            continue
        if not any(slot == manifest.slot for slot in candidate_slots):
            candidate_slots.append(manifest.slot)

    current_manifests: list[ArtifactManifest] = []
    for slot in candidate_slots:
        current = read_current_artifact(current_repository_root() / artifact_slot_directory(slot))
        if current is None:
            continue
        manifest, _payload = current
        if manifest.family in upstream_families:
            expected_producer = (
                ArtifactProducer.EVALUATION_PRODUCER
                if manifest.family is ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT
                else ArtifactProducer.FINAL_GATE_EVALUATOR
            )
            if manifest.producer is not expected_producer:
                raise ValueError(
                    f"{manifest.family.value} input has unexpected producer "
                    f"{manifest.producer.value}"
                )
            current_manifests.append(manifest)

    current_families: frozenset[ArtifactFamily] = frozenset(
        manifest.family for manifest in current_manifests
    )
    missing_families = tuple(
        family.value for family in sorted(upstream_families - current_families)
    )
    if missing_families:
        raise ValueError(
            "claim-state artifact requires current statistical and final-gate artifacts; "
            f"missing: {', '.join(missing_families)}"
        )

    current_manifests.sort(
        key=lambda manifest: (
            manifest.family.value,
            manifest.slot.experiment or "",
            manifest.slot.instance,
        )
    )
    return tuple(current_manifests)


def publish_claim_state_artifact(
    inputs: ClaimDerivationInputs,
    published_manifests: tuple[ArtifactManifest, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    current_manifests = _current_claim_upstream_manifests(published_manifests)
    payload = ClaimStateArtifactPayload(
        schema_version=PUBLICATION_SCHEMA_VERSION,
        claim_inputs=inputs,
        claim_summary=claim_summary_from_inputs(inputs),
    )
    payload_bytes = payload.model_dump_json().encode("utf-8")
    slot = claim_state_artifact_slot()
    dependencies = (
        ArtifactDependency(
            kind=ArtifactDependencyKind.ARTIFACT,
            dependency=(
                f"{ArtifactDependencyLabel.STATISTICAL_ARTIFACT}:"
                f"{manifest.slot.experiment or 'project'}:{manifest.slot.instance}"
            )
            if manifest.family is ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT
            else (
                f"{ArtifactDependencyLabel.GATE_ARTIFACT}:"
                f"{manifest.slot.experiment or 'project'}:{manifest.slot.instance}"
            ),
            digest=manifest.identity,
        )
        for manifest in current_manifests
    )
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.CLAIM_DECISION,
        payload=payload_bytes,
        dependencies=(
            *dependencies,
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.CLAIM_EVIDENCE,
                digest=claim_evidence_digest(inputs),
            ),
        ),
        procedure_identity=CLAIM_DECISION_PROCEDURE_IDENTITY,
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )


def read_claim_state_artifact(
    published_manifests: tuple[ArtifactManifest, ...],
) -> tuple[ArtifactManifest, ClaimStateArtifactPayload] | None:
    slot = claim_state_artifact_slot()
    current = read_current_artifact(current_repository_root() / artifact_slot_directory(slot))
    if current is None:
        return None
    manifest, payload = current
    if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        return None
    current_upstream = _current_claim_upstream_manifests(published_manifests)
    upstream_identities = frozenset(item.identity for item in current_upstream)
    recorded_identities = frozenset(
        item.digest
        for item in manifest.dependencies
        if item.kind is ArtifactDependencyKind.ARTIFACT
    )
    typed_payload = ClaimStateArtifactPayload.model_validate_json(payload)
    recorded_payload_digests = frozenset(
        item.digest
        for item in manifest.dependencies
        if item.dependency == ArtifactDependencyLabel.CLAIM_EVIDENCE
        and item.kind is ArtifactDependencyKind.CONTENT
    )
    if (
        manifest.procedure_identity != CLAIM_DECISION_PROCEDURE_IDENTITY
        or manifest.producer is not ArtifactProducer.CLAIM_DECISION
        or typed_payload.schema_version != PUBLICATION_SCHEMA_VERSION
        or recorded_identities != upstream_identities
        or recorded_payload_digests
        != frozenset((claim_evidence_digest(typed_payload.claim_inputs),))
        or typed_payload.claim_summary != claim_summary_from_inputs(typed_payload.claim_inputs)
    ):
        return None
    return manifest, typed_payload


def table_figure_source_data_slot(experiment: ExperimentName | None) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.TABLE_FIGURE_SOURCE_DATA,
        instance=ArtifactInstanceLabel.SOURCE_DATA,
        experiment=experiment,
    )


def table_figure_export_slot(experiment: ExperimentName | None) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT,
        instance=ArtifactInstanceLabel.REPORT_EXPORT,
        experiment=experiment,
    )


def publish_table_figure_source_data(
    experiment: ExperimentName,
    execution_digest: ArtifactDigest,
    metric_evidence_identity: ArtifactDigest,
    tables: tuple[RenderedTable, ...],
    figure_paths: tuple[RepositoryPath, ...],
    table_paths: tuple[RepositoryPath, ...],
    evidence_paths: tuple[RepositoryPath, ...],
    comparison_artifact_identity: ArtifactDigest | None = None,
    state_trajectory: tuple[EvidenceStateFraction, ...] = (),
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    evidence = tuple(
        ReportEvidenceIdentity(
            evidence_name=Path(path).name,
            content_digest=content_digest(path),
        )
        for path in evidence_paths
    )
    metric_payload = _verified_metric_evidence_payload(experiment, metric_evidence_identity)
    evidence_root = experiment_metric_evidence_root(experiment)
    aggregate_evidence, seed_evidence = _verified_metric_sources(
        experiment,
        metric_payload,
        evidence_root / AGGREGATE_METRICS_PARQUET_NAME,
        evidence_root / SEED_METRICS_PARQUET_NAME,
    )
    comparison_manifest = _current_comparison_manifest(
        experiment,
        comparison_artifact_identity,
        any(table.comparison_lineage or table.comparison_cell_lineage for table in tables),
    )
    metric_artifact_references = (
        ArtifactIdentityReference(
            slot=experiment_metric_evidence_slot(experiment),
            identity=metric_evidence_identity,
        ),
    )
    table_identities = tuple(
        _rendered_table_identity(
            table,
            path,
            (comparison_manifest,) if comparison_manifest is not None else (),
            aggregate_evidence,
            seed_evidence,
            metric_artifact_references,
        )
        for table, path in zip(tables, table_paths, strict=True)
    )
    comparison_references = (
        ()
        if comparison_manifest is None
        else (
            ArtifactIdentityReference(
                slot=comparison_manifest.slot,
                identity=comparison_manifest.identity,
            ),
        )
    )
    trajectory_lineage = _state_trajectory_point_lineage(
        state_trajectory,
        metric_artifact_references,
    )
    if (
        any(
            FigureName(Path(path).stem) == EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME
            for path in figure_paths
        )
        and not trajectory_lineage
    ):
        raise ValueError("Evidence-Arrival State Trajectory requires point-level source lineage")
    comparison_dependencies = (
        ()
        if comparison_manifest is None
        else (
            ArtifactDependency(
                kind=ArtifactDependencyKind.ARTIFACT,
                dependency=(
                    f"{ArtifactDependencyLabel.STATISTICAL_ARTIFACT}:"
                    f"{comparison_manifest.slot.experiment}:"
                    f"{comparison_manifest.slot.instance}"
                ),
                digest=comparison_manifest.identity,
            ),
        )
    )
    payload = TableFigureSourceDataPayload(
        schema_version=TABLE_FIGURE_SOURCE_DATA_SCHEMA_VERSION,
        experiment=experiment,
        execution_digest=execution_digest,
        upstream_artifacts=(
            ArtifactIdentityReference(
                slot=experiment_metric_evidence_slot(experiment),
                identity=metric_evidence_identity,
            ),
            *comparison_references,
        ),
        tables=table_identities,
        figures=tuple(
            RenderedFigureIdentity(
                figure=FigureName(Path(path).stem),
                content_bytes=Path(path).stat().st_size,
                content_digest=content_digest(path),
                point_lineage=(
                    trajectory_lineage
                    if FigureName(Path(path).stem) == EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME
                    else ()
                ),
            )
            for path in figure_paths
        ),
        evidence=evidence,
        verified_aggregate_metrics=aggregate_evidence,
        verified_seed_metrics=seed_evidence,
    )
    slot = table_figure_source_data_slot(experiment)
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.REPORTING_SOURCE_DATA,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.EXECUTION_EVIDENCE,
                digest=execution_digest,
            ),
            ArtifactDependency(
                kind=ArtifactDependencyKind.ARTIFACT,
                dependency=ArtifactDependencyLabel.METRIC_EVIDENCE,
                digest=metric_evidence_identity,
            ),
            *comparison_dependencies,
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=item.evidence_name,
                    digest=item.content_digest,
                )
                for item in evidence
            ),
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=f"table-render:{item.table}",
                    digest=item.content_digest,
                )
                for item in payload.tables
            ),
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=f"figure-render:{item.figure}",
                    digest=item.content_digest,
                )
                for item in payload.figures
            ),
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=f"state-trajectory:{item.experiment}",
                    digest=item.evidence_digest,
                )
                for item in trajectory_lineage
            ),
        ),
        procedure_identity=TABLE_FIGURE_SOURCE_DATA_PROCEDURE_IDENTITY,
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )


def publish_project_table_figure_source_data(
    execution_digest: ArtifactDigest,
    upstream_manifests: tuple[ArtifactManifest, ...],
    tables: tuple[RenderedTable, ...],
    figure_paths: tuple[RepositoryPath, ...],
    table_paths: tuple[RepositoryPath, ...],
    state_trajectory: tuple[EvidenceStateFraction, ...] = (),
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    if not upstream_manifests:
        raise ValueError("project report source data requires upstream artifacts")
    if len({manifest.identity for manifest in upstream_manifests}) != len(upstream_manifests):
        raise ValueError("project report source data upstream identities must be unique")
    metric_sources = tuple(
        (
            manifest.slot.experiment,
            *_current_metric_sources(manifest.slot.experiment, manifest.identity),
        )
        for manifest in upstream_manifests
        if manifest.family is ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT
        and manifest.slot.experiment is not None
    )
    aggregate_evidence = tuple(
        row for _experiment, aggregates, _seeds in metric_sources for row in aggregates
    )
    seed_evidence = tuple(
        row for _experiment, _aggregates, seeds in metric_sources for row in seeds
    )
    if not aggregate_evidence or not seed_evidence:
        raise ValueError("project report source data requires canonical aggregate metric lineage")
    comparison_manifests = tuple(
        manifest
        for manifest in upstream_manifests
        if manifest.family is ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT
    )
    metric_artifact_references = tuple(
        ArtifactIdentityReference(slot=manifest.slot, identity=manifest.identity)
        for manifest in upstream_manifests
        if manifest.family is ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT
        and manifest.slot.experiment is not None
    )
    table_identities = tuple(
        _rendered_table_identity(
            table,
            path,
            comparison_manifests,
            aggregate_evidence,
            seed_evidence,
            metric_artifact_references,
        )
        for table, path in zip(tables, table_paths, strict=True)
    )
    upstream_artifacts = tuple(
        ArtifactIdentityReference(slot=manifest.slot, identity=manifest.identity)
        for manifest in sorted(
            upstream_manifests,
            key=lambda item: (
                item.family.value,
                item.slot.experiment or "",
                item.slot.instance,
            ),
        )
    )
    trajectory_lineage = _state_trajectory_point_lineage(
        state_trajectory,
        metric_artifact_references,
    )
    if (
        any(
            FigureName(Path(path).stem) == EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME
            for path in figure_paths
        )
        and not trajectory_lineage
    ):
        raise ValueError("Evidence-Arrival State Trajectory requires point-level source lineage")
    payload = TableFigureSourceDataPayload(
        schema_version=TABLE_FIGURE_SOURCE_DATA_SCHEMA_VERSION,
        experiment=None,
        execution_digest=execution_digest,
        upstream_artifacts=upstream_artifacts,
        tables=table_identities,
        figures=tuple(
            RenderedFigureIdentity(
                figure=FigureName(Path(path).stem),
                content_bytes=Path(path).stat().st_size,
                content_digest=content_digest(path),
                point_lineage=(
                    trajectory_lineage
                    if FigureName(Path(path).stem) == EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME
                    else ()
                ),
            )
            for path in figure_paths
        ),
        evidence=(),
        verified_aggregate_metrics=aggregate_evidence,
        verified_seed_metrics=seed_evidence,
    )
    slot = table_figure_source_data_slot(None)
    dependencies = tuple(
        ArtifactDependency(
            kind=ArtifactDependencyKind.ARTIFACT,
            dependency=(
                f"{manifest.family.value}:{manifest.slot.experiment or 'project'}:"
                f"{manifest.slot.instance}"
            ),
            digest=manifest.identity,
        )
        for manifest in upstream_manifests
    )
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.REPORTING_SOURCE_DATA,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.EXECUTION_EVIDENCE,
                digest=execution_digest,
            ),
            *dependencies,
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=f"table-render:{item.table}",
                    digest=item.content_digest,
                )
                for item in payload.tables
            ),
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=f"figure-render:{item.figure}",
                    digest=item.content_digest,
                )
                for item in payload.figures
            ),
            *(
                ArtifactDependency(
                    kind=ArtifactDependencyKind.CONTENT,
                    dependency=f"state-trajectory:{item.experiment}",
                    digest=item.evidence_digest,
                )
                for item in trajectory_lineage
            ),
        ),
        procedure_identity=TABLE_FIGURE_SOURCE_DATA_PROCEDURE_IDENTITY,
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )


def _verified_metric_evidence_payload(
    experiment: ExperimentName,
    expected_identity: ArtifactDigest,
) -> MetricEvidencePayload:
    current = read_metric_evidence(experiment)
    if current is None or current[0].identity != expected_identity:
        raise ValueError(f"{experiment}: current metric evidence identity is unavailable")
    return current[1]


def _current_comparison_manifest(
    experiment: ExperimentName,
    expected_identity: ArtifactDigest | None,
    has_comparison_lineage: BooleanValue,
) -> ArtifactManifest | None:
    if not has_comparison_lineage:
        return None
    if expected_identity is None:
        raise ValueError(f"{experiment}: statistical table lineage requires a comparison artifact")
    slot = comparison_evidence_slot(experiment)
    current = read_current_artifact(current_repository_root() / artifact_slot_directory(slot))
    if current is None or current[0].identity != expected_identity:
        raise ValueError(f"{experiment}: current comparison artifact identity is unavailable")
    manifest, payload = current
    _validate_comparison_manifest(manifest, payload, experiment)
    return manifest


def _validate_comparison_manifest(
    manifest: ArtifactManifest,
    payload: ArtifactPayloadBytes,
    experiment: ExperimentName,
) -> PersistedComparisonEvidence:
    expected_slot = comparison_evidence_slot(experiment)
    if (
        manifest.family is not ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT
        or manifest.slot != expected_slot
        or manifest.producer is not ArtifactProducer.EVALUATION_PRODUCER
        or manifest.procedure_identity != COMPARISON_EVIDENCE_PROCEDURE_IDENTITY
    ):
        raise ValueError(f"{experiment}: comparison artifact has a stale or unexpected identity")
    evidence = PersistedComparisonEvidence.model_validate_json(payload)
    if (
        evidence.schema_version != COMPARISON_EVIDENCE_SCHEMA_VERSION
        or evidence.experiment != experiment
    ):
        raise ValueError(f"{experiment}: comparison artifact payload is stale")
    return evidence


def _rendered_table_identity(
    table: RenderedTable,
    path: RepositoryPath,
    comparison_manifests: tuple[ArtifactManifest, ...],
    aggregate_evidence: tuple[AggregateMetricEvidenceRow, ...],
    seed_evidence: tuple[SeedMetricEvidenceRow, ...],
    metric_artifact_references: tuple[ArtifactIdentityReference, ...],
) -> RenderedTableIdentity:
    parsed_rows = tuple(csv.reader(StringIO(table.csv_text)))
    if (
        table.comparison_lineage or table.comparison_cell_lineage or table.aggregate_lineage
    ) and not parsed_rows:
        raise ValueError(f"{table.name}: numeric lineage has no rendered table")
    resolved_aggregates = _resolve_aggregate_lineage(
        table,
        parsed_rows,
        aggregate_evidence,
        seed_evidence,
        metric_artifact_references,
    )
    resolved = _resolve_comparison_lineage(table, parsed_rows, comparison_manifests)
    resolved_cells = _resolve_comparison_cell_lineage(table, parsed_rows, comparison_manifests)
    return RenderedTableIdentity(
        table=table.name,
        row_count=_table_row_count(table),
        content_digest=content_digest(path),
        comparison_lineage=tuple(resolved),
        comparison_cell_lineage=tuple(resolved_cells),
        aggregate_lineage=tuple(resolved_aggregates),
    )


def _seed_provenance(
    table_name: TableName,
    lineage: RenderedAggregateCellLineage,
    seed_evidence: tuple[SeedMetricEvidenceRow, ...],
) -> tuple[ArtifactDigest | None, ArtifactDigest | None]:
    matches = tuple(
        seed
        for seed in seed_evidence
        if (
            seed.experiment == lineage.experiment
            and seed.method == lineage.method
            and seed.condition == lineage.scenario
            and seed.metric == lineage.metric
        )
    )
    if not matches:
        return None, None
    configuration_digests = {seed.configuration_digest for seed in matches}
    manifest_hashes = {seed.dataset_manifest_hash for seed in matches}
    if len(configuration_digests) != 1 or len(manifest_hashes) != 1:
        raise ValueError(f"{table_name}: aggregate seed provenance is not unique")
    return next(iter(configuration_digests)), next(iter(manifest_hashes))


def _resolve_aggregate_lineage(
    table: RenderedTable,
    parsed_rows: ParsedCsvRows,
    aggregate_evidence: tuple[AggregateMetricEvidenceRow, ...],
    seed_evidence: tuple[SeedMetricEvidenceRow, ...],
    metric_artifact_references: tuple[ArtifactIdentityReference, ...],
) -> tuple[ResolvedAggregateCellLineage, ...]:
    if not table.aggregate_lineage:
        return ()
    header, *body = parsed_rows
    lineage_experiments = {item.experiment for item in table.aggregate_lineage}
    experiment_columns = (ReportColumnName.EXPERIMENT, ReportColumnName.BOUNDARY_FAMILY)
    if len(lineage_experiments) > 1 and not any(column in header for column in experiment_columns):
        raise ValueError(
            f"{table.name}: cross-experiment aggregate lineage has no experiment identity column"
        )
    seen_cells: set[tuple[RowCount, ReportColumnName | ComparisonMetric]] = set()
    resolved: list[ResolvedAggregateCellLineage] = []
    for lineage in table.aggregate_lineage:
        cell_key = (lineage.row_index, lineage.source_column)
        if cell_key in seen_cells or lineage.row_index >= len(body):
            raise ValueError(f"{table.name}: aggregate lineage cell identity is invalid")
        seen_cells.add(cell_key)
        row = body[lineage.row_index]
        if len(row) != len(header):
            raise ValueError(f"{table.name}: rendered row width does not match its header")
        definition = experiment_by_name(lineage.experiment)
        method_columns = (
            ReportColumnName.METHOD,
            ReportColumnName.VARIANT,
            ReportColumnName.TARGETED_MECHANISM,
        )
        method_column = next(
            (header.index(item) for item in method_columns if item in header), None
        )
        scenario_columns = (ReportColumnName.SCENARIO, ReportColumnName.CONDITION)
        scenario_column = next(
            (header.index(item) for item in scenario_columns if item in header), None
        )
        experiment_columns = (ReportColumnName.EXPERIMENT, ReportColumnName.BOUNDARY_FAMILY)
        experiment_column = next(
            (header.index(item) for item in experiment_columns if item in header), None
        )
        try:
            value_column = header.index(lineage.source_column)
        except ValueError as error:
            raise ValueError(f"{table.name}: aggregate lineage source column is absent") from error
        if method_column is None or row[method_column] != lineage.method:
            raise ValueError(f"{table.name}: aggregate method identity does not match lineage")
        if (
            lineage.method not in definition.methods
            or lineage.scenario not in definition.conditions
        ):
            raise ValueError(f"{table.name}: aggregate identity is outside its registered design")
        if scenario_column is not None and row[scenario_column] != lineage.scenario:
            raise ValueError(f"{table.name}: aggregate scenario identity does not match lineage")
        if scenario_column is None and len(definition.conditions) != 1:
            raise ValueError(f"{table.name}: aggregate scenario identity is not rendered")
        if experiment_column is not None and row[experiment_column] != lineage.experiment:
            raise ValueError(f"{table.name}: aggregate row identity does not match lineage")
        aggregates = tuple(
            item
            for item in aggregate_evidence
            if (
                item.experiment == lineage.experiment
                and item.method == lineage.method
                and item.condition == lineage.scenario
                and item.metric == lineage.metric
            )
        )
        if len(aggregates) > 1:
            raise ValueError(f"{table.name}: aggregate source row is not unique")
        references = tuple(
            item
            for item in metric_artifact_references
            if item.slot.experiment == lineage.experiment
        )
        if len(references) != 1:
            raise ValueError(f"{table.name}: expected one metric artifact for {lineage.experiment}")
        expected_value = format_aggregate_statistic(
            aggregates[0] if aggregates else None,
            lineage.statistic,
            lineage.metric,
        )
        if row[value_column] != expected_value:
            raise ValueError(
                f"{table.name}: rendered aggregate value does not match canonical evidence"
            )
        configuration_digest, dataset_manifest_hash = _seed_provenance(
            table.name,
            lineage,
            seed_evidence,
        )
        resolved.append(
            ResolvedAggregateCellLineage(
                lineage=lineage,
                source_artifact=references[0],
                configuration_digest=configuration_digest,
                dataset_manifest_hash=dataset_manifest_hash,
            )
        )
    return tuple(resolved)


def _resolve_comparison_lineage(
    table: RenderedTable,
    parsed_rows: ParsedCsvRows,
    comparison_manifests: tuple[ArtifactManifest, ...],
) -> tuple[ResolvedComparisonLineage, ...]:
    if not table.comparison_lineage:
        return ()
    header, *body = parsed_rows
    seen_rows: set[RowCount] = set()
    resolved: list[ResolvedComparisonLineage] = []
    for lineage in table.comparison_lineage:
        if lineage.row_index >= len(body) or lineage.row_index in seen_rows:
            raise ValueError(f"{table.name}: comparison lineage row index is invalid")
        seen_rows.add(lineage.row_index)
        if not lineage.source_columns or any(
            column not in header for column in lineage.source_columns
        ):
            raise ValueError(f"{table.name}: comparison lineage names an absent table column")
        row = body[lineage.row_index]
        if len(row) != len(header):
            raise ValueError(f"{table.name}: rendered row width does not match its header")
        if (
            row[header.index(ReportColumnName.COMPARISON_FAMILY)] != lineage.family
            or row[header.index(ReportColumnName.METRIC)] != lineage.metric
        ):
            raise ValueError(f"{table.name}: rendered comparison identity does not match lineage")
        matches = tuple(
            manifest
            for manifest in comparison_manifests
            if manifest.slot.experiment == lineage.experiment
        )
        if len(matches) != 1:
            raise ValueError(
                f"{table.name}: expected one current comparison artifact for "
                f"{lineage.experiment}, found {len(matches)}"
            )
        manifest = matches[0]
        current = read_current_artifact(
            current_repository_root() / artifact_slot_directory(manifest.slot)
        )
        if current is None or current[0].identity != manifest.identity:
            raise ValueError(f"{table.name}: comparison artifact is no longer current")
        evidence = _validate_comparison_manifest(current[0], current[1], lineage.experiment)
        matches_in_evidence = tuple(
            comparison
            for family in evidence.families
            if family.family is lineage.family
            for comparison in family.comparisons
            if (
                comparison.definition.comparison_name == lineage.comparison_name
                and comparison.definition.method == lineage.method
                and comparison.definition.scientific_scenario == lineage.scenario
                and comparison.definition.metric == lineage.metric
            )
        )
        if len(matches_in_evidence) != 1:
            raise ValueError(f"{table.name}: comparison row has no unique source result")
        source = matches_in_evidence[0]
        if (
            source.paired_master_seeds != lineage.paired_master_seeds
            or comparison_source_semantic_keys(source) != lineage.source_cell_semantic_keys
        ):
            raise ValueError(f"{table.name}: comparison row seed lineage is inconsistent")
        expected_table = render_statistical_summary_table(
            (ComparisonFamilyResult(family=lineage.family, comparisons=(source,)),)
        )
        expected_header, expected_row = tuple(csv.reader(StringIO(expected_table.csv_text)))
        if expected_header != header or row != expected_row:
            raise ValueError(
                f"{table.name}: rendered comparison values do not match current evidence"
            )
        resolved.append(
            ResolvedComparisonLineage(
                lineage=lineage,
                source_artifact=ArtifactIdentityReference(
                    slot=manifest.slot,
                    identity=manifest.identity,
                ),
            )
        )
    if seen_rows != set(range(len(body))):
        raise ValueError(f"{table.name}: not every rendered comparison row has lineage")
    return tuple(resolved)


def _resolve_comparison_cell_lineage(
    table: RenderedTable,
    parsed_rows: ParsedCsvRows,
    comparison_manifests: tuple[ArtifactManifest, ...],
) -> tuple[ResolvedComparisonCellLineage, ...]:
    if not table.comparison_cell_lineage:
        return ()
    header, *body = parsed_rows
    seen_cells: set[tuple[RowCount, ReportColumnName]] = set()
    resolved: list[ResolvedComparisonCellLineage] = []
    for lineage in table.comparison_cell_lineage:
        cell_key = (lineage.row_index, lineage.source_column)
        if cell_key in seen_cells or lineage.row_index >= len(body):
            raise ValueError(f"{table.name}: comparison cell lineage identity is invalid")
        seen_cells.add(cell_key)
        row = body[lineage.row_index]
        if len(row) != len(header):
            raise ValueError(f"{table.name}: rendered row width does not match its header")
        try:
            value_column = header.index(lineage.source_column)
        except ValueError as error:
            raise ValueError(f"{table.name}: comparison cell lineage column is absent") from error
        matches = tuple(
            manifest
            for manifest in comparison_manifests
            if manifest.slot.experiment == lineage.experiment
        )
        if len(matches) != 1:
            raise ValueError(
                f"{table.name}: expected one current comparison artifact for {lineage.experiment}"
            )
        manifest = matches[0]
        current = read_current_artifact(
            current_repository_root() / artifact_slot_directory(manifest.slot)
        )
        if current is None or current[0].identity != manifest.identity:
            raise ValueError(f"{table.name}: comparison artifact is no longer current")
        evidence = _validate_comparison_manifest(current[0], current[1], lineage.experiment)
        matches_in_evidence = tuple(
            comparison
            for family in evidence.families
            if family.family is lineage.family
            for comparison in family.comparisons
            if (
                comparison.definition.comparison_name == lineage.comparison_name
                and comparison.definition.method == lineage.method
                and comparison.definition.scientific_scenario == lineage.scenario
                and comparison.definition.metric == lineage.metric
            )
        )
        if len(matches_in_evidence) != 1:
            raise ValueError(f"{table.name}: comparison cell has no unique source result")
        expected_value = format_comparison_displayed_value(
            matches_in_evidence[0],
            lineage.displayed_value,
        )
        if row[value_column] != expected_value:
            raise ValueError(
                f"{table.name}: rendered comparison cell does not match current evidence"
            )
        resolved.append(
            ResolvedComparisonCellLineage(
                lineage=lineage,
                source_artifact=ArtifactIdentityReference(
                    slot=manifest.slot,
                    identity=manifest.identity,
                ),
            )
        )
    return tuple(resolved)


def _current_metric_sources(
    experiment: ExperimentName,
    expected_identity: ArtifactDigest,
) -> tuple[tuple[AggregateMetricEvidenceRow, ...], tuple[SeedMetricEvidenceRow, ...]]:
    payload = _verified_metric_evidence_payload(experiment, expected_identity)
    root = experiment_metric_evidence_root(experiment)
    return _verified_metric_sources(
        experiment,
        payload,
        root / AGGREGATE_METRICS_PARQUET_NAME,
        root / SEED_METRICS_PARQUET_NAME,
    )


def _verified_metric_sources(
    experiment: ExperimentName,
    payload: MetricEvidencePayload,
    aggregate_path: Path,
    seed_path: Path,
) -> tuple[tuple[AggregateMetricEvidenceRow, ...], tuple[SeedMetricEvidenceRow, ...]]:
    _read_registered_metric_file(
        experiment, payload, AGGREGATE_METRICS_PARQUET_NAME, aggregate_path
    )
    _read_registered_metric_file(experiment, payload, SEED_METRICS_PARQUET_NAME, seed_path)
    aggregates = read_aggregate_metric_evidence(aggregate_path, experiment)
    seeds = read_seed_metric_evidence(seed_path, experiment)
    if not aggregates:
        raise ValueError(f"{experiment}: aggregate metric evidence has no canonical rows")
    if not seeds:
        raise ValueError(f"{experiment}: seed metric evidence has no canonical rows")
    _validate_aggregate_seed_lineage(experiment, aggregates, seeds)
    return aggregates, seeds


def _read_registered_metric_file(
    experiment: ExperimentName,
    payload: MetricEvidencePayload,
    evidence_name: ReportEvidenceName,
    path: Path,
) -> None:
    registered = tuple(item for item in payload.evidence if item.evidence_name == evidence_name)
    if len(registered) != 1:
        raise ValueError(f"{experiment}: {evidence_name} is not uniquely registered")
    evidence = registered[0]
    if (
        not path.is_file()
        or path.stat().st_size != evidence.content_bytes
        or content_digest(str(path)) != evidence.content_digest
    ):
        raise ValueError(f"{experiment}: {evidence_name} is missing or stale")


def _validate_aggregate_seed_lineage(
    experiment: ExperimentName,
    aggregates: tuple[AggregateMetricEvidenceRow, ...],
    seeds: tuple[SeedMetricEvidenceRow, ...],
) -> None:
    aggregate_keys = tuple(
        (row.experiment, row.method, row.condition, row.metric) for row in aggregates
    )
    seeds_by_key: defaultdict[
        tuple[ExperimentName, MethodName, ScenarioName, MetricName],
        list[SeedMetricEvidenceRow],
    ] = defaultdict(list)
    for row in seeds:
        seeds_by_key[(row.experiment, row.method, row.condition, row.metric)].append(row)
    if (
        len(set(aggregate_keys)) != len(aggregate_keys)
        or frozenset(aggregate_keys) != frozenset(seeds_by_key)
        or len(seeds_by_key) != len(seeds)
    ):
        raise ValueError(f"{experiment}: aggregate and seed metric identities do not match")

    for aggregate in aggregates:
        key = (aggregate.experiment, aggregate.method, aggregate.condition, aggregate.metric)
        matching = tuple(seeds_by_key[key])
        if (
            len(matching) != aggregate.seed_count
            or sum(len(row.source_observation_ids) for row in matching)
            != aggregate.observation_count
            or Counter(source_id for row in matching for source_id in row.source_observation_ids)
            != Counter(aggregate.source_observation_ids)
            or Counter(cell_key for row in matching for cell_key in row.source_cell_semantic_keys)
            != Counter(aggregate.source_cell_semantic_keys)
        ):
            raise ValueError(
                f"{experiment}/{aggregate.method}/{aggregate.condition}/{aggregate.metric}: "
                "aggregate-to-seed source lineage does not match"
            )


def publish_table_figure_export(
    experiment: ExperimentName | None,
    source_data_identity: ArtifactDigest,
    experiment_root: Path,
    exported_paths: tuple[RepositoryPath, ...],
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    payload = TableFigureExportPayload(
        schema_version=PUBLICATION_SCHEMA_VERSION,
        experiment=experiment,
        source_data_identity=source_data_identity,
        exported_paths=tuple(
            Path(path).relative_to(experiment_root).as_posix() for path in exported_paths
        ),
    )
    slot = table_figure_export_slot(experiment)
    return publish_artifact(
        slot=slot,
        producer=ArtifactProducer.REPORT_EXPORT,
        payload=payload.model_dump_json().encode("utf-8"),
        dependencies=(
            ArtifactDependency(
                kind=ArtifactDependencyKind.ARTIFACT,
                dependency=ArtifactDependencyLabel.SOURCE_DATA,
                digest=source_data_identity,
            ),
        ),
        procedure_identity=TABLE_FIGURE_REPORT_EXPORT_PROCEDURE_IDENTITY,
        slot_directory=current_repository_root() / artifact_slot_directory(slot),
        staging_root=current_repository_root() / artifact_staging_root(),
    )


def read_table_figure_export(
    experiment: ExperimentName | None,
) -> TableFigureExportPayload | None:
    slot = table_figure_export_slot(experiment)
    current = read_current_artifact(current_repository_root() / artifact_slot_directory(slot))
    if current is None:
        return None
    _manifest, payload = current
    return TableFigureExportPayload.model_validate_json(payload)


def read_table_figure_source_data(
    experiment: ExperimentName | None,
) -> tuple[ArtifactManifest, TableFigureSourceDataPayload] | None:
    slot = table_figure_source_data_slot(experiment)
    current = read_current_artifact(current_repository_root() / artifact_slot_directory(slot))
    if current is None:
        return None
    manifest, payload = current
    if (
        manifest.family is not ArtifactFamily.TABLE_FIGURE_SOURCE_DATA
        or manifest.slot != slot
        or manifest.producer is not ArtifactProducer.REPORTING_SOURCE_DATA
        or manifest.procedure_identity != TABLE_FIGURE_SOURCE_DATA_PROCEDURE_IDENTITY
        or json.loads(payload).get("schema_version") != TABLE_FIGURE_SOURCE_DATA_SCHEMA_VERSION
    ):
        return None
    typed_payload = TableFigureSourceDataPayload.model_validate_json(payload)
    upstream = frozenset(
        (reference.slot, reference.identity) for reference in typed_payload.upstream_artifacts
    )
    for table in typed_payload.tables:
        if table.table is TableName.STATISTICAL_SUMMARY and table.row_count != len(
            table.comparison_lineage
        ):
            return None
        if any(
            (lineage.source_artifact.slot, lineage.source_artifact.identity) not in upstream
            for lineage in (*table.comparison_lineage, *table.comparison_cell_lineage)
        ):
            return None
        aggregate_cells = tuple(
            (lineage.lineage.row_index, lineage.lineage.source_column)
            for lineage in table.aggregate_lineage
        )
        if len(set(aggregate_cells)) != len(aggregate_cells):
            return None
        if any(
            (lineage.source_artifact.slot, lineage.source_artifact.identity) not in upstream
            for lineage in table.aggregate_lineage
        ):
            return None
    if any(
        not _figure_point_lineage_is_current(figure, typed_payload)
        for figure in typed_payload.figures
    ):
        return None
    return manifest, typed_payload


def _figure_point_lineage_is_current(
    figure: RenderedFigureIdentity,
    payload: TableFigureSourceDataPayload,
) -> BooleanValue:
    if figure.figure == EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME and not figure.point_lineage:
        return False
    upstream = frozenset(
        (reference.slot, reference.identity) for reference in payload.upstream_artifacts
    )
    point_keys: set[tuple[ExperimentName, ScenarioName, EvidenceCycleIndex, AdmissionState]] = set()
    points_by_experiment: defaultdict[ExperimentName, list[RenderedFigurePointLineage]] = (
        defaultdict(list)
    )
    for point in figure.point_lineage:
        key = (point.experiment, point.condition, point.cycle, point.state)
        if key in point_keys or not point.source_cell_semantic_keys:
            return False
        point_keys.add(key)
        points_by_experiment[point.experiment].append(point)
        if (point.source_artifact.slot, point.source_artifact.identity) not in upstream:
            return False
        evidence_path = experiment_metric_evidence_root(point.experiment) / point.evidence_name
        tolerances = current_application_context().scientific_config.validation_tolerances
        fraction_tolerance = tolerances.trajectory_fraction_absolute
        if (
            not evidence_path.is_file()
            or content_digest(str(evidence_path)) != point.evidence_digest
            or not point.instance_total
            or not math.isclose(
                point.fraction,
                point.instance_count / point.instance_total,
                rel_tol=0.0,
                abs_tol=fraction_tolerance,
            )
        ):
            return False
    if figure.figure != EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME:
        return True
    current_metric_artifacts = tuple(
        reference
        for reference in payload.upstream_artifacts
        if reference.slot.experiment in points_by_experiment
    )
    for experiment, stored_points in points_by_experiment.items():
        current_rows = read_state_trajectory_fractions(
            experiment_metric_evidence_root(experiment) / STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
            experiment,
        )
        current_points = _state_trajectory_point_lineage(current_rows, current_metric_artifacts)

        def point_key(
            item: RenderedFigurePointLineage,
        ) -> tuple[ScenarioName, EvidenceCycleIndex, AdmissionState]:
            return item.condition, item.cycle, item.state

        if tuple(sorted(stored_points, key=point_key)) != tuple(
            sorted(
                (point for point in current_points if point.experiment is experiment),
                key=point_key,
            )
        ):
            return False
    return True


def _table_row_count(table: RenderedTable) -> RowCount:
    rows = table.csv_text.strip().splitlines()
    return 0 if len(rows) <= 1 else len(rows) - 1
