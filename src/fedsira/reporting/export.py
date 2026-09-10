from __future__ import annotations

from pathlib import Path

from fedsira.artifacts.paths import (
    OUTPUTS_ROOT,
    RESULTS_ROOT,
    preprocessing_root,
    workspace_root_for_family,
)
from fedsira.artifacts.provenance import load_published_artifact_graph, stale_artifact_identities
from fedsira.domain.enums import AdmissionState, ArtifactFamily, ExperimentLifecycleState
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    EvidenceCycleIndex,
    ExperimentName,
    FigureName,
    FrozenDomainModel,
    MetricName,
    MetricValue,
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
    ADMISSION_DELAY_DECOMPOSITION_FIGURE_NAME,
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_GRANULARITY_BOUNDARY_FIGURE_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COLLAPSE_DECISION_EFFECTS_FIGURE_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_BOUNDARY_FIGURE_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EFFICIENCY_PROFILE_FIGURE_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    HETEROGENEITY_SYNTHESIS_BOUNDARY_FIGURE_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PRIMARY_SECURITY_UTILITY_TRADEOFF_FIGURE_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SECONDARY_GENERALIZATION_FIGURE_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SHARED_EPISTEMIC_FAILURE_FIGURE_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    USEFUL_BACKDOORED_SOURCE_FIGURE_NAME,
    ComparisonFamily,
    experiment_by_name,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedExecutionRecord,
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
    render_admission_delay_decomposition,
    render_capability_granularity_boundary,
    render_collapse_decision_effects,
    render_compromised_reproducer_boundary,
    render_compromised_verifier_boundary,
    render_efficiency_profile,
    render_heterogeneity_synthesis_boundary,
    render_mandatory_figures,
    render_protocol_schematic,
    render_secondary_generalization,
    render_security_utility_tradeoff,
    render_shared_epistemic_failure,
    render_useful_backdoored_source,
    validate_mandatory_figures_covered,
)
from fedsira.reporting.materialization import (
    materialize_experiment_evidence,
    parquet_contains_rows,
)
from fedsira.reporting.tables import (
    MANUSCRIPT_TABLE_NAMES,
    RenderedTable,
    render_experiment_cell_metrics_table,
    render_mandatory_tables,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
    ExperimentTerminalCount,
    terminal_count_for_planned_experiment,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_no_stale_ancestors,
    verify_planned_cell_count_satisfied,
)
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ApplicationContext,
    FailureDetail,
    bound_application_context,
    current_application_context,
)

EXPORT_SCHEMA_VERSION: SchemaVersion = "fedsira|report_export|1"

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


def _results_root() -> Path:
    return Path("results")


def _write_table(root: Path, table: RenderedTable) -> Path:
    destination = root / f"{table.name}.csv"
    destination.write_text(table.csv_text + "\n")
    return destination


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
        if not parquet_contains_rows(path):
            failures.append(
                f"{result.experiment}: required metric artifact {filename} is missing or empty"
            )
    for table_name in specification.required_tables:
        path = tables_root / f"{table_name}.csv"
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            failures.append(f"{result.experiment}: required table {table_name} is missing or empty")
    for figure_name in specification.required_figures:
        path = figures_root / f"{figure_name}.png"
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(
                f"{result.experiment}: required figure {figure_name} is missing or empty"
            )
    return CompletenessVerificationResult(passed=not failures, failures=tuple(failures))


def _render_specialized_figure(
    result: ExperimentExecutionResult,
    figures_root: Path,
) -> Path | None:
    figure: Path | None = None
    if result.experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
        figure = render_compromised_reproducer_boundary(
            result.comparison_results,
            figures_root / f"{COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
        figure = render_compromised_verifier_boundary(
            result.comparison_results,
            figures_root / f"{COMPROMISED_VERIFIER_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME:
        figure = render_shared_epistemic_failure(
            result.comparison_results,
            figures_root / f"{SHARED_EPISTEMIC_FAILURE_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME:
        figure = render_capability_granularity_boundary(
            result.comparison_results,
            figures_root / f"{CAPABILITY_GRANULARITY_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
        figure = render_heterogeneity_synthesis_boundary(
            result.comparison_results,
            figures_root / f"{HETEROGENEITY_SYNTHESIS_BOUNDARY_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == ADMISSION_DELAY_DECOMPOSITION_NAME:
        figure = render_admission_delay_decomposition(
            result.comparison_results,
            figures_root / f"{ADMISSION_DELAY_DECOMPOSITION_FIGURE_NAME}.png",
            result.outcomes,
        )
    elif result.experiment == SECONDARY_DATASET_GENERALIZATION_NAME:
        figure = render_secondary_generalization(
            result.comparison_results,
            figures_root / f"{SECONDARY_GENERALIZATION_FIGURE_NAME}.png",
        )
    return figure


def _render_experiment_figures(
    result: ExperimentExecutionResult,
    figures_root: Path,
) -> tuple[Path, ...]:
    figures: list[Path] = [
        render_protocol_schematic(figures_root / "FedSIRA Protocol Schematic.png")
    ]
    if result.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME:
        figures.append(
            render_security_utility_tradeoff(
                result.comparison_results,
                figures_root / f"{PRIMARY_SECURITY_UTILITY_TRADEOFF_FIGURE_NAME}.png",
            )
        )
    elif result.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
        figures.append(
            render_useful_backdoored_source(
                result.comparison_results,
                figures_root / f"{USEFUL_BACKDOORED_SOURCE_FIGURE_NAME}.png",
                result.outcomes,
            )
        )
        figures.append(
            render_collapse_decision_effects(
                result.comparison_results,
                figures_root / f"{COLLAPSE_DECISION_EFFECTS_FIGURE_NAME}.png",
            )
        )
    elif result.experiment in COLLAPSE_EXPERIMENT_NAMES:
        figures.append(
            render_collapse_decision_effects(
                result.comparison_results,
                figures_root / f"{COLLAPSE_DECISION_EFFECTS_FIGURE_NAME}.png",
            )
        )
    elif result.experiment == EFFICIENCY_MEASUREMENT_NAME:
        figures.append(
            render_efficiency_profile(
                (),
                None,
                figures_root / f"{EFFICIENCY_PROFILE_FIGURE_NAME}.png",
                result.comparison_results,
            )
        )
    else:
        specialized = _render_specialized_figure(result, figures_root)
        if specialized is not None:
            figures.append(specialized)
    return tuple(figures)


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

    tables_root = experiment_root / "tables" / "main"
    figures_root = experiment_root / "figures" / "main"
    metrics_root = experiment_root / "metrics" / "primary"
    telemetry_root = experiment_root / "telemetry"
    tables_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)
    metrics_root.mkdir(parents=True, exist_ok=True)
    telemetry_root.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = [
        _write_table(tables_root, render_experiment_cell_metrics_table(result.outcomes)),
        *_render_experiment_figures(result, figures_root),
    ]
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
) -> tuple[ReportVerificationFailure, ...]:
    evidenced_experiments = frozenset(
        comparison.definition.experiment
        for family in comparison_results
        for comparison in family.comparisons
    )
    failures: list[ReportVerificationFailure] = []
    for table_name, expected_experiments in _RESULT_TABLE_EVIDENCE:
        missing = tuple(
            experiment
            for experiment in expected_experiments
            if experiment not in evidenced_experiments
        )
        if missing:
            failures.append(f"{table_name}: missing comparison evidence for {', '.join(missing)}")
    if not comparison_results:
        failures.append("Statistical Summary: no comparison evidence")
    return tuple(failures)


def export_project_summary(
    plan: ExperimentPlan,
    lifecycle_states: tuple[ExperimentLifecycleRecord, ...],
    verification: CompletenessVerificationResult,
    collapse_decisions: tuple[CollapseDecision, ...] | None = None,
    resolved_core: ResolvedCore | None = None,
    comparison_results: tuple[ComparisonFamilyResult, ...] = (),
    outcomes: tuple[CellExecutionOutcome, ...] = (),
    evidence_trajectory: tuple[EvidenceStateFraction, ...] | None = None,
    telemetry: tuple[EfficiencyMetricObservation, ...] | None = None,
) -> ReportExportResult:
    if not verification.passed:
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=verification,
        )

    evidence_failures = _missing_result_evidence(comparison_results)
    if evidence_failures:
        return ReportExportResult(
            experiment=None,
            exported_paths=(),
            verification=CompletenessVerificationResult(
                passed=False,
                failures=evidence_failures,
            ),
        )

    project_root = _results_root() / "project_summary"
    tables_root = project_root / "tables" / "main"
    reproducibility_root = project_root / "reproducibility" / "execution"
    figures_root = project_root / "figures" / "main"
    for directory in (tables_root, reproducibility_root, figures_root):
        directory.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    materialized_tables: list[TableName] = []

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
        _execute_bound(name, overwrite)


def _execute_bound(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
    config = current_application_context().scientific_config
    store = ExecutionRecordStore(
        REPOSITORY_ROOT / Path(config.execution.repository_layout.execution_workspace)
    )
    if name is not None:
        result = _load_experiment_result(name, store)
        experiment_root = (
            REPOSITORY_ROOT
            / Path(config.execution.repository_layout.manuscript_results)
            / "experiments"
            / name
        )
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
        REPOSITORY_ROOT / OUTPUTS_ROOT / "artifacts",
        REPOSITORY_ROOT / OUTPUTS_ROOT / "experiments",
        REPOSITORY_ROOT / RESULTS_ROOT,
    )
    artifact_graph, unresolved_identities = load_published_artifact_graph(artifact_roots)
    stale_ancestor_verification = verify_no_stale_ancestors(
        (*stale_artifact_identities(artifact_graph), *unresolved_identities)
    )
    failures = (
        *count_verification.failures,
        *completion_verification.failures,
        *terminal_verification.failures,
        *stale_ancestor_verification.failures,
    )
    verification = CompletenessVerificationResult(passed=not failures, failures=failures)
    collapse_decisions = _load_collapse_decisions(store)
    comparison_results = _project_comparison_results(plan, store)
    outcomes = _project_outcomes(plan, store)
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


def _project_comparison_results(
    plan: ExperimentPlan,
    store: ExecutionRecordStore,
) -> tuple[ComparisonFamilyResult, ...]:
    return tuple(
        comparison
        for planned in plan.experiments
        for comparison in _load_experiment_result(planned.definition.name, store).comparison_results
    )


def _project_outcomes(
    plan: ExperimentPlan,
    store: ExecutionRecordStore,
) -> tuple[CellExecutionOutcome, ...]:
    return tuple(
        outcome
        for planned in plan.experiments
        for outcome in _load_experiment_result(planned.definition.name, store).outcomes
    )


def project_efficiency_telemetry(
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[EfficiencyMetricObservation, ...]:
    metric_names: tuple[MetricName, ...] = (
        "post-evidence-wall-clock-seconds",
        "communication-bytes",
        "peak-gpu-memory-bytes",
    )
    methods = tuple(sorted(frozenset(outcome.cell.method for outcome in outcomes)))
    observations: list[EfficiencyMetricObservation] = []
    for metric_name in metric_names:
        for method in methods:
            values = tuple(
                value
                for outcome in outcomes
                if outcome.completed and outcome.cell.method == method
                for recorded_metric, value in outcome.metrics
                if recorded_metric == metric_name and value is not None
            )
            if values:
                observations.append(
                    EfficiencyMetricObservation(
                        method=method,
                        metric=metric_name,
                        value=sum(values) / len(values),
                    )
                )
    return tuple(observations)


def _record_metric(record: PersistedExecutionRecord, name: MetricName) -> MetricValue | None:
    for metric_name, value in record.metrics:
        if metric_name == name:
            return value
    return None


def _state_from_encoding(value: MetricValue) -> AdmissionState:
    states = (
        (1.0, AdmissionState.ADMITTED),
        (-1.0, AdmissionState.REJECTED),
        (-2.0, AdmissionState.EXPIRED),
        (0.0, AdmissionState.DORMANT),
    )
    for encoding, state in states:
        if value == encoding:
            return state
    raise ValueError(f"unknown terminal-state encoding: {value}")


def project_evidence_trajectory(
    store: ExecutionRecordStore,
) -> tuple[EvidenceStateFraction, ...]:
    config = current_application_context().scientific_config
    records = tuple(
        record
        for record in store.read_all_outcomes(ADMISSION_DELAY_DECOMPOSITION_NAME)
        if record.terminal_state is ExperimentLifecycleState.COMPLETED
    )
    if not records:
        return ()
    horizon = config.protocol.resource_horizon.maximum_logical_evidence_cycles
    result: list[EvidenceStateFraction] = []
    displayed_states = (
        AdmissionState.DORMANT,
        AdmissionState.ADMITTED,
        AdmissionState.REJECTED,
        AdmissionState.EXPIRED,
    )
    for cycle in range(horizon + 1):
        for state in displayed_states:
            count = sum(1 for record in records if _state_at_evidence_cycle(record, cycle) is state)
            if count:
                result.append(
                    EvidenceStateFraction(cycle=cycle, state=state, fraction=count / len(records))
                )
    return tuple(result)


def _state_at_evidence_cycle(
    record: PersistedExecutionRecord,
    cycle: EvidenceCycleIndex,
) -> AdmissionState:
    terminal_encoding = _record_metric(record, "terminal-state")
    if terminal_encoding is None:
        raise ValueError("completed evidence-arrival record lacks terminal-state metric")
    arrival_cycle = _record_metric(record, "evidence-arrival-cycle")
    if arrival_cycle is None or cycle < arrival_cycle:
        return AdmissionState.DORMANT
    return _state_from_encoding(terminal_encoding)


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
            ),
            terminal_state=record.terminal_state,
            failure=_to_failure_detail(record.failure),
            metrics=record.metrics,
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
                ),
                terminal_state=record.terminal_state,
                failure=None,
                metrics=record.metrics,
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
