from fedsira.experiments.planning import PLAN_CELL_COUNT_CONTRACT, build_plan


def test_plan_cell_counts_match_section_31_contract() -> None:
    plan = build_plan(resolved_core_complete=True)
    assert plan.pre_core_cell_count == PLAN_CELL_COUNT_CONTRACT.pre_core_subtotal
    assert plan.post_core_cell_count == PLAN_CELL_COUNT_CONTRACT.post_core_subtotal
    assert plan.total_cell_count == PLAN_CELL_COUNT_CONTRACT.complete_scientific_plan
