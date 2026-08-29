from pathlib import Path

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.records import ExperimentName, OverwriteExisting, ScientificCellCount
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
from fedsira.experiments.planning import ScientificCell, build_plan, validate_planned_cell_count_invariant
from fedsira.experiments.registry import (
    COLLAPSE_EXPERIMENT_NAMES,
    EXPERIMENT_REGISTRY,
    ClaimFamily,
    experiment_by_name,
)
from fedsira.reporting.export import (
    claim_definition_count,
    derive_claim_states_for_export,
    export_experiment_report,
    export_project_summary,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    verify_claim_states_derivable,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_no_stale_ancestors,
    verify_planned_cell_count_satisfied,
)
from fedsira.runtime.state import FailureDetail


def execute(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
    del overwrite
    store = ExecutionRecordStore(Path("outputs"))
    if name is not None:
        result = _load_experiment_result(name, store)
        experiment_root = Path("results") / "experiments" / name
        export = export_experiment_report(result, PRODUCTION_CONFIG_PATH, experiment_root)
        for path in export.exported_paths:
            print(f"exported {path}")
        if not export.verification.passed:
            raise SystemExit(1)
        return

    plan = build_plan(resolved_core_complete=True)
    validate_planned_cell_count_invariant(plan)
    terminal_counts: dict[ExperimentName, ScientificCellCount] = {}
    lifecycle_states: dict[ExperimentName, ExperimentLifecycleState] = {}
    experiment_names = tuple(definition.name for definition in EXPERIMENT_REGISTRY)
    for definition in EXPERIMENT_REGISTRY:
        outcomes = store.read_all_outcomes(definition.name)
        terminal_counts[definition.name] = len(outcomes)
        lifecycle_states[definition.name] = (
            derive_lifecycle_state(tuple(outcome.terminal_state for outcome in outcomes))
            if outcomes
            else ExperimentLifecycleState.NOT_STARTED
        )

    count_verification = verify_planned_cell_count_satisfied(plan, terminal_counts)
    completion_verification = verify_experiments_completed(lifecycle_states, experiment_names)
    terminal_verification = verify_experiments_reached_terminal_state(
        lifecycle_states,
        experiment_names,
    )
    claim_states = derive_claim_states_for_export()
    claim_verification = verify_claim_states_derivable(
        len(claim_states),
        claim_definition_count(),
    )
    stale_ancestor_verification = verify_no_stale_ancestors(())
    failures = (
        *count_verification.failures,
        *completion_verification.failures,
        *terminal_verification.failures,
        *claim_verification.failures,
        *stale_ancestor_verification.failures,
    )
    verification = CompletenessVerificationResult(passed=not failures, failures=failures)
    collapse_decisions = _load_collapse_decisions(store)
    export = export_project_summary(
        plan,
        claim_states,
        lifecycle_states,
        PRODUCTION_CONFIG_PATH,
        verification,
        collapse_decisions=collapse_decisions,
        resolved_core=(
            materialize_resolved_core(collapse_decisions)
            if collapse_decisions is not None
            else None
        ),
    )
    for path in export.exported_paths:
        print(f"exported {path}")
    if not verification.passed:
        print("project summary verification: BLOCKED")
        for failure in verification.failures:
            print(f"  {failure}")
        raise SystemExit(1)


def _load_experiment_result(
    name: ExperimentName,
    store: ExecutionRecordStore,
) -> ExperimentExecutionResult:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    definition = experiment_by_name(name)
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
    comparisons = comparison_results_for_experiment(
        name,
        definition.dataset,
        outcomes,
        config,
    )
    lifecycle = derive_lifecycle_state(tuple(outcome.terminal_state for outcome in outcomes))
    return ExperimentExecutionResult(
        experiment=name,
        lifecycle_state=lifecycle,
        outcomes=outcomes,
        comparison_results=comparisons,
    )


def _to_failure_detail(failure: PersistedFailureDetail | None) -> FailureDetail | None:
    if failure is None:
        return None
    return FailureDetail(
        failure_class=failure.failure_class,
        message=failure.message,
        cell_phase=failure.cell_phase,
    )


def _load_collapse_decisions(
    store: ExecutionRecordStore,
) -> tuple[CollapseDecision, ...] | None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    collapse_families = frozenset(
        {
            ClaimFamily.PROPOSAL_SCREEN_NECESSITY,
            ClaimFamily.PLURALITY_NECESSITY,
            ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM,
            ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY,
        }
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
        matched_family = next(
            (
                result.family
                for result in comparison_results
                if result.family in collapse_families
            ),
            None,
        )
        if matched_family is None:
            return None
        decisions.append(
            collapse_decision_from_comparison_families(
                matched_family,
                comparison_results,
                evaluation=None,
                materiality_config=config.metrics_and_statistics.materiality,
            )
        )
    if len(decisions) != len(COLLAPSE_EXPERIMENT_NAMES):
        return None
    if not all(decision.constraint_passes for decision in decisions):
        return None
    return tuple(decisions)
