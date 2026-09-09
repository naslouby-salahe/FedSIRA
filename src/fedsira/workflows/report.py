from pathlib import Path

from fedsira.artifacts import load_published_artifact_graph, stale_artifact_identities
from fedsira.domain.enums import AdmissionState, ArtifactFamily, ExperimentLifecycleState
from fedsira.domain.types import (
    BooleanValue,
    EvidenceCycleIndex,
    ExperimentName,
    MetricName,
    MetricValue,
    OverwriteExisting,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.experiments.collapse import (
    CollapseDecision,
    collapse_decision_from_comparison_families,
    materialize_resolved_core,
    read_resolved_core,
)
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    COLLAPSE_EXPERIMENT_NAMES,
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
from fedsira.experiments.executor import (
    collapse_evaluation_from_records,
    comparison_results_for_experiment,
)
from fedsira.experiments.planning import (
    ExperimentPlan,
    ScientificCell,
    build_plan,
    validate_planned_cell_count_invariant,
)
from fedsira.io.paths import (
    OUTPUTS_ROOT,
    RESULTS_ROOT,
    preprocessing_root,
    workspace_root_for_family,
)
from fedsira.reporting.export import (
    export_experiment_report,
    export_project_summary,
)
from fedsira.reporting.figures import EfficiencyMetricObservation, EvidenceStateFraction
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
    ApplicationContext,
    FailureDetail,
    bound_application_context,
    current_application_context,
)
from fedsira.workflows import REPOSITORY_ROOT

_COLLAPSE_FAMILIES: tuple[ComparisonFamily, ...] = (
    ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
    ComparisonFamily.PLURALITY_NECESSITY,
    ComparisonFamily.SOURCE_EXCLUSION_CENTRAL_EFFECT,
    ComparisonFamily.EXTERNAL_VERIFICATION_NECESSITY,
)


def execute(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
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
