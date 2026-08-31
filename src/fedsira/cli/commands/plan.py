from fedsira.artifacts.paths import workspace_root_for_family
from fedsira.cli.commands import REPOSITORY_ROOT
from fedsira.domain.enums import ArtifactFamily
from fedsira.domain.records import PlanRenderText, ResolvedCoreComplete
from fedsira.experiments.collapse import read_resolved_core
from fedsira.experiments.planning import (
    ExperimentPlan,
    build_plan,
    validate_planned_cell_count_invariant,
)
from fedsira.experiments.registry import (
    COLLAPSE_EXPERIMENT_NAMES,
    POST_CORE_EXPERIMENT_NAMES,
)
from fedsira.runtime.state import ApplicationContext, bound_application_context


def resolve_plan(resolved_core_complete: ResolvedCoreComplete = False) -> ExperimentPlan:
    plan = build_plan(resolved_core_complete=resolved_core_complete)
    validate_planned_cell_count_invariant(plan)
    return plan


def render_plan(plan: ExperimentPlan) -> PlanRenderText:
    lines: list[str] = []
    lines.append("FedSIRA experiment plan")
    lines.append("")
    lines.append(f"{'experiment':<55} {'cells':>6}  state")
    for planned in plan.experiments:
        state = planned.lifecycle_state.value
        suffix = ""
        if planned.definition.name in COLLAPSE_EXPERIMENT_NAMES:
            suffix = "  [collapse]"
        elif planned.definition.name in POST_CORE_EXPERIMENT_NAMES:
            suffix = "  [post-core]"
        lines.append(f"{planned.definition.name:<55} {len(planned.cells):>6}  {state}{suffix}")
    lines.append("")
    lines.append(f"pre-core cells: {plan.pre_core_cell_count}")
    lines.append(f"post-core cells: {plan.post_core_cell_count}")
    lines.append(f"total cells: {plan.total_cell_count}")
    return "\n".join(lines)


def execute() -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        resolved_core = read_resolved_core(
            REPOSITORY_ROOT / workspace_root_for_family(ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION)
        )
        plan = resolve_plan(resolved_core_complete=resolved_core is not None)
        print(render_plan(plan))
