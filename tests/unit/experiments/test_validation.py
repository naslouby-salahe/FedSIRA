from fedsira.datasets.nbaiot.validation import (
    validate_condition_vocabulary,
    validate_no_duplicate_semantic_cells,
)
from fedsira.experiments.planning import build_plan, validate_planned_cell_count_invariant


def test_built_plan_satisfies_condition_and_count_invariants() -> None:
    plan = build_plan(resolved_core_complete=False)
    validate_condition_vocabulary(plan)
    validate_no_duplicate_semantic_cells(plan)
    validate_planned_cell_count_invariant(plan)
