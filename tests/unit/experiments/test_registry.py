from fedsira.experiments.planning import PLAN_CELL_COUNT_CONTRACT, build_plan
from fedsira.experiments.registry import experiment_by_name, experiment_registry


def test_registry_names_are_unique() -> None:
    names = tuple(definition.name for definition in experiment_registry())
    assert len(names) == len(frozenset(names))


def test_experiment_by_name_resolves_every_registered_experiment() -> None:
    for definition in experiment_registry():
        assert experiment_by_name(definition.name).name == definition.name


def test_planned_cells_match_nominal_registry_counts() -> None:
    plan = build_plan(resolved_core_complete=True)
    assert plan.total_cell_count == PLAN_CELL_COUNT_CONTRACT.complete_scientific_plan
    for planned in plan.experiments:
        assert len(planned.cells) == planned.definition.nominal_cell_count
