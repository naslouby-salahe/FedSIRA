import ast

import pytest
from _repo import SRC_ROOT, iter_python_files, parse
from pydantic import ValidationError

from fedsira.domain.enums import DatasetId
from fedsira.experiments.definitions import (
    ExperimentDefinition,
    experiment_registry,
)
from fedsira.experiments.planning import (
    build_plan,
    efficiency_repetition_indices,
    plan_cell_count_contract,
    validate_planned_cell_count_invariant,
)
from fedsira.reporting.figures import MANDATORY_FIGURE_NAMES
from fedsira.reporting.tables import MANUSCRIPT_TABLE_NAMES

REPORTING_MODULES = (
    SRC_ROOT / "reporting" / "tables.py",
    SRC_ROOT / "reporting" / "protocol_tables.py",
)


def _rendered_table_names() -> frozenset[str]:
    produced: set[str] = set()
    for path in REPORTING_MODULES:
        for node in ast.walk(parse(path)):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Name) and node.func.id == "RenderedTable"):
                continue
            for keyword in node.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    produced.add(str(keyword.value.value))
    return frozenset(produced)


def test_every_experiment_declares_a_known_dataset() -> None:
    known = frozenset(DatasetId)
    offenders = [
        definition.name for definition in experiment_registry() if definition.dataset not in known
    ]
    assert not offenders, f"experiments without an explicit DatasetId: {offenders}"


def test_experiment_definitions_cannot_default_their_dataset() -> None:
    definition = experiment_registry()[0]
    payload = definition.model_dump()
    payload.pop("dataset")
    with pytest.raises(ValidationError):
        ExperimentDefinition.model_validate(payload)


def test_every_experiment_declares_its_scientific_matrix() -> None:
    offenders: list[str] = []
    for definition in experiment_registry():
        if not definition.methods or not definition.conditions:
            offenders.append(f"{definition.name}: empty method or condition matrix")
        if not definition.primary_metrics:
            offenders.append(f"{definition.name}: no primary metrics declared")
        if definition.nominal_cell_count <= 0:
            offenders.append(f"{definition.name}: non-positive nominal cell count")
    assert not offenders, f"incomplete experiment definitions: {offenders}"


def test_every_experiment_name_is_unique() -> None:
    names = tuple(definition.name for definition in experiment_registry())
    assert len(set(names)) == len(names)


def test_every_experiment_declares_an_artifact_specification() -> None:
    offenders: list[str] = []
    for definition in experiment_registry():
        specification = definition.artifacts
        if not specification.required_metric_artifacts:
            offenders.append(f"{definition.name}: no metric artifacts declared")
        if not specification.metrics_required:
            offenders.append(f"{definition.name}: mandatory metrics not required")
    assert not offenders, f"experiments without artifact contracts: {offenders}"


def test_planned_cells_cover_every_declared_method_and_condition() -> None:
    offenders: list[str] = []
    for planned in build_plan().experiments:
        definition: ExperimentDefinition = planned.definition
        methods = frozenset(cell.method for cell in planned.cells)
        conditions = frozenset(cell.condition for cell in planned.cells)
        if not methods.issubset(frozenset(definition.methods)):
            offenders.append(f"{definition.name}: planned methods outside the declared matrix")
        if not conditions.issubset(frozenset(definition.conditions)):
            offenders.append(f"{definition.name}: planned conditions outside the declared matrix")
        if len(planned.cells) != definition.nominal_cell_count:
            offenders.append(f"{definition.name}: planned cell count differs from its contract")
    assert not offenders, f"planned-cell drift: {offenders}"


def test_planned_cell_counts_match_the_section_31_contract() -> None:
    plan = build_plan()
    validate_planned_cell_count_invariant(plan)
    contract = plan_cell_count_contract()
    assert plan.pre_core_cell_count == contract.pre_core_subtotal == 299
    assert plan.post_core_cell_count == contract.post_core_subtotal == 1690
    assert plan.total_cell_count == contract.complete_scientific_plan == 1989


def test_efficiency_repetitions_follow_the_configured_count() -> None:
    indices = efficiency_repetition_indices()
    assert indices == tuple(range(1, len(indices) + 1))
    assert len(indices) > 1


def test_every_mandatory_table_has_a_producer() -> None:
    produced = _rendered_table_names()
    missing = tuple(name for name in MANUSCRIPT_TABLE_NAMES if name not in produced)
    assert not missing, f"mandatory tables without a renderer: {missing}"


def test_every_mandatory_figure_is_declared_once() -> None:
    assert len(set(MANDATORY_FIGURE_NAMES)) == len(MANDATORY_FIGURE_NAMES)
    assert len(MANDATORY_FIGURE_NAMES) == 13


def test_production_has_no_repository_state_or_source_fingerprint_machinery() -> None:
    forbidden_attributes = {"dump", "walk", "parse"}
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        tree = parse(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name.split(".", maxsplit=1)[0] == "ast" for alias in node.names
            ):
                offenders.append(f"{path.name}: ast import")
            if isinstance(node, ast.ImportFrom) and node.module == "ast":
                offenders.append(f"{path.name}: ast import")
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.strip().lower() in {"git", "git.exe", "dirty"}
            ):
                offenders.append(f"{path.name}: git repository state")
            if (
                isinstance(node, ast.Attribute)
                and node.attr in forbidden_attributes
                and isinstance(node.value, ast.Name)
                and node.value.id == "ast"
            ):
                offenders.append(f"{path.name}: ast.{node.attr}")
            if isinstance(node, ast.Name) and "fingerprint" in node.id.lower():
                offenders.append(f"{path.name}: {node.id}")
    assert not offenders, f"repository-state/source-fingerprint machinery: {sorted(set(offenders))}"
