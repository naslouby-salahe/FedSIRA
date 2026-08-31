from pathlib import Path

from fedsira.cli.commands import REPOSITORY_ROOT
from fedsira.config.loading import PRODUCTION_CONFIG_PATH
from fedsira.domain.records import ExperimentName, OverwriteExisting
from fedsira.experiments.collapse import (
    CollapseDecision,
    collapse_decision_from_comparison_families,
    materialize_resolved_core,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    PersistedFailureDetail,
    collapse_evaluation_from_records,
    comparison_results_for_experiment,
    derive_experiment_lifecycle,
)
from fedsira.experiments.planning import (
    ScientificCell,
    build_plan,
    validate_planned_cell_count_invariant,
)
from fedsira.experiments.registry import COLLAPSE_EXPERIMENT_NAMES, ClaimFamily, experiment_by_name
from fedsira.reporting.export import (
    claim_definition_count,
    derive_claim_states_for_export,
    export_experiment_report,
    export_project_summary,
)
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
    ExperimentTerminalCount,
    terminal_count_for_planned_experiment,
    verify_claim_states_derivable,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_no_stale_ancestors,
    verify_planned_cell_count_satisfied,
)
from fedsira.runtime.state import (
    ApplicationContext,
    FailureDetail,
    bound_application_context,
    current_application_context,
)

_COLLAPSE_FAMILIES: tuple[ClaimFamily, ...] = (
    ClaimFamily.PROPOSAL_SCREEN_NECESSITY,
    ClaimFamily.PLURALITY_NECESSITY,
    ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM,
    ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY,
)


def execute(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        _execute_bound(name, overwrite)


def _execute_bound(name: ExperimentName | None, overwrite: OverwriteExisting) -> None:
    config = current_application_context().scientific_config
    store = ExecutionRecordStore(
        REPOSITORY_ROOT / Path(config.runtime.repository_layout.execution_workspace)
    )
    if name is not None:
        result = _load_experiment_result(name, store)
        experiment_root = (
            REPOSITORY_ROOT
            / Path(config.runtime.repository_layout.manuscript_results)
            / "experiments"
            / name
        )
        if overwrite and experiment_root.exists():
            for child in experiment_root.rglob("*"):
                if child.is_file():
                    child.unlink()
        export = export_experiment_report(result, PRODUCTION_CONFIG_PATH, experiment_root)
        for path in export.exported_paths:
            print(f"exported {path}")
        if not export.verification.passed:
            raise SystemExit(1)
        return
    plan = build_plan(resolved_core_complete=True)
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
    claim_states = derive_claim_states_for_export()
    claim_verification = verify_claim_states_derivable(claim_states, claim_definition_count())
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
        lifecycle_records,
        PRODUCTION_CONFIG_PATH,
        verification,
        collapse_decisions=collapse_decisions,
        resolved_core=materialize_resolved_core(collapse_decisions)
        if collapse_decisions is not None
        else None,
    )
    for path in export.exported_paths:
        print(f"exported {path}")
    if not export.verification.passed:
        print("project summary verification: BLOCKED")
        for failure in export.verification.failures:
            print(f"  {failure}")
        raise SystemExit(1)


def _load_experiment_result(
    name: ExperimentName, store: ExecutionRecordStore
) -> ExperimentExecutionResult:
    definition = experiment_by_name(name)
    plan = build_plan(resolved_core_complete=True)
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
