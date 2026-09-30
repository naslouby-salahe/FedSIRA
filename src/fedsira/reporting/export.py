from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import TypeAlias, cast

import pandas

from fedsira.artifacts.paths import (
    artifact_log_path,
    artifact_publication_root,
    current_repository_root,
    execution_outputs_root,
    execution_workspace_root,
    experiment_metric_evidence_root,
    experiment_metrics_root,
    experiment_result_root,
    experiment_telemetry_evidence_root,
    manuscript_figures_root,
    manuscript_reproducibility_root,
    manuscript_results_root,
    manuscript_tables_root,
    preprocessing_root,
    project_summary_root,
    reporting_log_path,
    workspace_root_for_family,
)
from fedsira.artifacts.store import (
    ArtifactManifest,
    configure_artifact_logging,
    load_published_manifests,
)
from fedsira.datasets.layout import dataset_readiness
from fedsira.domain.enums import (
    AdmissionState,
    ArtifactFamily,
    ClaimState,
    ComparisonFamily,
    DatasetId,
    DelayPhaseMetric,
    DescriptiveScientificMetric,
    ExperimentLifecycleState,
    ExperimentName,
    FailureClass,
    FigureName,
    LogEvent,
    ReportColumnName,
    RuntimeComponentName,
    TableName,
    WorkflowTerminalState,
    WorkspaceFileToken,
)
from fedsira.domain.models import (
    ScientificCell,
)
from fedsira.domain.types import (
    AdmissionIndicator,
    ArtifactDigest,
    BooleanValue,
    ByzantineOperatingRegionEvidenceVerified,
    CodeRevision,
    ComparisonName,
    EvidenceCycleIndex,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricName,
    MetricObservation,
    MetricValue,
    OverwriteExisting,
    RelativePathText,
    RepetitionIndex,
    ReportScopeText,
    ReportVerificationFailure,
    RepositoryPath,
    RowCount,
    SafeDormancyEvidenceVerified,
    ScenarioName,
    SchemaVersion,
    ScientificCellCount,
    ScientificCellSemanticKey,
    ScientificCellSemanticKeyTuple,
    TableCsvText,
    VerificationPassed,
)
from fedsira.evaluation.claim_support import (
    ClaimDerivationInputs,
    ClaimSupportEvidence,
    PostEvidenceEfficiencyEvidence,
)
from fedsira.evaluation.comparison_evidence import current_comparison_evidence
from fedsira.evaluation.comparisons import (
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
)
from fedsira.evaluation.metrics import malicious_admission_rate
from fedsira.evaluation.statistics import (
    bootstrap_percentile_confidence_interval,
    quantile_type7,
)
from fedsira.evaluation.summaries import ClaimSummary, claim_summary_from_inputs
from fedsira.experiments.collapse import (
    CollapseDecision,
    ResolvedCore,
    collapse_decision_from_comparison_families,
    collapse_evaluation_from_records,
    materialize_resolved_core,
    read_resolved_core,
)
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    AGGREGATE_METRICS_PARQUET_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    CELL_METRICS_PARQUET_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SEED_METRICS_PARQUET_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
    STATE_TRAJECTORY_PARQUET_NAME,
    experiment_by_name,
)
from fedsira.experiments.engine import (
    CellExecutionOutcome,
    ExecutionProvenance,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedFailureDetail,
    current_execution_records,
    derive_current_experiment_lifecycle,
)
from fedsira.experiments.planning import (
    ExperimentPlan,
    build_plan,
    validate_planned_cell_count_invariant,
)
from fedsira.reporting import tables as table_renderers
from fedsira.reporting.aggregate import AggregateMetricEvidenceRow, SeedMetricEvidenceRow
from fedsira.reporting.figures import (
    EvidenceStateFraction,
    project_result_evidence,
    render_experiment_figures,
    render_mandatory_figures,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.figures import evidence_trajectory as project_evidence_trajectory
from fedsira.reporting.protocol_tables import (
    render_baseline_protocol_table,
    render_dataset_and_domain_protocol_table,
    render_experiment_plan_table,
    render_metric_and_statistics_protocol_table,
    render_model_and_training_protocol_table,
    render_primary_domain_statistics_table,
    render_security_and_capability_contract_protocol_table,
)
from fedsira.reporting.publication import (
    TableFigureSourceDataPayload,
    content_digest,
    publish_claim_state_artifact,
    publish_project_table_figure_source_data,
    publish_table_figure_export,
    publish_table_figure_source_data,
    read_claim_state_artifact,
    read_metric_evidence,
    read_table_figure_export,
    read_table_figure_source_data,
)
from fedsira.reporting.state_trajectory import (
    read_state_trajectory_fractions,
    state_trajectory_fraction_rows,
    write_state_trajectory_fraction_parquet,
)
from fedsira.reporting.tables import (
    MANUSCRIPT_TABLE_NAMES,
    RenderedTable,
    render_ablation_results_table,
    render_byzantine_robustness_table,
    render_collapse_decisions_table,
    render_delay_and_efficiency_table,
    render_experiment_cell_metrics_table,
    render_failure_boundaries_table,
    render_generalization_results_table,
    render_primary_results_table,
    render_source_exclusion_results_table,
    render_statistical_summary_table,
)
from fedsira.reporting.telemetry import (
    EFFICIENCY_METRICS,
    EfficiencyMetricObservation,
    summarize_seed_values,
)
from fedsira.reporting.telemetry import (
    efficiency_telemetry as project_efficiency_telemetry,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
    ExperimentTerminalCount,
    artifact_manifest_dependency_failures,
    metric_artifact_is_semantically_complete,
    table_header,
    terminal_count_for_planned_experiment,
    verify_artifact_manifest_dependencies,
    verify_byzantine_operating_region,
    verify_comparison_evidence_current,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_mandatory_figure_source_data,
    verify_planned_cell_count_satisfied,
    verify_rendered_table,
    verify_report_export_currency,
    verify_safe_dormancy,
)
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ApplicationContext,
    FailureDetail,
    bound_application_context,
    configure_structured_file_logging,
    current_application_context,
    get_structured_logger,
    log_structured_event,
    log_workflow_terminal,
    run_bounded,
)

EXPORT_SCHEMA_VERSION: SchemaVersion = "fedsira|report_export|5"
MINIMUM_SEEDS_FOR_SAMPLE_STANDARD_DEVIATION: ScientificCellCount = 2

REPORT_LOGGER = get_structured_logger(RuntimeComponentName.REPORTING)

PROJECT_SUMMARY_EXPORT_NAME: ReportScopeText = "project summary"


class ReportLogFields(FrozenDomainModel):
    report_scope: ReportScopeText
    artifact_count: ScientificCellCount | None = None


_RESULT_TABLE_EVIDENCE: tuple[tuple[TableName, tuple[ExperimentName, ...]], ...] = (
    (TableName.PRIMARY_RESULTS, (PRIMARY_CONFIRMATORY_EVALUATION_NAME,)),
    (TableName.SOURCE_EXCLUSION_RESULTS, (SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,)),
    (TableName.ABLATION_RESULTS, (MECHANISM_ABLATION_NAME,)),
    (
        TableName.BYZANTINE_ROBUSTNESS,
        (
            COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
            COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
            BYZANTINE_BOUND_VIOLATION_NAME,
        ),
    ),
    (
        TableName.FAILURE_BOUNDARIES,
        (
            EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        ),
    ),
    (
        TableName.DELAY_AND_EFFICIENCY,
        (
            ADMISSION_DELAY_DECOMPOSITION_NAME,
            EFFICIENCY_MEASUREMENT_NAME,
        ),
    ),
    (TableName.GENERALIZATION_RESULTS, (SECONDARY_DATASET_GENERALIZATION_NAME,)),
)


class ExperimentReportSummary(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    completed_cell_count: ScientificCellCount
    planned_cell_count: ScientificCellCount
    execution_digest: ArtifactDigest | None


class ExperimentArtifactManifest(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    execution_digest: ArtifactDigest | None
    artifacts: tuple[RepositoryPath, ...]


class ProjectReproducibilitySummary(FrozenDomainModel):
    schema_version: SchemaVersion
    experiment_states: tuple[ExperimentLifecycleRecord, ...]
    verification_passed: VerificationPassed
    verification_failures: tuple[ReportVerificationFailure, ...]
    mandatory_tables: tuple[TableName, ...]
    materialized_tables: tuple[TableName, ...]
    pending_mandatory_tables: tuple[TableName, ...]
    pending_mandatory_figures: tuple[FigureName, ...]
    claim_summary: ClaimSummary
    claim_state_artifact_identity: ArtifactDigest | None
    source_data_identity: ArtifactDigest | None


class ProjectReportMaterials(FrozenDomainModel):
    rendered_tables: tuple[RenderedTable, ...]
    table_paths: tuple[RepositoryPath, ...]
    figure_paths: tuple[RepositoryPath, ...]
    pending_tables: tuple[TableName, ...]
    pending_figures: tuple[FigureName, ...]


def _render_project_report_materials(
    stage_root: Path,
    plan: ExperimentPlan,
    collapse_decisions: tuple[CollapseDecision, ...] | None,
    resolved_core: ResolvedCore | None,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
    evidence_trajectory: tuple[EvidenceStateFraction, ...],
    telemetry: tuple[EfficiencyMetricObservation, ...],
) -> ProjectReportMaterials:
    tables_root = manuscript_tables_root(stage_root)
    figures_root = manuscript_figures_root(stage_root)
    tables_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)
    log_structured_event(
        REPORT_LOGGER,
        LogEvent.REPORT_PROJECT_TABLES_STARTED,
        ReportLogFields(report_scope=PROJECT_SUMMARY_EXPORT_NAME),
    )
    rendered_tables = render_mandatory_tables(
        plan,
        collapse_decisions=collapse_decisions,
        resolved_core=resolved_core,
        comparison_results=comparison_results,
        outcomes=outcomes,
        efficiency_observations=telemetry,
    )
    table_paths: list[Path] = []
    for table in rendered_tables:
        path = _write_table(tables_root, table)
        table_paths.append(path)
        log_structured_event(
            REPORT_LOGGER,
            LogEvent.REPORT_TABLE_GENERATED,
            ReportLogFields(report_scope=table.name),
        )
    log_structured_event(
        REPORT_LOGGER,
        LogEvent.REPORT_TABLES_COMPLETED,
        ReportLogFields(
            report_scope=PROJECT_SUMMARY_EXPORT_NAME, artifact_count=len(rendered_tables)
        ),
    )
    log_structured_event(
        REPORT_LOGGER,
        LogEvent.REPORT_FIGURE_STARTED,
        ReportLogFields(report_scope=PROJECT_SUMMARY_EXPORT_NAME),
    )
    figure_paths = render_mandatory_figures(
        comparison_results,
        figures_root,
        evidence_trajectory=evidence_trajectory,
        telemetry=telemetry,
        outcomes=outcomes,
    )
    for figure_path in figure_paths:
        log_structured_event(
            REPORT_LOGGER,
            LogEvent.REPORT_FIGURE_GENERATED,
            ReportLogFields(report_scope=Path(figure_path).name),
        )
    pending_tables = tuple(
        name
        for name in MANUSCRIPT_TABLE_NAMES
        if name not in {item.name for item in rendered_tables}
    )
    pending_figures = validate_mandatory_figures_covered(tuple(figure_paths))
    return ProjectReportMaterials(
        rendered_tables=rendered_tables,
        table_paths=tuple(str(path) for path in table_paths),
        figure_paths=tuple(str(path) for path in figure_paths),
        pending_tables=pending_tables,
        pending_figures=pending_figures,
    )


class ReportExportResult(FrozenDomainModel):
    experiment: ExperimentName | None
    exported_paths: tuple[RepositoryPath, ...]
    verification: CompletenessVerificationResult


def _table_evidence_row_count(csv_body: TableCsvText) -> RowCount:
    rows = csv_body.strip().splitlines()
    return 0 if len(rows) <= 1 else len(rows) - 1


def _write_table(root: Path, table: RenderedTable) -> Path:
    if _table_evidence_row_count(table.csv_text) == 0:
        raise ValueError(f"rendered table {table.name} carries no evidence rows")
    destination = root / f"{table.name}.csv"
    destination.write_text(table.csv_text + "\n")
    return destination


def verify_experiment_artifacts(
    result: ExperimentExecutionResult,
    tables_root: Path,
    figures_root: Path,
    metrics_root: Path,
    summary_path: Path,
    source_data_identity: ArtifactDigest,
    experiment_root: Path,
    exported_paths: tuple[RelativePathText, ...],
) -> CompletenessVerificationResult:
    specification = experiment_by_name(result.experiment).artifacts
    failures: list[ReportVerificationFailure] = []
    if specification.metrics_required:
        if not summary_path.is_file() or not summary_path.read_text(encoding="utf-8").strip():
            failures.append(f"{result.experiment}: metric summary is missing or empty")
        else:
            summary = ExperimentReportSummary.model_validate_json(
                summary_path.read_text(encoding="utf-8")
            )
            if summary.experiment != result.experiment:
                failures.append(
                    f"{result.experiment}: metric summary belongs to another experiment"
                )
            if summary.lifecycle_state != result.lifecycle_state:
                failures.append(f"{result.experiment}: metric summary lifecycle state is stale")
            if summary.planned_cell_count != len(result.outcomes):
                failures.append(f"{result.experiment}: metric summary planned cell count is stale")
            if summary.execution_digest != result.execution_digest:
                failures.append(f"{result.experiment}: metric summary execution digest is stale")
    for filename in specification.required_metric_artifacts:
        path = metrics_root / filename
        if not metric_artifact_is_semantically_complete(path, result):
            failures.append(
                f"{result.experiment}: required metric artifact {filename} is missing or empty"
            )
    for table_name in specification.required_tables:
        expected_header = table_header(table_name)
        required_rows = frozenset(
            (
                outcome.cell.experiment,
                outcome.cell.method,
                outcome.cell.condition,
                str(outcome.cell.master_seed),
                "" if outcome.cell.repetition is None else str(outcome.cell.repetition),
            )
            for outcome in result.outcomes
        )
        failures.extend(
            verify_rendered_table(
                tables_root / f"{table_name}.csv",
                expected_header,
                required_rows,
            )
        )
    for figure_name in specification.required_figures:
        path = figures_root / f"{figure_name}.png"
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(
                f"{result.experiment}: required figure {figure_name} is missing or empty"
            )
    failures.extend(
        verify_mandatory_figure_source_data(
            result,
            read_state_trajectory_fractions(
                metrics_root / STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
                result.experiment,
            )
            if result.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME
            else (),
            project_efficiency_telemetry(result.outcomes)
            if result.experiment == EFFICIENCY_MEASUREMENT_NAME
            else (),
            result.outcomes,
        )
    )
    if not result.outcomes or any(not outcome.completed for outcome in result.outcomes):
        failures.append(f"{result.experiment}: figures lack completed source evidence")
    failures.extend(
        verify_report_export_currency(
            result.experiment, source_data_identity, experiment_root, exported_paths
        )
    )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def verify_persisted_experiment_report(
    result: ExperimentExecutionResult,
    experiment_root: Path,
) -> ReportExportResult:
    export_payload = read_table_figure_export(result.experiment)
    source_data = read_table_figure_source_data(result.experiment)
    if export_payload is None or source_data is None:
        failures = tuple(
            failure
            for missing, failure in (
                (export_payload is None, f"{result.experiment}: report export artifact is absent"),
                (source_data is None, f"{result.experiment}: source-data artifact is absent"),
            )
            if missing
        )
        return ReportExportResult(
            experiment=result.experiment,
            exported_paths=(),
            verification=CompletenessVerificationResult(passed=False, failures=failures),
        )

    source_manifest, source_payload = source_data
    exported_paths = export_payload.exported_paths
    failures = (
        *_publication_identity_failures(
            result,
            export_payload.experiment,
            source_manifest.identity,
            export_payload.source_data_identity,
            source_payload.experiment,
            source_payload.execution_digest,
        ),
        *_published_path_failures(result.experiment, experiment_root, exported_paths),
        *_source_product_failures(result.experiment, experiment_root, source_payload),
        *_required_product_failures(result.experiment, experiment_root, source_payload),
        *_persisted_summary_failures(result, experiment_root),
    )

    return ReportExportResult(
        experiment=result.experiment,
        exported_paths=tuple(str(experiment_root / path) for path in exported_paths),
        verification=CompletenessVerificationResult(passed=not failures, failures=failures),
    )


def _publication_identity_failures(
    result: ExperimentExecutionResult,
    export_experiment: ExperimentName | None,
    source_identity: ArtifactDigest,
    export_source_identity: ArtifactDigest,
    source_experiment: ExperimentName | None,
    source_execution_digest: ArtifactDigest,
) -> tuple[ReportVerificationFailure, ...]:
    failures: list[ReportVerificationFailure] = []
    if export_experiment != result.experiment:
        failures.append(f"{result.experiment}: report export belongs to another experiment")
    if source_experiment != result.experiment:
        failures.append(f"{result.experiment}: source-data artifact belongs to another experiment")
    if source_execution_digest != result.execution_digest:
        failures.append(f"{result.experiment}: source-data artifact is stale for current execution")
    if export_source_identity != source_identity:
        failures.append(f"{result.experiment}: report export artifact is stale for its source data")
    return tuple(failures)


def _published_path_failures(
    experiment: ExperimentName,
    experiment_root: Path,
    exported_paths: tuple[RelativePathText, ...],
) -> tuple[ReportVerificationFailure, ...]:
    return tuple(
        f"{experiment}: exported report product is missing or empty: {relative}"
        for relative in exported_paths
        if not (path := experiment_root / relative).is_file() or path.stat().st_size == 0
    )


def _source_product_failures(
    experiment: ExperimentName,
    experiment_root: Path,
    payload: TableFigureSourceDataPayload,
) -> tuple[ReportVerificationFailure, ...]:
    failures: list[ReportVerificationFailure] = []
    products = (
        (
            item.content_digest,
            manuscript_tables_root(experiment_root) / f"{item.table}.csv",
            f"rendered table {item.table}",
        )
        for item in payload.tables
    )
    products = (
        *products,
        *(
            (
                item.content_digest,
                manuscript_figures_root(experiment_root) / f"{item.figure}.png",
                f"rendered figure {item.figure}",
            )
            for item in payload.figures
        ),
    )
    for digest, path, label in products:
        if not path.is_file() or content_digest(str(path)) != digest:
            failures.append(f"{experiment}: {label} is missing or stale")
    for item in payload.evidence:
        candidates = (
            experiment_metric_evidence_root(experiment) / item.evidence_name,
            experiment_telemetry_evidence_root(experiment) / item.evidence_name,
        )
        if not any(
            path.is_file() and content_digest(str(path)) == item.content_digest
            for path in candidates
        ):
            failures.append(
                f"{experiment}: source evidence is missing or stale: {item.evidence_name}"
            )
    return tuple(failures)


def _required_product_failures(
    experiment: ExperimentName,
    experiment_root: Path,
    payload: TableFigureSourceDataPayload,
) -> tuple[ReportVerificationFailure, ...]:
    specification = experiment_by_name(experiment).artifacts
    failures = [
        f"{experiment}: required metric artifact {filename} is missing or empty"
        for filename in specification.required_metric_artifacts
        if not (path := experiment_metric_evidence_root(experiment) / filename).is_file()
        or path.stat().st_size == 0
    ]
    evidence_names = {item.evidence_name for item in payload.evidence}
    failures.extend(
        f"{experiment}: required metric artifact {filename} is not registered in source data"
        for filename in specification.required_metric_artifacts
        if filename not in evidence_names
    )
    table_names = {item.table for item in payload.tables}
    figure_names = {item.figure for item in payload.figures}
    failures.extend(
        f"{experiment}: required table {table_name} is not registered"
        for table_name in specification.required_tables
        if table_name not in table_names
    )
    failures.extend(
        f"{experiment}: required figure {figure_name} is not registered"
        for figure_name in specification.required_figures
        if figure_name not in figure_names
    )
    return tuple(failures)


def _metric_evidence_publication_failures(
    result: ExperimentExecutionResult,
) -> tuple[ArtifactDigest | None, tuple[ReportVerificationFailure, ...]]:
    current = read_metric_evidence(result.experiment)
    if current is None:
        return None, (f"{result.experiment}: published metric evidence artifact is absent",)
    manifest, payload = current
    failures: list[ReportVerificationFailure] = []
    if payload.experiment != result.experiment:
        failures.append(f"{result.experiment}: metric evidence belongs to another experiment")
    if payload.execution_digest != result.execution_digest:
        failures.append(f"{result.experiment}: metric evidence is stale for current execution")
    evidence_names: set[str] = set()
    for item in payload.evidence:
        evidence_names.add(item.evidence_name)
        candidates = (
            experiment_metric_evidence_root(result.experiment) / item.evidence_name,
            experiment_telemetry_evidence_root(result.experiment) / item.evidence_name,
        )
        if not any(
            path.is_file()
            and path.stat().st_size == item.content_bytes
            and content_digest(str(path)) == item.content_digest
            for path in candidates
        ):
            failures.append(
                f"{result.experiment}: published metric evidence file is missing or stale: "
                f"{item.evidence_name}"
            )
    failures.extend(
        f"{result.experiment}: required metric artifact {filename} is not published"
        for filename in experiment_by_name(result.experiment).artifacts.required_metric_artifacts
        if filename not in evidence_names
    )
    return manifest.identity, tuple(failures)


def _persisted_summary_failures(
    result: ExperimentExecutionResult,
    experiment_root: Path,
) -> tuple[ReportVerificationFailure, ...]:
    summary_path = experiment_metrics_root(experiment_root) / WorkspaceFileToken.SUMMARY_JSON
    if not summary_path.is_file():
        return (f"{result.experiment}: metric summary is missing",)
    summary = ExperimentReportSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))
    if (
        summary.experiment != result.experiment
        or summary.execution_digest != result.execution_digest
    ):
        return (f"{result.experiment}: metric summary is stale for current execution",)
    if summary.lifecycle_state is not ExperimentLifecycleState.COMPLETED:
        return (f"{result.experiment}: metric summary is not complete",)
    if summary.planned_cell_count != len(result.outcomes):
        return (f"{result.experiment}: metric summary planned cell count is stale",)
    if summary.completed_cell_count != result.cell_completion_count:
        return (f"{result.experiment}: metric summary completed cell count is stale",)
    return ()


def export_experiment_report(
    result: ExperimentExecutionResult,
    experiment_root: Path,
) -> ReportExportResult:
    if result.lifecycle_state is not ExperimentLifecycleState.COMPLETED:
        verification = CompletenessVerificationResult(
            passed=False,
            failures=(f"{result.experiment}: experiment is not complete",),
        )
        return ReportExportResult(
            experiment=result.experiment,
            exported_paths=(),
            verification=verification,
        )

    if result.provenance is None:
        verification = CompletenessVerificationResult(
            passed=False,
            failures=(f"{result.experiment}: current execution provenance is missing",),
        )
        return ReportExportResult(
            experiment=result.experiment,
            exported_paths=(),
            verification=verification,
        )

    tables_root = manuscript_tables_root(experiment_root)
    figures_root = manuscript_figures_root(experiment_root)
    metrics_root = experiment_metric_evidence_root(result.experiment)
    telemetry_root = experiment_telemetry_evidence_root(result.experiment)
    summary_path = experiment_metrics_root(experiment_root) / WorkspaceFileToken.SUMMARY_JSON
    missing_evidence = tuple(
        filename
        for filename in experiment_by_name(result.experiment).artifacts.required_metric_artifacts
        if not metric_artifact_is_semantically_complete(metrics_root / filename, result)
    )
    metric_evidence_identity, metric_publication_failures = _metric_evidence_publication_failures(
        result
    )
    if missing_evidence or metric_publication_failures or metric_evidence_identity is None:
        return ReportExportResult(
            experiment=result.experiment,
            exported_paths=(),
            verification=CompletenessVerificationResult(
                passed=False,
                failures=(
                    *metric_publication_failures,
                    *tuple(
                        f"{result.experiment}: required run-side metric evidence "
                        f"is missing or invalid: {filename}"
                        for filename in missing_evidence
                    ),
                ),
            ),
        )
    tables_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)

    log_structured_event(
        REPORT_LOGGER,
        LogEvent.REPORT_TABLE_STARTED,
        ReportLogFields(report_scope=result.experiment),
    )
    rendered_tables: list[RenderedTable] = [render_experiment_cell_metrics_table(result.outcomes)]
    if result.comparison_results:
        rendered_tables.append(
            table_renderers.render_statistical_summary_table(result.comparison_results)
        )
    table_paths = tuple(_write_table(tables_root, table) for table in rendered_tables)
    state_trajectory = (
        read_state_trajectory_fractions(
            metrics_root / STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
            result.experiment,
        )
        if result.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME
        else ()
    )
    figure_paths = render_experiment_figures(
        result,
        figures_root,
        state_trajectory,
        project_efficiency_telemetry(result.outcomes)
        if result.experiment == EFFICIENCY_MEASUREMENT_NAME
        else (),
    )
    exported: list[Path] = [*table_paths, *figure_paths]
    log_structured_event(
        REPORT_LOGGER,
        LogEvent.REPORT_EXPERIMENT_ARTIFACTS_RENDERED,
        ReportLogFields(report_scope=result.experiment, artifact_count=len(exported)),
    )
    evidence_paths = _persisted_experiment_evidence_paths(metrics_root, telemetry_root)
    source_data_manifest, _source_data_reused = publish_table_figure_source_data(
        result.experiment,
        result.execution_digest,
        metric_evidence_identity,
        tuple(rendered_tables),
        tuple(str(path) for path in figure_paths),
        tuple(str(path) for path in table_paths),
        evidence_paths,
        comparison_artifact_identity=result.comparison_artifact_id,
        state_trajectory=state_trajectory,
    )

    summary = ExperimentReportSummary(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment=result.experiment,
        lifecycle_state=result.lifecycle_state,
        completed_cell_count=result.cell_completion_count,
        planned_cell_count=len(result.outcomes),
        execution_digest=result.execution_digest,
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary.model_dump_json(indent=2) + "\n")
    exported.append(summary_path)
    manifest_path = experiment_root / WorkspaceFileToken.MANIFEST_JSON
    manifest = ExperimentArtifactManifest(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment=result.experiment,
        lifecycle_state=result.lifecycle_state,
        execution_digest=result.execution_digest,
        artifacts=tuple(str(path) for path in exported),
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
    exported.append(manifest_path)
    exported_relative = tuple(path.relative_to(experiment_root).as_posix() for path in exported)
    publish_table_figure_export(
        result.experiment,
        source_data_manifest.identity,
        experiment_root,
        tuple(str(path) for path in exported),
    )
    verification = verify_experiment_artifacts(
        result,
        tables_root,
        figures_root,
        metrics_root,
        summary_path,
        source_data_manifest.identity,
        experiment_root,
        exported_relative,
    )
    return ReportExportResult(
        experiment=result.experiment,
        exported_paths=tuple(str(path) for path in exported),
        verification=verification,
    )


def _persisted_experiment_evidence_paths(
    metrics_root: Path,
    telemetry_root: Path,
) -> tuple[RepositoryPath, ...]:
    candidates = (
        *(
            metrics_root / name
            for name in (
                CELL_METRICS_PARQUET_NAME,
                SEED_METRICS_PARQUET_NAME,
                AGGREGATE_METRICS_PARQUET_NAME,
                STATE_TRAJECTORY_PARQUET_NAME,
                STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
                COMPARISONS_PARQUET_NAME,
            )
        ),
        telemetry_root / TIMINGS_PARQUET_NAME,
        telemetry_root / RESOURCES_PARQUET_NAME,
    )
    return tuple(str(path) for path in candidates if path.is_file())


def _report_material_failures(
    pending_tables: tuple[TableName, ...],
    pending_figures: tuple[FigureName, ...],
) -> tuple[ReportVerificationFailure, ...]:
    failures: list[ReportVerificationFailure] = []
    if pending_tables:
        failures.append(f"mandatory tables not materialized: {', '.join(pending_tables)}")
    if pending_figures:
        failures.append(f"mandatory figures not materialized: {', '.join(pending_figures)}")
    return tuple(failures)


def _missing_result_evidence(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[ReportVerificationFailure, ...]:
    evidenced_experiments = frozenset(
        comparison.definition.experiment
        for family in comparison_results
        for comparison in family.comparisons
    )
    completed_experiments = frozenset(
        outcome.cell.experiment for outcome in outcomes if outcome.completed
    )
    failures: list[ReportVerificationFailure] = []
    for table_name, expected_experiments in _RESULT_TABLE_EVIDENCE:
        missing = tuple(
            experiment
            for experiment in expected_experiments
            if (
                experiment not in evidenced_experiments
                if experiment_by_name(experiment).comparison_family is not None
                else experiment not in completed_experiments
            )
        )
        if missing:
            failures.append(
                f"{table_name}: missing required scientific evidence for {', '.join(missing)}"
            )
    if not comparison_results:
        failures.append("Statistical Summary: no comparison evidence")
    return tuple(failures)


def _publish_project_report_source_data(
    upstream_catalog: tuple[ArtifactManifest, ...],
    rendered_tables: tuple[RenderedTable, ...],
    table_paths: tuple[Path, ...],
    figure_paths: tuple[Path, ...],
    state_trajectory: tuple[EvidenceStateFraction, ...],
) -> tuple[ArtifactManifest | None, tuple[ReportVerificationFailure, ...]]:
    required_families = frozenset(
        (
            ArtifactFamily.DATASET_MANIFEST,
            ArtifactFamily.ROLE_SPLIT_SAMPLE_MANIFEST,
            ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION,
            ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT,
            ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
            ArtifactFamily.FINAL_GATE_DECISION,
        )
    )
    upstream_manifests = [
        manifest for manifest in upstream_catalog if manifest.family in required_families
    ]
    claim_artifact = read_claim_state_artifact(upstream_catalog)
    if claim_artifact is not None and all(
        manifest.identity != claim_artifact[0].identity for manifest in upstream_manifests
    ):
        upstream_manifests.append(claim_artifact[0])
    unique_upstream_manifests = tuple(
        sorted(
            upstream_manifests,
            key=lambda item: (
                item.family.value,
                item.slot.experiment or "",
                item.slot.instance,
            ),
        )
    )
    if not unique_upstream_manifests:
        return None, ("Project source data: current upstream manifests are unavailable",)
    execution_digest = hashlib.sha256(
        json.dumps(
            [manifest.identity for manifest in unique_upstream_manifests],
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    try:
        manifest, _reused = publish_project_table_figure_source_data(
            execution_digest,
            unique_upstream_manifests,
            rendered_tables,
            tuple(str(path) for path in figure_paths),
            tuple(str(path) for path in table_paths),
            state_trajectory,
        )
    except (OSError, ValueError) as error:
        return None, (f"Project source data: publication failed: {error}",)
    current_source = read_table_figure_source_data(None)
    if current_source is None or current_source[0].identity != manifest.identity:
        return None, ("Project source data: current publication could not be read back",)
    payload = current_source[1]
    expected_upstream = tuple(
        (item.slot, item.identity)
        for item in sorted(
            unique_upstream_manifests,
            key=lambda item: (
                item.family.value,
                item.slot.experiment or "",
                item.slot.instance,
            ),
        )
    )
    actual_upstream = tuple((item.slot, item.identity) for item in payload.upstream_artifacts)
    if (
        payload.experiment is not None
        or payload.execution_digest != execution_digest
        or actual_upstream != expected_upstream
    ):
        return None, ("Project source data: payload lineage does not match current inputs",)
    for record, path in zip(payload.tables, table_paths, strict=True):
        if record.content_digest != content_digest(str(path)):
            return None, (f"Project source data: rendered table changed: {record.table}",)
    for record, path in zip(payload.figures, figure_paths, strict=True):
        if record.content_digest != content_digest(str(path)):
            return None, (f"Project source data: rendered figure changed: {record.figure}",)
    return manifest, ()


def _finalize_project_report(
    project_root: Path,
    reproducibility_root: Path,
    lifecycle_states: tuple[ExperimentLifecycleRecord, ...],
    materialized_tables: tuple[TableName, ...],
    pending_tables: tuple[TableName, ...],
    pending_figures: tuple[FigureName, ...],
    claim_summary: ClaimSummary,
    claim_state_identity: ArtifactDigest,
    rendered_tables: tuple[RenderedTable, ...],
    table_paths: tuple[Path, ...],
    figure_paths: tuple[Path, ...],
    exported_paths: tuple[Path, ...],
    initial_verification: CompletenessVerificationResult,
    upstream_catalog: tuple[ArtifactManifest, ...],
    state_trajectory: tuple[EvidenceStateFraction, ...],
) -> tuple[CompletenessVerificationResult, Path]:
    verification = initial_verification
    source_data_manifest: ArtifactManifest | None = None
    if verification.passed:
        source_data_manifest, failures = _publish_project_report_source_data(
            upstream_catalog, rendered_tables, table_paths, figure_paths, state_trajectory
        )
        if failures:
            verification = CompletenessVerificationResult(passed=False, failures=failures)

    summary = ProjectReproducibilitySummary(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment_states=lifecycle_states,
        verification_passed=verification.passed,
        verification_failures=verification.failures,
        mandatory_tables=MANUSCRIPT_TABLE_NAMES,
        materialized_tables=materialized_tables,
        pending_mandatory_tables=pending_tables,
        pending_mandatory_figures=pending_figures,
        claim_summary=claim_summary,
        claim_state_artifact_identity=claim_state_identity,
        source_data_identity=(
            None if source_data_manifest is None else source_data_manifest.identity
        ),
    )
    summary_path = reproducibility_root / WorkspaceFileToken.EXECUTION_SUMMARY_JSON
    summary_path.write_text(summary.model_dump_json(indent=2) + "\n")
    if verification.passed and source_data_manifest is not None:
        try:
            _export_manifest, _reused = publish_table_figure_export(
                None,
                source_data_manifest.identity,
                project_root.resolve(),
                tuple(str(path.resolve()) for path in (*exported_paths, summary_path)),
            )
        except (OSError, ValueError) as error:
            verification = CompletenessVerificationResult(
                passed=False,
                failures=(f"Project report export: publication failed: {error}",),
            )
        else:
            export_payload = read_table_figure_export(None)
            failures = verify_report_export_currency(
                None,
                source_data_manifest.identity,
                project_root.resolve(),
                () if export_payload is None else export_payload.exported_paths,
            )
            if failures:
                verification = CompletenessVerificationResult(
                    passed=False,
                    failures=failures,
                )
    return verification, summary_path


def post_evidence_efficiency_evidence(
    outcomes: tuple[CellExecutionOutcome, ...],
    telemetry: tuple[EfficiencyMetricObservation, ...],
) -> PostEvidenceEfficiencyEvidence | None:
    efficiency_outcomes = tuple(
        outcome for outcome in outcomes if outcome.cell.experiment == EFFICIENCY_MEASUREMENT_NAME
    )
    if not efficiency_outcomes:
        return None
    required_metrics = frozenset(
        (
            DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
            DescriptiveScientificMetric.COMMUNICATION_BYTES,
            DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
        )
    )
    observed = tuple(
        observation for observation in telemetry if observation.metric in required_metrics
    )
    return PostEvidenceEfficiencyEvidence(
        measurement_executed=True,
        all_repetitions_complete=all(
            outcome.completed and outcome.cell.repetition is not None
            for outcome in efficiency_outcomes
        ),
        median_iqr_valid=required_metrics.issubset({observation.metric for observation in observed})
        and all(observation.seed_count > 0 for observation in observed),
    )


def export_project_summary(
    plan: ExperimentPlan,
    lifecycle_states: tuple[ExperimentLifecycleRecord, ...],
    verification: CompletenessVerificationResult,
    collapse_decisions: tuple[CollapseDecision, ...] | None,
    resolved_core: ResolvedCore | None,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
    evidence_trajectory: tuple[EvidenceStateFraction, ...],
    telemetry: tuple[EfficiencyMetricObservation, ...],
    claim_upstream_manifests: tuple[ArtifactManifest, ...] = (),
    safe_dormancy_verified: SafeDormancyEvidenceVerified = False,
    byzantine_operating_region_verified: ByzantineOperatingRegionEvidenceVerified = False,
) -> ReportExportResult:
    if not verification.passed:
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=verification,
        )

    evidence_failures = _missing_result_evidence(comparison_results, outcomes)
    if not evidence_trajectory:
        evidence_failures = (
            *evidence_failures,
            "Evidence-Arrival State Trajectory: missing state evidence",
        )
    if not telemetry:
        evidence_failures = (*evidence_failures, "Efficiency Profile: missing telemetry evidence")
    if evidence_failures:
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=CompletenessVerificationResult(
                passed=False,
                failures=evidence_failures,
            ),
        )

    efficiency_evidence = post_evidence_efficiency_evidence(outcomes, telemetry)
    claim_inputs = ClaimDerivationInputs(
        collapse_decisions=collapse_decisions,
        comparison_results=comparison_results,
        safe_dormancy_verified=safe_dormancy_verified,
        byzantine_operating_region_verified=byzantine_operating_region_verified,
        support=(
            None
            if efficiency_evidence is None
            else ClaimSupportEvidence(post_evidence_efficiency=efficiency_evidence)
        ),
    )
    claim_summary = claim_summary_from_inputs(claim_inputs)
    claim_state_artifact_identity: ArtifactDigest | None = None
    if claim_upstream_manifests:
        try:
            claim_manifest, _claim_artifact_reused = publish_claim_state_artifact(
                claim_inputs,
                claim_upstream_manifests,
            )
        except ValueError as error:
            return ReportExportResult(
                experiment=None,
                exported_paths=(),
                verification=CompletenessVerificationResult(
                    passed=False,
                    failures=(f"Claim-state artifact: {error}",),
                ),
            )
        claim_state_artifact_identity = claim_manifest.identity
        claim_artifact = read_claim_state_artifact(claim_upstream_manifests)
        if (
            claim_artifact is None
            or claim_artifact[0].identity != claim_manifest.identity
            or claim_artifact[1].claim_summary != claim_summary
        ):
            return ReportExportResult(
                experiment=None,
                exported_paths=(),
                verification=CompletenessVerificationResult(
                    passed=False,
                    failures=(
                        "Claim-state artifact: current evidence lineage or "
                        "payload verification failed",
                    ),
                ),
            )
    if any(decision.state is ClaimState.NOT_TESTED for decision in claim_summary.decisions):
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=CompletenessVerificationResult(
                passed=False,
                failures=("Claim states: final evidence-driven decisions are not available",),
            ),
        )

    if claim_state_artifact_identity is None:
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=CompletenessVerificationResult(
                passed=False,
                failures=(
                    "Claim-state artifact: mandatory statistical/gate lineage is unavailable",
                ),
            ),
        )

    project_root = project_summary_root()
    reproducibility_root = manuscript_reproducibility_root(project_root)
    exported: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="fedsira-project-report-") as staging_directory:
        stage_root = Path(staging_directory)
        materials = _render_project_report_materials(
            stage_root,
            plan,
            collapse_decisions,
            resolved_core,
            comparison_results,
            outcomes,
            evidence_trajectory,
            telemetry,
        )
        material_failures = _report_material_failures(
            materials.pending_tables, materials.pending_figures
        )
        if material_failures:
            return ReportExportResult(
                experiment=None,
                exported_paths=(),
                verification=CompletenessVerificationResult(
                    passed=False,
                    failures=material_failures,
                ),
            )

        final_table_paths: list[Path] = []
        final_figure_paths: list[Path] = []
        for staged_path in materials.table_paths:
            source = Path(staged_path)
            destination = project_root / source.relative_to(stage_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            final_table_paths.append(destination)
        for staged_path in materials.figure_paths:
            source = Path(staged_path)
            destination = project_root / source.relative_to(stage_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            final_figure_paths.append(destination)
        exported.extend((*final_table_paths, *final_figure_paths))
        reproducibility_root.mkdir(parents=True, exist_ok=True)
        final_verification, reproducibility_path = _finalize_project_report(
            project_root,
            reproducibility_root,
            lifecycle_states,
            tuple(item.name for item in materials.rendered_tables),
            materials.pending_tables,
            materials.pending_figures,
            claim_summary,
            claim_state_artifact_identity,
            materials.rendered_tables,
            tuple(final_table_paths),
            tuple(final_figure_paths),
            tuple(exported),
            CompletenessVerificationResult(passed=True, failures=()),
            claim_upstream_manifests,
            evidence_trajectory,
        )
        exported.append(reproducibility_path)

    return ReportExportResult(
        experiment=None,
        exported_paths=tuple(str(path) for path in exported),
        verification=final_verification,
    )


_COLLAPSE_FAMILIES: tuple[ComparisonFamily, ...] = (
    ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
    ComparisonFamily.PLURALITY_NECESSITY,
    ComparisonFamily.SOURCE_EXCLUSION_CENTRAL_EFFECT,
    ComparisonFamily.EXTERNAL_VERIFICATION_NECESSITY,
)


def execute_report(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
    try:
        context = ApplicationContext.load(REPOSITORY_ROOT)
    except ValueError as error:
        log_workflow_terminal(
            REPORT_LOGGER,
            RuntimeComponentName.CREATING_REPORT,
            WorkflowTerminalState.BLOCKED,
            FailureClass.CONFIGURATION_INVALID,
            str(error),
        )
        raise
    with bound_application_context(context):
        configure_structured_file_logging(
            REPORT_LOGGER, current_repository_root() / reporting_log_path()
        )
        configure_artifact_logging(current_repository_root() / artifact_log_path())
        scope = name if name is not None else PROJECT_SUMMARY_EXPORT_NAME
        fields = ReportLogFields(report_scope=scope)
        log_structured_event(REPORT_LOGGER, LogEvent.REPORT_STARTED, fields)
        timeout = context.scientific_config.execution.timeouts_seconds.experiment_analysis_or_report
        try:
            run_bounded(
                RuntimeComponentName.CREATING_REPORT,
                timeout,
                lambda: _execute_bound(name, overwrite),
            )
        except SystemExit:
            log_workflow_terminal(
                REPORT_LOGGER,
                RuntimeComponentName.CREATING_REPORT,
                WorkflowTerminalState.BLOCKED,
                FailureClass.EVIDENCE_INSUFFICIENT,
                "report verification blocked publication",
            )
            raise
        except TimeoutError as error:
            log_workflow_terminal(
                REPORT_LOGGER,
                RuntimeComponentName.CREATING_REPORT,
                WorkflowTerminalState.FAILED,
                FailureClass.TIMEOUT,
                str(error),
            )
            raise
        except Exception as error:
            log_workflow_terminal(
                REPORT_LOGGER,
                RuntimeComponentName.CREATING_REPORT,
                WorkflowTerminalState.FAILED,
                FailureClass.IMPLEMENTATION_ERROR,
                str(error),
            )
            raise
        log_structured_event(REPORT_LOGGER, LogEvent.REPORT_COMPLETED, fields)
        log_workflow_terminal(
            REPORT_LOGGER,
            RuntimeComponentName.CREATING_REPORT,
            WorkflowTerminalState.COMPLETED,
        )


def _execute_bound(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
    store = ExecutionRecordStore(execution_workspace_root())
    if name is not None:
        result = _load_experiment_result(name, store)
        experiment_root = current_repository_root() / experiment_result_root(name)
        export = export_experiment_report(result, experiment_root)
        for path in export.exported_paths:
            print(f"exported {path}")
        if not export.verification.passed:
            raise SystemExit(1)
        persisted = verify_persisted_experiment_report(result, experiment_root)
        if not persisted.verification.passed:
            raise SystemExit(1)
        return
    resolved_core_complete = _resolved_core_complete()
    plan = build_plan(resolved_core_complete=resolved_core_complete)
    validate_planned_cell_count_invariant(plan)
    terminal_counts: list[ExperimentTerminalCount] = []
    lifecycle_states: list[ExperimentLifecycleRecord] = []
    readiness = dataset_readiness()
    for planned in plan.experiments:
        records = store.read_all_outcomes(planned.definition.name)
        records = current_execution_records(planned, records, readiness)
        terminal_counts.append(
            ExperimentTerminalCount(
                experiment=planned.definition.name,
                count=terminal_count_for_planned_experiment(planned, records),
            )
        )
        lifecycle_states.append(
            ExperimentLifecycleRecord(
                experiment=planned.definition.name,
                state=derive_current_experiment_lifecycle(planned, records, readiness),
            )
        )
    terminal_count_records = tuple(terminal_counts)
    lifecycle_records = tuple(lifecycle_states)
    experiment_names = tuple(planned.definition.name for planned in plan.experiments)
    execution_config = current_application_context().scientific_config.execution
    verification_timeout = execution_config.timeouts_seconds.final_export_verification
    artifact_roots = (
        current_repository_root() / preprocessing_root(),
        current_repository_root() / artifact_publication_root(),
        current_repository_root() / execution_outputs_root(),
        current_repository_root() / manuscript_results_root(),
    )
    (
        count_verification,
        completion_verification,
        terminal_verification,
        manifest_catalog,
        byzantine_bound_verification,
        comparison_evidence_verification,
        safe_dormancy_verification,
    ) = run_bounded(
        RuntimeComponentName.FINAL_EXPORT_VERIFICATION,
        verification_timeout,
        lambda: (
            verify_planned_cell_count_satisfied(plan, terminal_count_records),
            verify_experiments_completed(lifecycle_records, experiment_names),
            verify_experiments_reached_terminal_state(lifecycle_records, experiment_names),
            load_published_manifests(artifact_roots),
            verify_byzantine_operating_region(
                plan.experiment(BYZANTINE_BOUND_VIOLATION_NAME),
                store.read_all_outcomes(BYZANTINE_BOUND_VIOLATION_NAME),
            ),
            verify_comparison_evidence_current(experiment_names, store),
            verify_safe_dormancy(
                plan.experiment(EVIDENCE_SCARCITY_AND_DORMANCY_NAME),
                store.read_all_outcomes(EVIDENCE_SCARCITY_AND_DORMANCY_NAME),
            ),
        ),
    )
    published_manifests, invalid_manifests = manifest_catalog
    manifest_dependency_verification = verify_artifact_manifest_dependencies(
        artifact_manifest_dependency_failures(published_manifests, invalid_manifests)
    )
    failures = (
        *count_verification.failures,
        *completion_verification.failures,
        *terminal_verification.failures,
        *manifest_dependency_verification.failures,
        *byzantine_bound_verification.failures,
        *comparison_evidence_verification.failures,
        *safe_dormancy_verification.failures,
    )
    loaded_results = tuple(
        _load_experiment_result(planned.definition.name, store) for planned in plan.experiments
    )
    metric_evidence_failures = tuple(
        failure
        for result in loaded_results
        if result.lifecycle_state is ExperimentLifecycleState.COMPLETED
        for failure in _run_side_metric_evidence_failures(result)
    )
    failures = (*failures, *metric_evidence_failures)
    verification = CompletenessVerificationResult(passed=not failures, failures=failures)
    collapse_decisions = _load_collapse_decisions(store)
    comparison_results, outcomes = project_result_evidence(
        plan,
        lambda name: next(result for result in loaded_results if result.experiment == name),
    )
    export = export_project_summary(
        plan,
        lifecycle_records,
        verification,
        collapse_decisions=collapse_decisions,
        resolved_core=materialize_resolved_core(collapse_decisions)
        if collapse_decisions is not None
        else None,
        comparison_results=comparison_results,
        outcomes=outcomes,
        evidence_trajectory=project_evidence_trajectory(),
        telemetry=project_efficiency_telemetry(outcomes),
        claim_upstream_manifests=published_manifests,
        safe_dormancy_verified=safe_dormancy_verification.passed,
        byzantine_operating_region_verified=byzantine_bound_verification.passed,
    )
    for path in export.exported_paths:
        print(f"exported {path}")
    if not export.verification.passed:
        print("project summary verification: BLOCKED")
        for failure in export.verification.failures:
            print(f"  {failure}")
        raise SystemExit(1)


def _resolved_core_complete() -> BooleanValue:
    directory = current_repository_root() / workspace_root_for_family(
        ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION
    )
    return read_resolved_core(directory) is not None


def _load_experiment_result(
    name: ExperimentName, store: ExecutionRecordStore
) -> ExperimentExecutionResult:
    plan = build_plan(resolved_core_complete=_resolved_core_complete())
    records = store.read_all_outcomes(name)
    readiness = dataset_readiness()
    if (
        name == DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME
        and readiness is not ExperimentLifecycleState.COMPLETED
    ):
        records = ()
    else:
        records = current_execution_records(plan.experiment(name), records, readiness)
    outcomes = tuple(
        CellExecutionOutcome(
            cell=ScientificCell(
                experiment=record.experiment,
                method=record.method,
                condition=record.condition,
                master_seed=record.master_seed,
                repetition=record.repetition,
            ),
            terminal_state=record.terminal_state,
            failure=_to_failure_detail(record.failure),
            metrics=record.metrics,
            state_trajectory=record.state_trajectory,
            scoring_artifact_ids=record.scoring_artifact_ids,
        )
        for record in records
    )
    comparison_evidence = current_comparison_evidence(name, records)
    result = ExperimentExecutionResult(
        experiment=name,
        lifecycle_state=derive_current_experiment_lifecycle(
            plan.experiment(name), records, readiness
        ),
        outcomes=outcomes,
        comparison_results=(() if comparison_evidence is None else comparison_evidence[1].families),
        provenance=records[0].provenance if records else None,
        comparison_artifact_id=(
            None if comparison_evidence is None else comparison_evidence[0].identity
        ),
    )
    return _load_published_metric_values(result)


def _load_published_metric_values(
    result: ExperimentExecutionResult,
) -> ExperimentExecutionResult:
    if result.provenance is None:
        return _result_with_outcomes(
            result,
            tuple(_outcome_with_metrics(outcome, ()) for outcome in result.outcomes),
        )
    _identity, publication_failures = _metric_evidence_publication_failures(result)
    if publication_failures:
        return _result_with_outcomes(
            result,
            tuple(_outcome_with_metrics(outcome, ()) for outcome in result.outcomes),
        )

    metric_path = experiment_metric_evidence_root(result.experiment) / CELL_METRICS_PARQUET_NAME
    if not metric_artifact_is_semantically_complete(metric_path, result):
        return _result_with_outcomes(
            result,
            tuple(_outcome_with_metrics(outcome, ()) for outcome in result.outcomes),
        )
    metrics_by_cell: defaultdict[ScientificCellSemanticKey, list[MetricObservation]] = defaultdict(
        list
    )
    columns = (
        ReportColumnName.EXPERIMENT,
        ReportColumnName.CELL_SEMANTIC_KEY,
        ReportColumnName.METRIC,
        ReportColumnName.VALUE,
    )
    frame = pandas.read_parquet(metric_path)
    records = cast(
        Iterable[tuple[MetricParquetScalar, ...]],
        frame.loc[:, list(columns)].itertuples(index=False, name=None),
    )
    for row in records:
        raw_experiment, raw_cell_key, raw_metric, raw_value = row
        if raw_experiment != result.experiment:
            continue
        if not isinstance(raw_cell_key, str) or not isinstance(raw_metric, str):
            raise ValueError(f"{result.experiment}: metric evidence identity is malformed")
        cell_key: ScientificCellSemanticKey = raw_cell_key
        metric: MetricName = raw_metric
        if raw_value is None:
            value = None
        elif isinstance(raw_value, int | float):
            numeric_value = float(raw_value)
            value = None if math.isnan(numeric_value) else numeric_value
        else:
            raise ValueError(f"{result.experiment}: metric evidence value is malformed")
        metrics_by_cell[cell_key].append((metric, value))

    expected_keys = frozenset(outcome.cell.semantic_key for outcome in result.outcomes)
    if not frozenset(metrics_by_cell).issubset(expected_keys):
        raise ValueError(f"{result.experiment}: metric evidence contains an unknown cell identity")
    outcomes: list[CellExecutionOutcome] = []
    for outcome in result.outcomes:
        persisted_metrics = tuple(metrics_by_cell.get(outcome.cell.semantic_key, ()))
        if sorted(outcome.metrics) != sorted(persisted_metrics):
            raise ValueError(
                f"{result.experiment}: metric evidence does not match its execution cell"
            )
        outcomes.append(_outcome_with_metrics(outcome, persisted_metrics))
    return _result_with_outcomes(result, tuple(outcomes))


def _outcome_with_metrics(
    outcome: CellExecutionOutcome,
    metrics: tuple[MetricObservation, ...],
) -> CellExecutionOutcome:
    return CellExecutionOutcome(
        cell=outcome.cell,
        terminal_state=outcome.terminal_state,
        failure=outcome.failure,
        metrics=metrics,
        state_trajectory=outcome.state_trajectory,
        scoring_artifact_ids=outcome.scoring_artifact_ids,
    )


def _result_with_outcomes(
    result: ExperimentExecutionResult,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> ExperimentExecutionResult:
    return ExperimentExecutionResult(
        experiment=result.experiment,
        lifecycle_state=result.lifecycle_state,
        outcomes=outcomes,
        comparison_results=result.comparison_results,
        provenance=result.provenance,
        comparison_artifact_id=result.comparison_artifact_id,
    )


def _run_side_metric_evidence_failures(
    result: ExperimentExecutionResult,
) -> tuple[ReportVerificationFailure, ...]:
    identity, publication_failures = _metric_evidence_publication_failures(result)
    failures = list(publication_failures)
    if identity is None:
        return tuple(failures)
    for filename in experiment_by_name(result.experiment).artifacts.required_metric_artifacts:
        candidates = (
            experiment_metric_evidence_root(result.experiment) / filename,
            experiment_telemetry_evidence_root(result.experiment) / filename,
        )
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None or not metric_artifact_is_semantically_complete(path, result):
            failures.append(
                f"{result.experiment}: required run-side metric evidence is missing or invalid: "
                f"{filename}"
            )
    return tuple(failures)


def _to_failure_detail(failure: PersistedFailureDetail | None) -> FailureDetail | None:
    if failure is None:
        return None
    return FailureDetail(
        failure_class=failure.failure_class, message=failure.message, cell_phase=failure.cell_phase
    )


def _load_collapse_decisions(store: ExecutionRecordStore) -> tuple[CollapseDecision, ...] | None:
    config = current_application_context().scientific_config
    plan = build_plan(resolved_core_complete=_resolved_core_complete())
    decisions: list[CollapseDecision] = []
    for experiment in COLLAPSE_EXPERIMENT_NAMES:
        records = current_execution_records(
            plan.experiment(experiment),
            store.read_all_outcomes(experiment),
            dataset_readiness(),
        )
        if not records:
            return None
        evaluation = collapse_evaluation_from_records(experiment, records)
        if evaluation is None:
            return None
        comparison_evidence = current_comparison_evidence(experiment, records)
        if comparison_evidence is None:
            return None
        comparison_results = comparison_evidence[1].families
        matched_family = next(
            (result.family for result in comparison_results if result.family in _COLLAPSE_FAMILIES),
            None,
        )
        if matched_family is None:
            return None
        decisions.append(
            collapse_decision_from_comparison_families(
                matched_family,
                comparison_results,
                evaluation=evaluation,
                materiality_config=config.metrics_and_statistics.materiality,
            )
        )
    if len(decisions) != len(COLLAPSE_EXPERIMENT_NAMES):
        return None
    return tuple(decisions)


COMPARISONS_PARQUET_NAME = "comparisons.parquet"
TIMINGS_PARQUET_NAME = "timings.parquet"
RESOURCES_PARQUET_NAME = "resources.parquet"

_TIMING_METRICS: frozenset[MetricName] = frozenset(
    (
        DelayPhaseMetric.ASSIGNMENT_SECONDS,
        DelayPhaseMetric.REPRODUCE_SECONDS,
        DelayPhaseMetric.VERIFY_SECONDS,
        DelayPhaseMetric.SYNTHESIZE_SECONDS,
        DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
    )
)
_RESOURCE_METRICS: frozenset[MetricName] = frozenset(
    (
        DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
        DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES,
        DescriptiveScientificMetric.COMMUNICATION_BYTES,
        DescriptiveScientificMetric.MODEL_TRANSMISSIONS,
    )
)
MetricParquetScalar: TypeAlias = str | float | int | None


class MetricEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    dataset: DatasetId
    cell_semantic_key: ScientificCellSemanticKey
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    repetition: RepetitionIndex | None
    terminal_state: ExperimentLifecycleState
    metric: MetricName
    value: MetricValue | None
    configuration_digest: ArtifactDigest
    code_revision: CodeRevision | None
    dataset_manifest_hash: ArtifactDigest
    scoring_artifact_ids: tuple[ArtifactDigest, ...]

    @property
    def observation_id(self) -> ArtifactDigest:
        return hashlib.sha256(self.model_dump_json().encode("utf-8")).hexdigest()

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        DatasetId,
        ScientificCellSemanticKey,
        MethodName,
        ScenarioName,
        MasterSeed,
        RepetitionIndex | None,
        ExperimentLifecycleState,
        MetricName,
        MetricValue | None,
        ArtifactDigest,
        ArtifactDigest,
        CodeRevision | None,
        ArtifactDigest,
        tuple[ArtifactDigest, ...],
    ]:
        return (
            self.experiment,
            self.dataset,
            self.cell_semantic_key,
            self.method,
            self.condition,
            self.master_seed,
            self.repetition,
            self.terminal_state,
            self.metric,
            self.value,
            self.observation_id,
            self.configuration_digest,
            self.code_revision,
            self.dataset_manifest_hash,
            self.scoring_artifact_ids,
        )


class StateTrajectoryEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    repetition: RepetitionIndex | None
    logical_evidence_cycle: EvidenceCycleIndex
    admission_state: AdmissionState

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        MethodName,
        ScenarioName,
        MasterSeed,
        RepetitionIndex | None,
        EvidenceCycleIndex,
        AdmissionState,
    ]:
        return (
            self.experiment,
            self.method,
            self.condition,
            self.master_seed,
            self.repetition,
            self.logical_evidence_cycle,
            self.admission_state,
        )


class ComparisonEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    family: ComparisonFamily
    comparison: ComparisonName
    method: MethodName
    scenario: ScenarioName
    metric: MetricName
    complete_seed_count: ScientificCellCount
    mean_paired_difference: MetricValue | None
    adjusted_p_value: MetricValue | None
    state: ComparisonState
    comparison_artifact_id: ArtifactDigest | None
    paired_master_seeds: tuple[MasterSeed, ...]
    source_cell_semantic_keys: ScientificCellSemanticKeyTuple

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        ComparisonFamily,
        ComparisonName,
        MethodName,
        ScenarioName,
        MetricName,
        ScientificCellCount,
        MetricValue | None,
        MetricValue | None,
        ComparisonState,
        ArtifactDigest | None,
        tuple[MasterSeed, ...],
        ScientificCellSemanticKeyTuple,
    ]:
        return (
            self.experiment,
            self.family,
            self.comparison,
            self.method,
            self.scenario,
            self.metric,
            self.complete_seed_count,
            self.mean_paired_difference,
            self.adjusted_p_value,
            self.state,
            self.comparison_artifact_id,
            self.paired_master_seeds,
            self.source_cell_semantic_keys,
        )


class ExperimentEvidenceMaterialization(FrozenDomainModel):
    paths: tuple[RepositoryPath, ...]


def _metric_rows(
    experiment: ExperimentName,
    outcomes: tuple[CellExecutionOutcome, ...],
    provenance: ExecutionProvenance,
) -> tuple[MetricEvidenceRow, ...]:
    return tuple(
        MetricEvidenceRow(
            experiment=experiment,
            dataset=experiment_by_name(experiment).dataset,
            cell_semantic_key=outcome.cell.semantic_key,
            method=outcome.cell.method,
            condition=outcome.cell.condition,
            master_seed=outcome.cell.master_seed,
            repetition=outcome.cell.repetition,
            terminal_state=outcome.terminal_state,
            metric=metric,
            value=value,
            configuration_digest=provenance.configuration_digest,
            code_revision=provenance.code_revision,
            dataset_manifest_hash=provenance.dataset_manifest_hash,
            scoring_artifact_ids=outcome.scoring_artifact_ids,
        )
        for outcome in outcomes
        for metric, value in outcome.metrics
    )


_MALICIOUS_ADMISSION_ABSENT: MetricValue = 0.0
_MALICIOUS_ADMISSION_PRESENT: MetricValue = 1.0


def _binary_malicious_admission_indicators(
    seed_values: tuple[MetricValue, ...],
) -> tuple[AdmissionIndicator, ...]:
    indicators: list[AdmissionIndicator] = []
    for value in seed_values:
        if value == _MALICIOUS_ADMISSION_PRESENT:
            indicators.append(True)
        elif value == _MALICIOUS_ADMISSION_ABSENT:
            indicators.append(False)
        else:
            raise ValueError(
                "malicious admission seed values must be binary admission-rate indicators"
            )
    return tuple(indicators)


def _aggregate_rows(
    rows: tuple[SeedMetricEvidenceRow, ...],
) -> tuple[AggregateMetricEvidenceRow, ...]:
    rows_by_identity: defaultdict[
        tuple[ExperimentName, MethodName, ScenarioName, MetricName], list[SeedMetricEvidenceRow]
    ] = defaultdict(list)
    for row in rows:
        rows_by_identity[(row.experiment, row.method, row.condition, row.metric)].append(row)
    aggregates: list[AggregateMetricEvidenceRow] = []
    for (experiment, method, condition, metric), unsorted_source_rows in sorted(
        rows_by_identity.items()
    ):
        source_rows = tuple(
            sorted(
                unsorted_source_rows,
                key=lambda row: (row.master_seed,),
            )
        )
        summary = summarize_seed_values(tuple(row.value for row in source_rows))
        if summary is None:
            continue
        seed_values = tuple(row.value for row in source_rows)
        mean_value = summary.mean
        if metric == ComparisonMetric.MALICIOUS_ADMISSION:
            indicators = _binary_malicious_admission_indicators(seed_values)
            rate_value = malicious_admission_rate(indicators).value
            if rate_value is None:
                raise ValueError(
                    "malicious admission seed values must be binary admission-rate indicators"
                )
            mean_value = rate_value
        sample_standard_deviation = (
            0.0
            if len(seed_values) < MINIMUM_SEEDS_FOR_SAMPLE_STANDARD_DEVIATION
            else math.sqrt(
                sum((value - summary.mean) ** 2 for value in seed_values) / (len(seed_values) - 1)
            )
        )
        interval: tuple[MetricValue, MetricValue] | None = None
        if (
            experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME
            and metric == ComparisonMetric.TARGET_F1
        ) or (
            experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
            and metric in (ComparisonMetric.ATTACK_SUCCESS_RATE, ComparisonMetric.TARGET_F1)
        ):
            config = current_application_context().scientific_config
            interval = bootstrap_percentile_confidence_interval(
                seed_values,
                config.metrics_and_statistics.bootstrap,
                config.seeds_and_determinism.analysis_seed,
            )
        aggregates.append(
            AggregateMetricEvidenceRow(
                experiment=experiment,
                method=method,
                condition=condition,
                metric=metric,
                observation_count=sum(len(row.source_observation_ids) for row in source_rows),
                seed_count=summary.seed_count,
                mean_value=mean_value,
                sample_standard_deviation=sample_standard_deviation,
                median_value=summary.median,
                first_quartile=summary.first_quartile,
                third_quartile=summary.third_quartile,
                confidence_interval_lower=None if interval is None else interval[0],
                confidence_interval_upper=None if interval is None else interval[1],
                source_observation_ids=tuple(
                    source_id for row in source_rows for source_id in row.source_observation_ids
                ),
                source_cell_semantic_keys=tuple(
                    cell_key for row in source_rows for cell_key in row.source_cell_semantic_keys
                ),
            )
        )
    return tuple(aggregates)


def _seed_metric_rows(
    rows: tuple[MetricEvidenceRow, ...],
) -> tuple[SeedMetricEvidenceRow, ...]:
    by_seed: defaultdict[
        tuple[ExperimentName, DatasetId, MethodName, ScenarioName, MasterSeed, MetricName],
        list[MetricEvidenceRow],
    ] = defaultdict(list)
    for row in rows:
        if row.terminal_state is ExperimentLifecycleState.COMPLETED and row.value is not None:
            by_seed[
                (
                    row.experiment,
                    row.dataset,
                    row.method,
                    row.condition,
                    row.master_seed,
                    row.metric,
                )
            ].append(row)
    seed_rows: list[SeedMetricEvidenceRow] = []
    for identity, source_rows in sorted(by_seed.items()):
        experiment, dataset, method, condition, master_seed, metric = identity
        values = tuple(row.value for row in source_rows if row.value is not None)
        value = (
            quantile_type7(tuple(sorted(values)), 0.5)
            if experiment == EFFICIENCY_MEASUREMENT_NAME and metric in EFFICIENCY_METRICS
            else sum(values) / len(values)
        )
        provenance_rows = tuple(sorted(source_rows, key=lambda row: row.cell_semantic_key))
        first = provenance_rows[0]
        if any(
            row.configuration_digest != first.configuration_digest
            or row.code_revision != first.code_revision
            or row.dataset_manifest_hash != first.dataset_manifest_hash
            for row in provenance_rows
        ):
            raise ValueError(f"{experiment}: inconsistent provenance among seed metric rows")
        seed_rows.append(
            SeedMetricEvidenceRow(
                experiment=experiment,
                dataset=dataset,
                method=method,
                condition=condition,
                master_seed=master_seed,
                metric=metric,
                value=value,
                configuration_digest=first.configuration_digest,
                code_revision=first.code_revision,
                dataset_manifest_hash=first.dataset_manifest_hash,
                scoring_artifact_ids=tuple(
                    sorted({item for row in provenance_rows for item in row.scoring_artifact_ids})
                ),
                source_observation_ids=tuple(row.observation_id for row in provenance_rows),
                source_cell_semantic_keys=tuple(row.cell_semantic_key for row in provenance_rows),
            )
        )
    return tuple(seed_rows)


def _state_trajectory_rows(
    experiment: ExperimentName,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[StateTrajectoryEvidenceRow, ...]:
    return tuple(
        StateTrajectoryEvidenceRow(
            experiment=experiment,
            method=outcome.cell.method,
            condition=outcome.cell.condition,
            master_seed=outcome.cell.master_seed,
            repetition=outcome.cell.repetition,
            logical_evidence_cycle=observation.cycle,
            admission_state=observation.state,
        )
        for outcome in outcomes
        for observation in outcome.state_trajectory
    )


def _comparison_rows(
    experiment: ExperimentName,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    comparison_artifact_id: ArtifactDigest | None,
) -> tuple[ComparisonEvidenceRow, ...]:
    return tuple(
        ComparisonEvidenceRow(
            experiment=experiment,
            family=family.family,
            comparison=comparison.definition.comparison_name,
            method=comparison.definition.method,
            scenario=comparison.definition.scientific_scenario,
            metric=comparison.definition.metric,
            complete_seed_count=comparison.complete_seed_count,
            mean_paired_difference=comparison.mean_paired_difference,
            adjusted_p_value=comparison.adjusted_p_value,
            state=comparison.comparison_state,
            comparison_artifact_id=comparison_artifact_id,
            paired_master_seeds=comparison.paired_master_seeds,
            source_cell_semantic_keys=_comparison_source_semantic_keys(comparison),
        )
        for family in comparison_results
        for comparison in family.comparisons
    )


def _comparison_source_semantic_keys(
    comparison: ComparisonResult,
) -> ScientificCellSemanticKeyTuple:
    definition = comparison.definition
    keys: list[ScientificCellSemanticKey] = []
    for seed in comparison.paired_master_seeds:
        keys.append(
            ScientificCell(
                experiment=definition.experiment,
                method=definition.method,
                condition=definition.scientific_scenario,
                master_seed=seed,
            ).semantic_key
        )
        if definition.reference_kind is ComparisonReferenceKind.SCIENTIFIC_CELL:
            keys.append(
                ScientificCell(
                    experiment=definition.reference_experiment,
                    method=definition.reference_method,
                    condition=definition.reference_scenario,
                    master_seed=seed,
                ).semantic_key
            )
    return tuple(keys)


def _write_metric_parquet(destination: Path, rows: tuple[MetricEvidenceRow, ...]) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            ReportColumnName.EXPERIMENT,
            ReportColumnName.DATASET,
            ReportColumnName.CELL_SEMANTIC_KEY,
            ReportColumnName.METHOD,
            ReportColumnName.CONDITION,
            ReportColumnName.MASTER_SEED,
            ReportColumnName.REPETITION,
            ReportColumnName.TERMINAL_STATE,
            ReportColumnName.METRIC,
            ReportColumnName.VALUE,
            ReportColumnName.OBSERVATION_ID,
            ReportColumnName.CONFIGURATION_DIGEST,
            ReportColumnName.CODE_REVISION,
            ReportColumnName.DATASET_MANIFEST_HASH,
            ReportColumnName.SCORING_ARTIFACT_IDS,
        ),
    )
    frame.to_parquet(destination, index=False)
    return destination


def _write_seed_metric_parquet(
    destination: Path,
    rows: tuple[SeedMetricEvidenceRow, ...],
) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            ReportColumnName.EXPERIMENT,
            ReportColumnName.DATASET,
            ReportColumnName.METHOD,
            ReportColumnName.CONDITION,
            ReportColumnName.MASTER_SEED,
            ReportColumnName.METRIC,
            ReportColumnName.VALUE,
            ReportColumnName.CONFIGURATION_DIGEST,
            ReportColumnName.CODE_REVISION,
            ReportColumnName.DATASET_MANIFEST_HASH,
            ReportColumnName.SCORING_ARTIFACT_IDS,
            ReportColumnName.SOURCE_OBSERVATION_IDS,
            ReportColumnName.SOURCE_CELL_SEMANTIC_KEYS,
        ),
    )
    frame.to_parquet(destination, index=False)
    return destination


def _write_aggregate_metric_parquet(
    destination: Path,
    rows: tuple[AggregateMetricEvidenceRow, ...],
) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            ReportColumnName.EXPERIMENT,
            ReportColumnName.METHOD,
            ReportColumnName.CONDITION,
            ReportColumnName.METRIC,
            ReportColumnName.OBSERVATION_COUNT,
            ReportColumnName.SEED_COUNT,
            ReportColumnName.MEAN_VALUE,
            ReportColumnName.SAMPLE_STANDARD_DEVIATION,
            ReportColumnName.MEDIAN_VALUE,
            ReportColumnName.FIRST_QUARTILE,
            ReportColumnName.THIRD_QUARTILE,
            ReportColumnName.CONFIDENCE_INTERVAL_LOWER,
            ReportColumnName.CONFIDENCE_INTERVAL_UPPER,
            ReportColumnName.SOURCE_OBSERVATION_IDS,
            ReportColumnName.SOURCE_CELL_SEMANTIC_KEYS,
        ),
    )
    frame.to_parquet(destination, index=False)
    return destination


def _write_state_trajectory_parquet(
    destination: Path,
    rows: tuple[StateTrajectoryEvidenceRow, ...],
) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            ReportColumnName.EXPERIMENT,
            ReportColumnName.METHOD,
            ReportColumnName.CONDITION,
            ReportColumnName.MASTER_SEED,
            ReportColumnName.REPETITION,
            ReportColumnName.LOGICAL_EVIDENCE_CYCLE,
            ReportColumnName.ADMISSION_STATE,
        ),
    )
    frame.to_parquet(destination, index=False)
    return destination


def _write_comparison_parquet(destination: Path, rows: tuple[ComparisonEvidenceRow, ...]) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            ReportColumnName.EXPERIMENT,
            ReportColumnName.FAMILY,
            ReportColumnName.COMPARISON,
            ReportColumnName.METHOD,
            ReportColumnName.SCENARIO,
            ReportColumnName.METRIC,
            ReportColumnName.COMPLETE_SEED_COUNT,
            ReportColumnName.MEAN_PAIRED_DIFFERENCE,
            ReportColumnName.ADJUSTED_P_VALUE,
            ReportColumnName.STATE,
            ReportColumnName.COMPARISON_ARTIFACT_ID,
            ReportColumnName.COMPLETE_SEEDS,
            ReportColumnName.SOURCE_CELL_SEMANTIC_KEYS,
        ),
    )
    frame.to_parquet(destination, index=False)
    return destination


def materialize_experiment_evidence(
    result: ExperimentExecutionResult,
    metrics_root: Path,
    telemetry_root: Path,
) -> ExperimentEvidenceMaterialization:
    metrics_root.mkdir(parents=True, exist_ok=True)
    telemetry_root.mkdir(parents=True, exist_ok=True)
    if result.provenance is None:
        raise ValueError(f"{result.experiment}: current execution provenance is missing")
    rows = _metric_rows(result.experiment, result.outcomes, result.provenance)
    seed_rows = _seed_metric_rows(rows)
    paths: list[Path] = [
        _write_metric_parquet(metrics_root / CELL_METRICS_PARQUET_NAME, rows),
        _write_seed_metric_parquet(metrics_root / SEED_METRICS_PARQUET_NAME, seed_rows),
        _write_aggregate_metric_parquet(
            metrics_root / AGGREGATE_METRICS_PARQUET_NAME,
            _aggregate_rows(seed_rows),
        ),
    ]
    comparison_rows = _comparison_rows(
        result.experiment,
        result.comparison_results,
        result.comparison_artifact_id,
    )
    trajectory_rows = _state_trajectory_rows(result.experiment, result.outcomes)
    if trajectory_rows:
        paths.append(
            _write_state_trajectory_parquet(
                metrics_root / STATE_TRAJECTORY_PARQUET_NAME,
                trajectory_rows,
            )
        )
    trajectory_fraction_rows = state_trajectory_fraction_rows(
        result.experiment,
        result.outcomes,
    )
    if trajectory_fraction_rows:
        paths.append(
            write_state_trajectory_fraction_parquet(
                metrics_root / STATE_TRAJECTORY_FRACTIONS_PARQUET_NAME,
                trajectory_fraction_rows,
            )
        )
    if comparison_rows:
        paths.append(
            _write_comparison_parquet(
                metrics_root / COMPARISONS_PARQUET_NAME,
                comparison_rows,
            )
        )
    for filename, metric_names in (
        (TIMINGS_PARQUET_NAME, _TIMING_METRICS),
        (RESOURCES_PARQUET_NAME, _RESOURCE_METRICS),
    ):
        telemetry_rows = tuple(row for row in rows if row.metric in metric_names)
        if telemetry_rows:
            paths.append(_write_metric_parquet(telemetry_root / filename, telemetry_rows))
    return ExperimentEvidenceMaterialization(paths=tuple(str(path) for path in paths))


def render_mandatory_tables(
    plan: ExperimentPlan,
    collapse_decisions: tuple[CollapseDecision, ...] | None,
    resolved_core: ResolvedCore | None,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    outcomes: tuple[CellExecutionOutcome, ...],
    efficiency_observations: tuple[EfficiencyMetricObservation, ...],
) -> tuple[RenderedTable, ...]:
    tables = [
        render_dataset_and_domain_protocol_table(),
        render_primary_domain_statistics_table(),
        render_model_and_training_protocol_table(),
        render_security_and_capability_contract_protocol_table(),
        render_baseline_protocol_table(),
        render_experiment_plan_table(plan),
        render_metric_and_statistics_protocol_table(),
        render_primary_results_table(comparison_results, outcomes),
        render_source_exclusion_results_table(
            comparison_results,
            outcomes,
            collapse_decisions,
        ),
    ]
    if collapse_decisions is not None and resolved_core is not None:
        tables.append(render_collapse_decisions_table(collapse_decisions, resolved_core))
    tables.extend(
        (
            render_ablation_results_table(comparison_results, outcomes),
            render_byzantine_robustness_table(comparison_results, outcomes),
            render_failure_boundaries_table(comparison_results, outcomes),
            render_delay_and_efficiency_table(
                comparison_results, outcomes, efficiency_observations
            ),
            render_generalization_results_table(comparison_results, outcomes),
            render_statistical_summary_table(comparison_results),
        )
    )
    return tuple(tables)
