from pathlib import Path

from fedsira.domain.enums import ArtifactFamily, ExperimentLifecycleState
from fedsira.domain.types import BooleanValue, ExperimentName, OverwriteExisting, RunRenderText
from fedsira.experiments.collapse import (
    CollapseDecision,
    collapse_decision_from_comparison_families,
    materialize_resolved_core,
    publish_resolved_core,
    read_resolved_core,
)
from fedsira.experiments.definitions import (
    COLLAPSE_EXPERIMENT_NAMES,
    ComparisonFamily,
    experiment_by_name,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
)
from fedsira.experiments.executor import (
    ProtocolCellExecutor,
    collapse_evaluation_from_records,
    comparison_results_for_experiment,
    derive_experiment_lifecycle,
    execute_experiment,
)
from fedsira.experiments.planning import ScientificCell, build_plan
from fedsira.io.paths import workspace_root_for_family
from fedsira.runtime import (
    ApplicationContext,
    bound_application_context,
    current_application_context,
)
from fedsira.runtime_execution import configure_deterministic_backend
from fedsira.workflows import REPOSITORY_ROOT

RESOLVED_CORE_PUBLISHED_DIRECTORY = workspace_root_for_family(
    ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION
)
_COLLAPSE_FAMILIES: tuple[ComparisonFamily, ...] = (
    ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
    ComparisonFamily.PLURALITY_NECESSITY,
    ComparisonFamily.SOURCE_EXCLUSION_CENTRAL_EFFECT,
    ComparisonFamily.EXTERNAL_VERIFICATION_NECESSITY,
)


def render_result(result: ExperimentExecutionResult) -> RunRenderText:
    lines: list[RunRenderText] = [
        f"FedSIRA run: {result.experiment}",
        f"experiment state: {result.lifecycle_state.value}",
        f"cells: {result.cell_completion_count}/{len(result.outcomes)} completed",
    ]
    for outcome in result.outcomes:
        lines.append(
            f"  {outcome.cell.method:<45} {outcome.cell.condition:<40} "
            f"seed={outcome.cell.master_seed:>5} -> {outcome.terminal_state.value}"
        )
    if result.comparison_results:
        lines.extend(("", "comparisons:"))
        for family in result.comparison_results:
            lines.append(f"  family: {family.family.value}")
            for comparison in family.comparisons:
                p_value = (
                    f"p={comparison.adjusted_p_value:.4f}"
                    if comparison.adjusted_p_value is not None
                    else "p=NA"
                )
                lines.append(
                    f"    {comparison.definition.comparison_name:<110} "
                    f"{comparison.comparison_state.value:<22} {p_value}"
                )
    return "\n".join(lines)


def _collapse_family_for_experiment(experiment: ExperimentName) -> ComparisonFamily | None:
    definition = experiment_by_name(experiment)
    if definition.comparison_family not in _COLLAPSE_FAMILIES:
        return None
    return definition.comparison_family


def _collapse_experiment_completed(
    experiment: ExperimentName, store: ExecutionRecordStore
) -> BooleanValue:
    config = current_application_context().scientific_config
    definition = experiment_by_name(experiment)
    planned = build_plan(
        resolved_core_complete=False,
        master_seeds=config.seeds_and_determinism.master_seeds,
        smoke_seed=config.seeds_and_determinism.smoke_seed,
    ).experiment(experiment)
    lifecycle = derive_experiment_lifecycle(planned, store.read_planned_outcomes(planned))
    return (
        lifecycle is ExperimentLifecycleState.COMPLETED
        and len(store.read_all_outcomes(experiment)) == definition.nominal_cell_count
    )


def _materialize_core_if_complete(experiment: ExperimentName) -> None:
    if experiment not in COLLAPSE_EXPERIMENT_NAMES:
        return
    config = current_application_context().scientific_config
    store = ExecutionRecordStore(
        REPOSITORY_ROOT / Path(config.execution.repository_layout.execution_workspace)
    )
    for collapse_experiment in COLLAPSE_EXPERIMENT_NAMES:
        if not _collapse_experiment_completed(collapse_experiment, store):
            return
    decisions: list[CollapseDecision] = []
    for collapse_experiment in COLLAPSE_EXPERIMENT_NAMES:
        records = store.read_all_outcomes(collapse_experiment)
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
        definition = experiment_by_name(collapse_experiment)
        comparison_results = comparison_results_for_experiment(
            collapse_experiment, definition.dataset, outcomes, store
        )
        family = _collapse_family_for_experiment(collapse_experiment)
        if family is None:
            return
        evaluation = collapse_evaluation_from_records(collapse_experiment, records)
        if evaluation is None:
            return
        decisions.append(
            collapse_decision_from_comparison_families(
                family,
                comparison_results,
                evaluation=evaluation,
                materiality_config=config.metrics_and_statistics.materiality,
            )
        )
    if len(decisions) != len(COLLAPSE_EXPERIMENT_NAMES):
        return
    core = materialize_resolved_core(tuple(decisions))
    publish_resolved_core(REPOSITORY_ROOT / RESOLVED_CORE_PUBLISHED_DIRECTORY, core)
    print(f"Resolved FedSIRA Core materialized: {core.decision_identity}")


def execute(name: ExperimentName, overwrite: OverwriteExisting) -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        configure_deterministic_backend()
        _execute_bound(name, overwrite)


def _execute_bound(name: ExperimentName, overwrite: OverwriteExisting) -> None:
    resolved_core = read_resolved_core(REPOSITORY_ROOT / RESOLVED_CORE_PUBLISHED_DIRECTORY)
    result = execute_experiment(
        name,
        ProtocolCellExecutor(resolved_core=resolved_core),
        overwrite=overwrite,
        resolved_core_complete=resolved_core is not None,
    )
    print(render_result(result))
    if (
        result.lifecycle_state is ExperimentLifecycleState.COMPLETED
        and (not overwrite)
        and result.execution_digest
    ):
        print(f"already-completed: execution digest {result.execution_digest}")
    if result.lifecycle_state is ExperimentLifecycleState.COMPLETED:
        _materialize_core_if_complete(name)
    if result.lifecycle_state in (
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
        ExperimentLifecycleState.BLOCKED,
    ):
        raise SystemExit(1)
