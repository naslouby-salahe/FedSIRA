from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas

from fedsira.artifacts.paths import (
    RESULTS_ROOT,
    artifact_publication_root,
    execution_outputs_root,
    experiment_metrics_root,
    experiment_result_root,
    experiment_telemetry_root,
    manuscript_figures_root,
    manuscript_tables_root,
    preprocessing_log_path,
    preprocessing_root,
    project_summary_root,
    workspace_root_for_family,
)
from fedsira.artifacts.provenance import load_published_manifests
from fedsira.domain.enums import ArtifactFamily, ExperimentLifecycleState
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    ExperimentName,
    FigureName,
    FrozenDomainModel,
    OverwriteExisting,
    ReportVerificationFailure,
    RepositoryPath,
    SchemaVersion,
    ScientificCellCount,
    TableName,
    VerificationPassed,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.evaluation.service import comparison_results_for_experiment
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
    COLLAPSE_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    STATE_TRAJECTORY_PARQUET_NAME,
    ComparisonFamily,
    experiment_by_name,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedFailureDetail,
    derive_experiment_lifecycle,
)
from fedsira.experiments.planning import (
    ExperimentPlan,
    ScientificCell,
    build_plan,
    validate_planned_cell_count_invariant,
)
from fedsira.reporting import tables as table_renderers
from fedsira.reporting.figures import (
    EfficiencyMetricObservation,
    EvidenceStateFraction,
    render_experiment_figures,
    render_mandatory_figures,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.materialization import (
    materialize_experiment_evidence,
)
from fedsira.reporting.project_evidence import efficiency_telemetry as project_efficiency_telemetry
from fedsira.reporting.project_evidence import evidence_trajectory as project_evidence_trajectory
from fedsira.reporting.project_evidence import outcome_evidence_trajectory, project_result_evidence
from fedsira.reporting.rendering import RenderedTable
from fedsira.reporting.tables import (
    MANUSCRIPT_TABLE_NAMES,
    render_experiment_cell_metrics_table,
    render_mandatory_tables,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
    ExperimentTerminalCount,
    artifact_manifest_dependency_failures,
    table_header,
    terminal_count_for_planned_experiment,
    verify_artifact_manifest_dependencies,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_mandatory_figure_source_data,
    verify_planned_cell_count_satisfied,
    verify_rendered_table,
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
)

EXPORT_SCHEMA_VERSION: SchemaVersion = "fedsira|report_export|1"

REPORT_LOGGER = get_structured_logger("reporting")

PROJECT_SUMMARY_EXPORT_NAME: ExperimentName = "project summary"


class ReportLogFields(FrozenDomainModel):
    report_scope: ExperimentName
    artifact_count: ScientificCellCount | None = None


_RESULT_TABLE_EVIDENCE: tuple[tuple[TableName, tuple[ExperimentName, ...]], ...] = (
    ("Primary Results", (PRIMARY_CONFIRMATORY_EVALUATION_NAME,)),
    ("Source-Exclusion Results", (SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,)),
    ("Ablation Results", (MECHANISM_ABLATION_NAME,)),
    (
        "Byzantine Robustness",
        (
            COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
            COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
            BYZANTINE_BOUND_VIOLATION_NAME,
        ),
    ),
    (
        "Failure Boundaries",
        (
            EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        ),
    ),
    (
        "Delay and Efficiency",
        (
            ADMISSION_DELAY_DECOMPOSITION_NAME,
            EFFICIENCY_MEASUREMENT_NAME,
        ),
    ),
    ("Generalization Results", (SECONDARY_DATASET_GENERALIZATION_NAME,)),
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


class ReportExportResult(FrozenDomainModel):
    experiment: ExperimentName | None
    exported_paths: tuple[RepositoryPath, ...]
    verification: CompletenessVerificationResult


def _write_table(root: Path, table: RenderedTable) -> Path:
    destination = root / f"{table.name}.csv"
    destination.write_text(table.csv_text + "\n")
    return destination


def _metric_artifact_is_semantically_complete(
    path: Path,
    result: ExperimentExecutionResult,
) -> BooleanValue:
    if not path.is_file():
        return False
    frame = pandas.read_parquet(path)
    if path.name == STATE_TRAJECTORY_PARQUET_NAME:
        required_columns = frozenset(
            (
                "experiment",
                "method",
                "condition",
                "master_seed",
                "logical_evidence_cycle",
                "admission_state",
            )
        )
        if not required_columns.issubset(frame.columns) or frame.empty:
            return False
        experiment_rows = frame[frame["experiment"] == result.experiment]
        expected_cells = frozenset(
            (outcome.cell.method, outcome.cell.condition, outcome.cell.master_seed)
            for outcome in result.outcomes
        )
        observed_cells = frozenset(
            (row.method, row.condition, row.master_seed) for row in experiment_rows.itertuples()
        )
        return expected_cells.issubset(observed_cells) and bool(
            experiment_rows["admission_state"].notna().all()
        )
    required_columns = (
        frozenset(
            ("experiment", "method", "condition", "metric", "observation_count", "mean_value")
        )
        if path.name == AGGREGATE_METRICS_PARQUET_NAME
        else frozenset(("experiment", "method", "condition", "master_seed", "terminal_state"))
    )
    if not required_columns.issubset(frame.columns) or frame.empty:
        return False
    experiment_rows = frame[frame["experiment"] == result.experiment]
    if experiment_rows.empty:
        return False
    if path.name == AGGREGATE_METRICS_PARQUET_NAME:
        expected_conditions = frozenset(
            (outcome.cell.method, outcome.cell.condition) for outcome in result.outcomes
        )
        observed_conditions = frozenset(
            (row.method, row.condition) for row in experiment_rows.itertuples()
        )
        return expected_conditions.issubset(observed_conditions) and bool(
            (experiment_rows["observation_count"] > 0).all()
        )
    terminal_state_values = cast(list[str], experiment_rows["terminal_state"].tolist())
    recorded_terminal_states = frozenset(
        ExperimentLifecycleState(state) for state in terminal_state_values
    )
    if recorded_terminal_states != frozenset((ExperimentLifecycleState.COMPLETED,)):
        return False
    expected_cells = frozenset(
        (outcome.cell.method, outcome.cell.condition, outcome.cell.master_seed)
        for outcome in result.outcomes
    )
    observed_cells = frozenset(
        (row.method, row.condition, row.master_seed) for row in experiment_rows.itertuples()
    )
    return expected_cells.issubset(observed_cells)


def verify_experiment_artifacts(
    result: ExperimentExecutionResult,
    tables_root: Path,
    figures_root: Path,
    metrics_root: Path,
    summary_path: Path,
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
        if not _metric_artifact_is_semantically_complete(path, result):
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
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


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

    tables_root = manuscript_tables_root(experiment_root)
    figures_root = manuscript_figures_root(experiment_root)
    metrics_root = experiment_metrics_root(experiment_root)
    telemetry_root = experiment_telemetry_root(experiment_root)
    tables_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)
    metrics_root.mkdir(parents=True, exist_ok=True)
    telemetry_root.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = [
        _write_table(tables_root, render_experiment_cell_metrics_table(result.outcomes)),
        *render_experiment_figures(
            result,
            figures_root,
            outcome_evidence_trajectory(result.outcomes)
            if result.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME
            else (),
            project_efficiency_telemetry(result.outcomes)
            if result.experiment == EFFICIENCY_MEASUREMENT_NAME
            else (),
        ),
    ]
    log_structured_event(
        REPORT_LOGGER,
        "report.experiment.artifacts.rendered",
        ReportLogFields(report_scope=result.experiment, artifact_count=len(exported)),
    )
    evidence = materialize_experiment_evidence(result, metrics_root, telemetry_root)
    exported.extend(Path(path) for path in evidence.paths)
    if result.comparison_results:
        statistical_table = table_renderers.render_statistical_summary_table(
            result.comparison_results,
        )
        exported.append(_write_table(tables_root, statistical_table))

    summary = ExperimentReportSummary(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment=result.experiment,
        lifecycle_state=result.lifecycle_state,
        completed_cell_count=result.cell_completion_count,
        planned_cell_count=len(result.outcomes),
        execution_digest=result.execution_digest,
    )
    summary_path = metrics_root / "summary.json"
    summary_path.write_text(summary.model_dump_json(indent=2) + "\n")
    exported.append(summary_path)
    manifest_path = experiment_root / "manifest.json"
    manifest = ExperimentArtifactManifest(
        schema_version=EXPORT_SCHEMA_VERSION,
        experiment=result.experiment,
        lifecycle_state=result.lifecycle_state,
        execution_digest=result.execution_digest,
        artifacts=tuple(str(path) for path in exported),
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
    exported.append(manifest_path)
    verification = verify_experiment_artifacts(
        result,
        tables_root,
        figures_root,
        metrics_root,
        summary_path,
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

    project_root = project_summary_root()
    tables_root = manuscript_tables_root(project_root)
    reproducibility_root = project_root / "reproducibility" / "execution"
    figures_root = manuscript_figures_root(project_root)
    for directory in (tables_root, reproducibility_root, figures_root):
        directory.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    materialized_tables: list[TableName] = []

    log_structured_event(
        REPORT_LOGGER,
        "report.project.tables.started",
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

    exported.extend(
        render_mandatory_figures(
            comparison_results,
            figures_root,
            evidence_trajectory=evidence_trajectory,
            telemetry=telemetry,
            outcomes=outcomes,
        )
    )

    pending_tables = tuple(
        name for name in MANUSCRIPT_TABLE_NAMES if name not in materialized_tables
    )
    pending_figures = validate_mandatory_figures_covered(tuple(exported))
    material_failures = _report_material_failures(pending_tables, pending_figures)
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
    )
    reproducibility_path = reproducibility_root / "execution_summary.json"
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
        configure_structured_file_logging(REPORT_LOGGER, REPOSITORY_ROOT / preprocessing_log_path())
        scope = name if name is not None else PROJECT_SUMMARY_EXPORT_NAME
        fields = ReportLogFields(report_scope=scope)
        log_structured_event(REPORT_LOGGER, "report.started", fields)
        _execute_bound(name, overwrite)
        log_structured_event(REPORT_LOGGER, "report.completed", fields)


def _execute_bound(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
    config = current_application_context().scientific_config
    store = ExecutionRecordStore(
        REPOSITORY_ROOT / Path(config.execution.repository_layout.execution_workspace)
    )
    if name is not None:
        result = _load_experiment_result(name, store)
        experiment_root = REPOSITORY_ROOT / experiment_result_root(name)
        if overwrite and experiment_root.exists():
            for child in experiment_root.rglob("*"):
                if child.is_file():
                    child.unlink()
        export = export_experiment_report(result, experiment_root)
        for path in export.exported_paths:
            print(f"exported {path}")
        if not export.verification.passed:
            raise SystemExit(1)
        return
    resolved_core_complete = _resolved_core_complete()
    plan = build_plan(resolved_core_complete=resolved_core_complete)
    validate_planned_cell_count_invariant(plan)
    terminal_counts: list[ExperimentTerminalCount] = []
    lifecycle_states: list[ExperimentLifecycleRecord] = []
    for planned in plan.experiments:
        records = store.read_all_outcomes(planned.definition.name)
        terminal_counts.append(
            ExperimentTerminalCount(
                experiment=planned.definition.name,
                count=terminal_count_for_planned_experiment(planned, records),
            )
        )
        lifecycle_states.append(
            ExperimentLifecycleRecord(
                experiment=planned.definition.name,
                state=derive_experiment_lifecycle(planned, records),
            )
        )
    terminal_count_records = tuple(terminal_counts)
    lifecycle_records = tuple(lifecycle_states)
    experiment_names = tuple(planned.definition.name for planned in plan.experiments)
    count_verification = verify_planned_cell_count_satisfied(plan, terminal_count_records)
    completion_verification = verify_experiments_completed(lifecycle_records, experiment_names)
    terminal_verification = verify_experiments_reached_terminal_state(
        lifecycle_records, experiment_names
    )
    artifact_roots = (
        REPOSITORY_ROOT / preprocessing_root(),
        REPOSITORY_ROOT / artifact_publication_root(),
        REPOSITORY_ROOT / execution_outputs_root(),
        REPOSITORY_ROOT / RESULTS_ROOT,
    )
    manifest_dependency_verification = verify_artifact_manifest_dependencies(
        artifact_manifest_dependency_failures(load_published_manifests(artifact_roots))
    )
    failures = (
        *count_verification.failures,
        *completion_verification.failures,
        *terminal_verification.failures,
        *manifest_dependency_verification.failures,
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
    directory = REPOSITORY_ROOT / workspace_root_for_family(
        ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION
    )
    return read_resolved_core(directory) is not None


def _load_experiment_result(
    name: ExperimentName, store: ExecutionRecordStore
) -> ExperimentExecutionResult:
    definition = experiment_by_name(name)
    plan = build_plan(resolved_core_complete=_resolved_core_complete())
    records = store.read_all_outcomes(name)
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
        )
        for record in records
    )
    comparisons = comparison_results_for_experiment(name, definition.dataset, outcomes, store)
    return ExperimentExecutionResult(
        experiment=name,
        lifecycle_state=derive_experiment_lifecycle(plan.experiment(name), records),
        outcomes=outcomes,
        comparison_results=comparisons,
    )


def _to_failure_detail(failure: PersistedFailureDetail | None) -> FailureDetail | None:
    if failure is None:
        return None
    return FailureDetail(
        failure_class=failure.failure_class, message=failure.message, cell_phase=failure.cell_phase
    )


def _load_collapse_decisions(store: ExecutionRecordStore) -> tuple[CollapseDecision, ...] | None:
    config = current_application_context().scientific_config
    decisions: list[CollapseDecision] = []
    for experiment in COLLAPSE_EXPERIMENT_NAMES:
        records = store.read_all_outcomes(experiment)
        if not records:
            return None
        evaluation = collapse_evaluation_from_records(experiment, records)
        if evaluation is None:
            return None
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
                failure=None,
                metrics=record.metrics,
                state_trajectory=record.state_trajectory,
            )
            for record in records
        )
        definition = experiment_by_name(experiment)
        comparison_results = comparison_results_for_experiment(
            experiment, definition.dataset, outcomes, store
        )
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
