from pathlib import Path

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedFailureDetail,
    comparison_results_for_experiment,
)
from fedsira.experiments.planning import (
    ScientificCell,
    build_plan,
    validate_planned_cell_count_invariant,
)
from fedsira.experiments.registry import EXPERIMENT_REGISTRY
from fedsira.reporting.export import (
    derive_claim_states_for_export,
    export_experiment_report,
    export_project_summary,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult as _CompletenessResult,
)
from fedsira.reporting.verification import (
    verify_claim_states_derivable,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_planned_cell_count_satisfied,
)
from fedsira.runtime.state import FailureDetail


def execute(name: str | None, overwrite: bool) -> None:
    store = ExecutionRecordStore(Path("outputs"))
    if name is not None:
        result = _load_experiment_result(name, store)
        experiment_root = Path("results") / "experiments" / name
        export = export_experiment_report(result, PRODUCTION_CONFIG_PATH, experiment_root)
        for path in export.exported_paths:
            print(f"exported {path}")
        return

    plan = build_plan(resolved_core_complete=True)
    validate_planned_cell_count_invariant(plan)
    terminal_counts: dict[str, int] = {}
    lifecycle_states: dict[str, ExperimentLifecycleState] = {}
    for definition in EXPERIMENT_REGISTRY:
        outcomes = store.read_all_outcomes(definition.name)
        terminal_counts[definition.name] = len(outcomes)
        if not outcomes:
            lifecycle_states[definition.name] = ExperimentLifecycleState.NOT_STARTED
            continue
        states = {outcome.terminal_state for outcome in outcomes}
        if "Invalid" in states:
            lifecycle_states[definition.name] = ExperimentLifecycleState.INVALID
        elif "Failed" in states:
            lifecycle_states[definition.name] = ExperimentLifecycleState.FAILED
        elif states == {"Completed"}:
            lifecycle_states[definition.name] = ExperimentLifecycleState.COMPLETED
        else:
            lifecycle_states[definition.name] = ExperimentLifecycleState.RUNNING

    count_verification = verify_planned_cell_count_satisfied(plan, terminal_counts)
    completion_verification = verify_experiments_completed(
        lifecycle_states, tuple(d.name for d in EXPERIMENT_REGISTRY)
    )
    terminal_verification = verify_experiments_reached_terminal_state(
        lifecycle_states, tuple(d.name for d in EXPERIMENT_REGISTRY)
    )
    claim_states = derive_claim_states_for_export()
    claim_verification = verify_claim_states_derivable(len(claim_states), len(claim_states))

    combined_failures = (
        *count_verification.failures,
        *completion_verification.failures,
        *terminal_verification.failures,
        *claim_verification.failures,
    )
    verification = _CompletenessResult(passed=not combined_failures, failures=combined_failures)

    export = export_project_summary(
        plan,
        claim_states,
        lifecycle_states,
        PRODUCTION_CONFIG_PATH,
        verification,
    )
    for path in export.exported_paths:
        print(f"exported {path}")
    if not verification.passed:
        print("project summary verification: BLOCKED")
        for failure in verification.failures:
            print(f"  {failure}")
        raise SystemExit(1)


def _load_experiment_result(name: str, store: ExecutionRecordStore) -> ExperimentExecutionResult:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    outcomes_records = store.read_all_outcomes(name)
    outcomes: list[CellExecutionOutcome] = []
    for record in outcomes_records:
        cell = ScientificCell(
            experiment=record.experiment,
            method=record.method,
            condition=record.condition,
            master_seed=record.master_seed,
        )
        outcomes.append(
            CellExecutionOutcome(
                cell=cell,
                terminal_state=record.terminal_state,
                failure=_to_failure_detail(record.failure),
                metrics=record.metrics,
            )
        )
    comparison_results = comparison_results_for_experiment(name, outcomes, config)
    states = {outcome.terminal_state for outcome in outcomes}
    if not outcomes:
        lifecycle = ExperimentLifecycleState.NOT_STARTED
    elif "Invalid" in states:
        lifecycle = ExperimentLifecycleState.INVALID
    elif "Failed" in states:
        lifecycle = ExperimentLifecycleState.FAILED
    elif states == {"Completed"}:
        lifecycle = ExperimentLifecycleState.COMPLETED
    else:
        lifecycle = ExperimentLifecycleState.RUNNING
    return ExperimentExecutionResult(
        experiment=name,
        lifecycle_state=lifecycle,
        outcomes=tuple(outcomes),
        comparison_results=comparison_results,
    )


def _to_failure_detail(failure: PersistedFailureDetail | None) -> FailureDetail | None:
    if failure is None:
        return None
    return FailureDetail(
        failure_class=failure.failure_class,
        message=failure.message,
        cell_phase=failure.cell_phase,
    )
