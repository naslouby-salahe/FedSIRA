from __future__ import annotations

from pathlib import Path

from fedsira.artifacts.paths import (
    experiment_log_path,
    workspace_root_for_family,
)
from fedsira.datasets.nbaiot.validation import ExperimentPrerequisiteState
from fedsira.domain.enums import (
    ArtifactFamily,
    ExperimentLifecycleState,
)
from fedsira.domain.types import (
    ExperimentName,
    OverwriteExisting,
    ResolvedCoreComplete,
    StatusRenderText,
)
from fedsira.experiments.definitions import experiment_by_name
from fedsira.experiments.engine import (
    EXECUTION_LOGGER,
    CellExecutionOutcome,
    CellExecutor,
    ComparisonResultBuilder,
    ExecutionLogFields,
    ExecutionRecordStore,
    ExperimentExecutionResult,
    derive_experiment_lifecycle,
    execute_cell_with_retry,
    execution_digest,
    log_execution_event,
    prerequisite_states_from_store,
)
from fedsira.experiments.planning import build_plan
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ApplicationContext,
    ElapsedTimer,
    bound_application_context,
    configure_deterministic_backend,
    configure_structured_file_logging,
    current_application_context,
)


def execute_experiment(
    experiment: ExperimentName,
    executor: CellExecutor,
    comparison_builder: ComparisonResultBuilder | None = None,
    *,
    overwrite: OverwriteExisting = False,
    resolved_core_complete: ResolvedCoreComplete = False,
    prerequisite_states: tuple[ExperimentPrerequisiteState, ...] | None = None,
) -> ExperimentExecutionResult:
    from fedsira.datasets.nbaiot.validation import (
        validate_condition_vocabulary,
        validate_experiment_prerequisites_met,
        validate_no_duplicate_semantic_cells,
    )

    resolved_config = current_application_context().scientific_config
    configure_structured_file_logging(
        EXECUTION_LOGGER,
        current_application_context().repository_root / experiment_log_path(experiment),
    )
    timer = ElapsedTimer()
    log_execution_event(
        "experiment.started",
        ExecutionLogFields(experiment=experiment, overwrite=overwrite),
    )
    definition = experiment_by_name(experiment)
    log_execution_event(
        "experiment.configuration.resolved", ExecutionLogFields(experiment=experiment)
    )
    plan = build_plan(
        resolved_core_complete=resolved_core_complete,
        master_seeds=resolved_config.seeds_and_determinism.master_seeds,
        smoke_seed=resolved_config.seeds_and_determinism.smoke_seed,
    )
    validate_condition_vocabulary(plan)
    validate_no_duplicate_semantic_cells(plan)
    planned = plan.experiment(experiment)
    log_execution_event(
        "experiment.plan.created",
        ExecutionLogFields(
            experiment=experiment,
            dataset=definition.dataset,
            total_cells=len(planned.cells),
        ),
    )
    if planned.lifecycle_state is ExperimentLifecycleState.BLOCKED:
        return ExperimentExecutionResult(
            experiment=experiment, lifecycle_state=ExperimentLifecycleState.BLOCKED, outcomes=()
        )
    store = ExecutionRecordStore(
        Path(resolved_config.execution.repository_layout.execution_workspace)
    )
    states = prerequisite_states or prerequisite_states_from_store(plan, experiment, store)
    validate_experiment_prerequisites_met(experiment, states)
    log_execution_event(
        "experiment.prerequisites.validated", ExecutionLogFields(experiment=experiment)
    )
    outcomes: list[CellExecutionOutcome] = []
    for cell in planned.cells:
        fields = ExecutionLogFields(
            experiment=experiment,
            dataset=definition.dataset,
            cell=cell.semantic_key,
            method=cell.method,
            condition=cell.condition,
            master_seed=cell.master_seed,
            total_cells=len(planned.cells),
        )
        existing = store.read_outcome(experiment, cell.semantic_key)
        if (
            existing is not None
            and not overwrite
            and existing.terminal_state is ExperimentLifecycleState.COMPLETED
        ):
            log_execution_event(
                "cell.reused",
                fields,
            )
            outcomes.append(
                CellExecutionOutcome(
                    cell=cell,
                    terminal_state=existing.terminal_state,
                    failure=None,
                    metrics=existing.metrics,
                    state_trajectory=existing.state_trajectory,
                )
            )
            continue
        log_execution_event("cell.started", fields)
        outcome = execute_cell_with_retry(cell, executor)
        store.write_outcome(outcome)
        completed_cells = len(outcomes) + 1
        completed_fields = fields.with_cell_terminal_state(outcome.terminal_state, completed_cells)
        log_execution_event("cell.record.persisted", completed_fields)
        for metric_name, _metric_value in outcome.metrics:
            log_execution_event(
                "cell.metric.computed",
                completed_fields.with_metric(metric_name),
            )
        log_execution_event("cell.completed", completed_fields)
        log_execution_event("experiment.progress", completed_fields)
        outcomes.append(outcome)
    outcome_tuple = tuple(outcomes)
    lifecycle_state = derive_experiment_lifecycle(planned, store.read_planned_outcomes(planned))
    if comparison_builder is None:
        comparisons = ()
    else:
        log_execution_event("comparison.started", ExecutionLogFields(experiment=experiment))
        comparisons = comparison_builder(experiment, definition.dataset, outcome_tuple, store)
        log_execution_event("comparison.completed", ExecutionLogFields(experiment=experiment))
    result = ExperimentExecutionResult(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        outcomes=outcome_tuple,
        comparison_results=comparisons,
        execution_digest=execution_digest(experiment, lifecycle_state, outcome_tuple),
    )
    log_execution_event(
        "experiment.completed"
        if lifecycle_state is ExperimentLifecycleState.COMPLETED
        else "experiment.failed",
        ExecutionLogFields(
            experiment=experiment,
            terminal_state=lifecycle_state,
            completed_cells=result.cell_completion_count,
            total_cells=len(planned.cells),
            elapsed_seconds=timer.elapsed_seconds(),
        ),
    )
    return result


def render_status() -> StatusRenderText:
    from fedsira.experiments.collapse import read_resolved_core

    config = current_application_context().scientific_config
    resolved_core = read_resolved_core(
        REPOSITORY_ROOT / workspace_root_for_family(ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION)
    )
    plan = build_plan(resolved_core_complete=resolved_core is not None)
    store = ExecutionRecordStore(
        REPOSITORY_ROOT / Path(config.execution.repository_layout.execution_workspace)
    )
    lines: list[str] = ["FedSIRA experiment status", ""]
    for planned in plan.experiments:
        records = store.read_planned_outcomes(planned)
        state = derive_experiment_lifecycle(planned, records)
        completed = sum(
            record.terminal_state is ExperimentLifecycleState.COMPLETED for record in records
        )
        lines.append(
            f"{planned.definition.name:<55} {completed:>4}/{len(planned.cells):<4} {state.value}"
        )
    return "\n".join(lines)


def execute_status() -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        print(render_status())


def execute_smoke(overwrite: OverwriteExisting) -> None:
    from fedsira.datasets.nbaiot.validation import render_smoke, run_smoke_suite

    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        configure_deterministic_backend()
        result = run_smoke_suite(overwrite=overwrite)
    print(render_smoke(result))
    if not result.passed:
        raise SystemExit(1)
