from pathlib import Path

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.experiments.collapse import (
    CollapseDecision,
    ResolvedCore,
    collapse_decision_from_comparison_families,
    materialize_resolved_core,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedFailureDetail,
    comparison_results_for_experiment,
    derive_lifecycle_state,
)
from fedsira.experiments.planning import (
    ScientificCell,
    build_plan,
    validate_planned_cell_count_invariant,
)
from fedsira.experiments.registry import (
    COLLAPSE_EXPERIMENT_NAMES,
    EXPERIMENT_REGISTRY,
    ClaimFamily,
    experiment_by_name,
)
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
    verify_no_stale_ancestors,
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
        lifecycle_states[definition.name] = derive_lifecycle_state(
            tuple(outcome.terminal_state for outcome in outcomes)
        )

    count_verification = verify_planned_cell_count_satisfied(plan, terminal_counts)
    completion_verification = verify_experiments_completed(
        lifecycle_states, tuple(d.name for d in EXPERIMENT_REGISTRY)
    )
    terminal_verification = verify_experiments_reached_terminal_state(
        lifecycle_states, tuple(d.name for d in EXPERIMENT_REGISTRY)
    )
    claim_states = derive_claim_states_for_export()
    claim_verification = verify_claim_states_derivable(len(claim_states), len(claim_states))
    stale_ancestor_verification = verify_no_stale_ancestors(())

    combined_failures = (
        *count_verification.failures,
        *completion_verification.failures,
        *terminal_verification.failures,
        *claim_verification.failures,
        *stale_ancestor_verification.failures,
    )
    verification = _CompletenessResult(passed=not combined_failures, failures=combined_failures)

    export = export_project_summary(
        plan,
        claim_states,
        lifecycle_states,
        PRODUCTION_CONFIG_PATH,
        verification,
        collapse_decisions=_load_collapse_decisions(store),
        resolved_core=_load_resolved_core(store),
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
    definition = experiment_by_name(name)
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
    comparison_results = comparison_results_for_experiment(
        name,
        definition.dataset,
        outcomes,
        config,
    )
    if not outcomes:
        lifecycle = ExperimentLifecycleState.NOT_STARTED
    else:
        lifecycle = derive_lifecycle_state(tuple(outcome.terminal_state for outcome in outcomes))
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


def _load_collapse_decisions(store: ExecutionRecordStore) -> tuple[CollapseDecision, ...] | None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    alpha = config.metrics_and_statistics.multiplicity.family_wise_alpha
    collapse_family_names = (
        ClaimFamily.PROPOSAL_SCREEN_NECESSITY.value,
        ClaimFamily.PLURALITY_NECESSITY.value,
        ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM.value,
        ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY.value,
    )
    decisions: list[CollapseDecision] = []
    for experiment in COLLAPSE_EXPERIMENT_NAMES:
        records = store.read_all_outcomes(experiment)
        if not records:
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
            experiment,
            definition.dataset,
            outcomes,
            config,
        )
        family_names = {family.family.value for family in comparison_results}
        matched_family = next(
            (family for family in family_names if family in collapse_family_names),
            None,
        )
        if matched_family is None:
            return None
        decisions.append(
            collapse_decision_from_comparison_families(matched_family, comparison_results, alpha)
        )
    if len(decisions) != len(COLLAPSE_EXPERIMENT_NAMES):
        return None
    return tuple(decisions)


def _load_resolved_core(store: ExecutionRecordStore) -> ResolvedCore | None:
    decisions = _load_collapse_decisions(store)
    if decisions is None:
        return None
    return materialize_resolved_core(decisions)
