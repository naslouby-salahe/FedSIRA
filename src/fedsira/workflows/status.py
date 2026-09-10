from pathlib import Path

from fedsira.artifacts.paths import workspace_root_for_family
from fedsira.domain.enums import ArtifactFamily, ExperimentLifecycleState
from fedsira.domain.types import StatusRenderText
from fedsira.experiments.collapse import read_resolved_core
from fedsira.experiments.execution import ExecutionRecordStore, derive_experiment_lifecycle
from fedsira.experiments.planning import build_plan
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ApplicationContext,
    bound_application_context,
    current_application_context,
)


def render_status() -> StatusRenderText:
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


def execute() -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        print(render_status())
