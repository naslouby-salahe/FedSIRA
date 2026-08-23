from fedsira.experiments.planning import (
    build_plan,
    plan_cell_count_by_program_block,
    validate_planned_cell_count_invariant,
)
from fedsira.experiments.registry import COLLAPSE_EXPERIMENT_NAMES, POST_CORE_EXPERIMENT_NAMES


def test_plan_matches_section_31_counts_exactly() -> None:
    plan = build_plan()
    validate_planned_cell_count_invariant(plan)
    assert plan.total_cell_count == 1989
    assert plan.pre_core_cell_count == 299
    assert plan.post_core_cell_count == 1690


def test_plan_block_counts_match_section_31_table() -> None:
    blocks = plan_cell_count_by_program_block()
    assert blocks["pre_core_subtotal"] == 299
    assert blocks["post_core_subtotal"] == 1690
    assert blocks["complete_scientific_plan"] == 1989


def test_post_core_experiments_block_without_resolved_core() -> None:
    plan = build_plan(resolved_core_complete=False)
    for name in POST_CORE_EXPERIMENT_NAMES:
        assert plan.experiment(name).lifecycle_state.value == "Blocked"
    for name in COLLAPSE_EXPERIMENT_NAMES:
        assert plan.experiment(name).lifecycle_state.value == "Not Started"


def test_post_core_experiments_available_with_resolved_core() -> None:
    plan = build_plan(resolved_core_complete=True)
    for name in POST_CORE_EXPERIMENT_NAMES:
        assert plan.experiment(name).lifecycle_state.value == "Not Started"


def test_plan_has_no_duplicate_semantic_cells() -> None:
    plan = build_plan()
    keys = [cell.semantic_key for planned in plan.experiments for cell in planned.cells]
    assert len(keys) == len(set(keys))


def test_efficiency_measurement_has_five_repetitions_per_method_seed() -> None:
    plan = build_plan(resolved_core_complete=True)
    efficiency = plan.experiment("Efficiency Measurement")
    repetition_conditions = [cell.condition for cell in efficiency.cells]
    assert len(repetition_conditions) == 60
    for method in ("Resolved FedSIRA Core", "One Independent Retrain"):
        method_cells = [cell for cell in efficiency.cells if cell.method == method]
        assert len(method_cells) == 15
        assert len({cell.master_seed for cell in method_cells}) == 3
