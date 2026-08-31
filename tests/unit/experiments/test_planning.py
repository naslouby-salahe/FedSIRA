from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.experiments.definitions import COLLAPSE_EXPERIMENT_NAMES, POST_CORE_EXPERIMENT_NAMES
from fedsira.experiments.planning import build_plan, validate_planned_cell_count_invariant


def test_plan_matches_section_31_counts_exactly() -> None:
    plan = build_plan()
    validate_planned_cell_count_invariant(plan)
    assert plan.total_cell_count == 1989
    assert plan.pre_core_cell_count == 299
    assert plan.post_core_cell_count == 1690


def test_every_experiment_matches_its_section_31_nominal_count() -> None:
    plan = build_plan(resolved_core_complete=True)
    for planned in plan.experiments:
        assert len(planned.cells) == planned.definition.nominal_cell_count


def test_post_core_experiments_block_without_resolved_core() -> None:
    plan = build_plan(resolved_core_complete=False)
    for name in POST_CORE_EXPERIMENT_NAMES:
        assert plan.experiment(name).lifecycle_state is ExperimentLifecycleState.BLOCKED
    for name in COLLAPSE_EXPERIMENT_NAMES:
        assert plan.experiment(name).lifecycle_state is ExperimentLifecycleState.NOT_STARTED


def test_post_core_experiments_available_with_resolved_core() -> None:
    plan = build_plan(resolved_core_complete=True)
    for name in POST_CORE_EXPERIMENT_NAMES:
        assert plan.experiment(name).lifecycle_state is ExperimentLifecycleState.NOT_STARTED


def test_plan_has_no_duplicate_semantic_cells() -> None:
    plan = build_plan()
    keys = tuple(cell.semantic_key for planned in plan.experiments for cell in planned.cells)
    assert len(keys) == len(set(keys))


def test_efficiency_measurement_has_five_repetitions_per_method_seed() -> None:
    plan = build_plan(resolved_core_complete=True)
    efficiency = plan.experiment("Efficiency Measurement")
    assert len(efficiency.cells) == 60
    for method in ("Resolved FedSIRA Core", "One Independent Retrain"):
        method_cells = tuple(cell for cell in efficiency.cells if cell.method == method)
        assert len(method_cells) == 15
        assert len({cell.master_seed for cell in method_cells}) == 3
        repetitions = tuple(cell.condition for cell in method_cells)
        assert set(repetitions) == {
            "repetition-1",
            "repetition-2",
            "repetition-3",
            "repetition-4",
            "repetition-5",
        }
