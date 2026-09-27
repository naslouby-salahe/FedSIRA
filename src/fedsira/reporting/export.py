from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

import pandas

from fedsira.artifacts.paths import (
    artifact_log_path,
    artifact_publication_root,
    current_repository_root,
    execution_outputs_root,
    execution_workspace_root,
    experiment_metrics_root,
    experiment_result_root,
    experiment_telemetry_root,
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
    FigureName,
    LogEvent,
    ReportColumnName,
    RuntimeComponentName,
    TableName,
    WorkspaceFileToken,
)
from fedsira.domain.models import (
    ScientificCell,
)
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    CodeRevision,
    ComparisonName,
    EvidenceCycleIndex,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricName,
    MetricValue,
    OverwriteExisting,
    RelativePathText,
    RepetitionIndex,
    ReportScopeText,
    ReportVerificationFailure,
    RepositoryPath,
    RowCount,
    ScenarioName,
    SchemaVersion,
    ScientificCellCount,
    ScientificCellSemanticKey,
    ScientificCellSemanticKeyTuple,
    TableCsvText,
    VerificationPassed,
)
from fedsira.evaluation.comparison_evidence import current_comparison_evidence
from fedsira.evaluation.comparisons import (
    ComparisonFamilyResult,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
)
from fedsira.evaluation.summaries import ClaimSummary, unevaluated_claim_summary
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
from fedsira.reporting.figures import (
    EfficiencyMetricObservation,
    EvidenceStateFraction,
    outcome_evidence_trajectory,
    project_result_evidence,
    render_experiment_figures,
    render_mandatory_figures,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.figures import efficiency_telemetry as project_efficiency_telemetry
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
    publish_table_figure_export,
    publish_table_figure_source_data,
    read_table_figure_export,
    read_table_figure_source_data,
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
    run_bounded,
)

EXPORT_SCHEMA_VERSION: SchemaVersion = "fedsira|report_export|3"

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
            outcome_evidence_trajectory(result.outcomes)
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
    export_experiment: ExperimentName,
    source_identity: ArtifactDigest,
    export_source_identity: ArtifactDigest,
    source_experiment: ExperimentName,
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
        candidates = tuple(experiment_root.rglob(item.evidence_name))
        if not candidates or all(
            content_digest(str(path)) != item.content_digest for path in candidates
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
        if not (path := experiment_metrics_root(experiment_root) / filename).is_file()
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
    metrics_root = experiment_metrics_root(experiment_root)
    telemetry_root = experiment_telemetry_root(experiment_root)
    tables_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)
    metrics_root.mkdir(parents=True, exist_ok=True)
    telemetry_root.mkdir(parents=True, exist_ok=True)

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
    figure_paths = render_experiment_figures(
        result,
        figures_root,
        outcome_evidence_trajectory(result.outcomes)
        if result.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME
        else (),
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
    evidence = materialize_experiment_evidence(result, metrics_root, telemetry_root)
    exported.extend(Path(path) for path in evidence.paths)
    source_data_manifest, _source_data_reused = publish_table_figure_source_data(
        result.experiment,
        result.execution_digest,
        tuple(rendered_tables),
        tuple(str(path) for path in figure_paths),
        tuple(str(path) for path in table_paths),
        evidence.paths,
    )

    summary = ExperimentReportSummary(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment=result.experiment,
        lifecycle_state=result.lifecycle_state,
        completed_cell_count=result.cell_completion_count,
        planned_cell_count=len(result.outcomes),
        execution_digest=result.execution_digest,
    )
    summary_path = metrics_root / WorkspaceFileToken.SUMMARY_JSON
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
    exported_relative = tuple(str(path.relative_to(experiment_root)) for path in exported)
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

    claim_summary = unevaluated_claim_summary()
    if any(decision.state is ClaimState.NOT_TESTED for decision in claim_summary.decisions):
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=CompletenessVerificationResult(
                passed=False,
                failures=("Claim states: final evidence-driven decisions are not available",),
            ),
        )

    project_root = project_summary_root()
    tables_root = manuscript_tables_root(project_root)
    reproducibility_root = manuscript_reproducibility_root(project_root)
    figures_root = manuscript_figures_root(project_root)
    for directory in (tables_root, reproducibility_root, figures_root):
        directory.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    materialized_tables: list[TableName] = []

    log_structured_event(
        REPORT_LOGGER,
        LogEvent.REPORT_PROJECT_TABLES_STARTED,
        ReportLogFields(report_scope=PROJECT_SUMMARY_EXPORT_NAME),
    )
    for table in render_mandatory_tables(
        plan,
        collapse_decisions=collapse_decisions,
        resolved_core=resolved_core,
        comparison_results=comparison_results,
        outcomes=outcomes,
    ):
        exported.append(_write_table(tables_root, table))
        materialized_tables.append(table.name)
        log_structured_event(
            REPORT_LOGGER,
            LogEvent.REPORT_TABLE_GENERATED,
            ReportLogFields(report_scope=table.name),
        )
    log_structured_event(
        REPORT_LOGGER,
        LogEvent.REPORT_TABLES_COMPLETED,
        ReportLogFields(
            report_scope=PROJECT_SUMMARY_EXPORT_NAME, artifact_count=len(materialized_tables)
        ),
    )

    log_structured_event(
        REPORT_LOGGER,
        LogEvent.REPORT_FIGURE_STARTED,
        ReportLogFields(report_scope=PROJECT_SUMMARY_EXPORT_NAME),
    )
    mandatory_figures = render_mandatory_figures(
        comparison_results,
        figures_root,
        evidence_trajectory=evidence_trajectory,
        telemetry=telemetry,
        outcomes=outcomes,
    )
    exported.extend(mandatory_figures)
    for figure_path in mandatory_figures:
        log_structured_event(
            REPORT_LOGGER,
            LogEvent.REPORT_FIGURE_GENERATED,
            ReportLogFields(report_scope=Path(figure_path).name),
        )

    pending_tables = tuple(
        name for name in MANUSCRIPT_TABLE_NAMES if name not in materialized_tables
    )
    pending_figures = validate_mandatory_figures_covered(tuple(exported))
    material_failures = (*_report_material_failures(pending_tables, pending_figures),)
    final_verification = CompletenessVerificationResult(
        passed=not material_failures,
        failures=material_failures,
    )
    reproducibility_summary = ProjectReproducibilitySummary(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment_states=lifecycle_states,
        verification_passed=final_verification.passed,
        verification_failures=final_verification.failures,
        mandatory_tables=MANUSCRIPT_TABLE_NAMES,
        materialized_tables=tuple(materialized_tables),
        pending_mandatory_tables=pending_tables,
        pending_mandatory_figures=pending_figures,
        claim_summary=claim_summary,
    )
    reproducibility_path = reproducibility_root / WorkspaceFileToken.EXECUTION_SUMMARY_JSON
    reproducibility_path.write_text(reproducibility_summary.model_dump_json(indent=2) + "\n")
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
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        configure_structured_file_logging(
            REPORT_LOGGER, current_repository_root() / reporting_log_path()
        )
        configure_artifact_logging(current_repository_root() / artifact_log_path())
        scope = name if name is not None else PROJECT_SUMMARY_EXPORT_NAME
        fields = ReportLogFields(report_scope=scope)
        log_structured_event(REPORT_LOGGER, LogEvent.REPORT_STARTED, fields)
        timeout = context.scientific_config.execution.timeouts_seconds.experiment_analysis_or_report
        run_bounded(
            RuntimeComponentName.CREATING_REPORT, timeout, lambda: _execute_bound(name, overwrite)
        )
        log_structured_event(REPORT_LOGGER, LogEvent.REPORT_COMPLETED, fields)


def _execute_bound(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
    store = ExecutionRecordStore(execution_workspace_root())
    if name is not None:
        result = _load_experiment_result(name, store)
        experiment_root = current_repository_root() / experiment_result_root(name)
        export = verify_persisted_experiment_report(result, experiment_root)
        for path in export.exported_paths:
            print(f"verified {path}")
        if not export.verification.passed:
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
        manifest_dependency_verification,
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
            verify_artifact_manifest_dependencies(
                artifact_manifest_dependency_failures(*load_published_manifests(artifact_roots))
            ),
            verify_byzantine_operating_region(
                store.read_all_outcomes(BYZANTINE_BOUND_VIOLATION_NAME)
            ),
            verify_comparison_evidence_current(experiment_names, store),
            verify_safe_dormancy(store.read_all_outcomes(EVIDENCE_SCARCITY_AND_DORMANCY_NAME)),
        ),
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
    verification = CompletenessVerificationResult(passed=not failures, failures=failures)
    collapse_decisions = _load_collapse_decisions(store)
    comparison_results, outcomes = project_result_evidence(
        plan, lambda name: _load_experiment_result(name, store)
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
        evidence_trajectory=project_evidence_trajectory(store),
        telemetry=project_efficiency_telemetry(outcomes),
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
    return ExperimentExecutionResult(
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


class AggregateMetricEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    metric: MetricName
    observation_count: ScientificCellCount
    mean_value: MetricValue
    source_observation_ids: tuple[ArtifactDigest, ...]
    source_cell_semantic_keys: ScientificCellSemanticKeyTuple

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        MethodName,
        ScenarioName,
        MetricName,
        ScientificCellCount,
        MetricValue,
        tuple[ArtifactDigest, ...],
        ScientificCellSemanticKeyTuple,
    ]:
        return (
            self.experiment,
            self.method,
            self.condition,
            self.metric,
            self.observation_count,
            self.mean_value,
            self.source_observation_ids,
            self.source_cell_semantic_keys,
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


def _aggregate_rows(
    rows: tuple[MetricEvidenceRow, ...],
) -> tuple[AggregateMetricEvidenceRow, ...]:
    rows_by_identity: defaultdict[
        tuple[ExperimentName, MethodName, ScenarioName, MetricName], list[MetricEvidenceRow]
    ] = defaultdict(list)
    for row in rows:
        if row.value is not None:
            rows_by_identity[(row.experiment, row.method, row.condition, row.metric)].append(row)
    return tuple(
        AggregateMetricEvidenceRow(
            experiment=experiment,
            method=method,
            condition=condition,
            metric=metric,
            observation_count=len(source_rows),
            mean_value=sum(row.value for row in source_rows if row.value is not None)
            / len(source_rows),
            source_observation_ids=tuple(row.observation_id for row in source_rows),
            source_cell_semantic_keys=tuple(row.cell_semantic_key for row in source_rows),
        )
        for (experiment, method, condition, metric), source_rows in sorted(rows_by_identity.items())
        if source_rows
    )


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
            ReportColumnName.MEAN_VALUE,
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
    paths: list[Path] = [
        _write_metric_parquet(metrics_root / CELL_METRICS_PARQUET_NAME, rows),
        _write_metric_parquet(metrics_root / SEED_METRICS_PARQUET_NAME, rows),
        _write_aggregate_metric_parquet(
            metrics_root / AGGREGATE_METRICS_PARQUET_NAME,
            _aggregate_rows(rows),
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
            render_delay_and_efficiency_table(comparison_results, outcomes),
            render_generalization_results_table(comparison_results, outcomes),
            render_statistical_summary_table(comparison_results),
        )
    )
    return tuple(tables)
