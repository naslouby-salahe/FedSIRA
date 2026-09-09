import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

FORBIDDEN_GENERIC_ALIASES = {
    "FiniteFloat",
    "NonNegativeFloat",
    "NonNegativeInt",
    "OpenUnitInterval",
    "PositiveFloat",
    "PositiveInt",
    "SignedInt",
    "UnitInterval",
}
CANONICAL_TYPES_PATH = SRC_ROOT / "domain" / "types.py"
PRIMITIVE_BASES = {"bool", "bytes", "float", "int", "str"}
CONVERSION_CALLS = {"bool", "float", "int", "str"}


def _alias_bases() -> dict[str, str]:
    tree = parse(CANONICAL_TYPES_PATH)
    resolved: dict[str, str] = {}
    pending: dict[str, ast.expr] = {}
    for statement in tree.body:
        if not (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            continue
        name = statement.targets[0].id
        value = statement.value
        if (
            isinstance(value, ast.Subscript)
            and isinstance(value.value, ast.Name)
            and value.value.id == "Annotated"
            and isinstance(value.slice, ast.Tuple)
            and value.slice.elts
            and isinstance(value.slice.elts[0], ast.Name)
            and value.slice.elts[0].id in PRIMITIVE_BASES
        ):
            resolved[name] = value.slice.elts[0].id
            continue
        pending[name] = value
    changed = True
    while changed:
        changed = False
        for name, value in list(pending.items()):
            if name in resolved:
                continue
            if isinstance(value, ast.Name) and value.id in resolved:
                resolved[name] = resolved[value.id]
                changed = True
    return resolved


def forbidden_alias_symbol_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_GENERIC_ALIASES:
            found.append(f"name:{node.id}:{node.lineno}")
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_GENERIC_ALIASES:
            found.append(f"attribute:{node.attr}:{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            for imported in node.names:
                if imported.name in FORBIDDEN_GENERIC_ALIASES:
                    found.append(f"import:{imported.name}:{node.lineno}")
        elif isinstance(node, ast.Import):
            for imported in node.names:
                terminal = imported.name.rsplit(".", maxsplit=1)[-1]
                if terminal in FORBIDDEN_GENERIC_ALIASES:
                    found.append(f"import:{terminal}:{node.lineno}")
    return found


def _enum_member_unwrap(node: ast.expr) -> bool:
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Attribute)
            and child.attr == "value"
            and isinstance(child.value, ast.Attribute)
            and child.value.attr.isupper()
        ):
            return True
    return False


def enum_value_in_comparison_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        if any(_enum_member_unwrap(operand) for operand in operands):
            found.append(f"{node.lineno}")
    return found


def redundant_same_base_cast_violations(tree: ast.Module) -> list[str]:
    bases = _alias_bases()
    found: list[str] = []
    for function in (
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ):
        declared: dict[str, str] = {}
        for argument in function.args.posonlyargs + function.args.args + function.args.kwonlyargs:
            if argument.arg in {"self", "cls"} or argument.annotation is None:
                continue
            if isinstance(argument.annotation, ast.Name):
                declared[argument.arg] = argument.annotation.id
        for node in ast.walk(function):
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and isinstance(node.annotation, ast.Name)
            ):
                declared[node.target.id] = node.annotation.id
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in CONVERSION_CALLS
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in declared
            ):
                argument_name = node.args[0].id
                source_name = declared[argument_name]
                if source_name in PRIMITIVE_BASES:
                    source_base = source_name
                elif source_name in bases:
                    source_base = bases[source_name]
                else:
                    continue
                if source_base == node.func.id:
                    found.append(
                        f"{function.name}:{node.lineno}: {node.func.id}({argument_name}) "
                        f"where {argument_name}: {source_name}"
                    )
    return found


def test_no_forbidden_generic_aliases_outside_canonical_types() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path == CANONICAL_TYPES_PATH:
            continue
        for violation in forbidden_alias_symbol_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert (
        not offenders
    ), f"Forbidden generic aliases used outside {CANONICAL_TYPES_PATH.name}: {offenders}"


def test_no_enum_value_unwrap_inside_comparisons() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        for lineno in enum_value_in_comparison_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    assert not offenders, f"Enum .value unwraps inside comparisons: {offenders}"


def test_no_redundant_same_base_scalar_casts() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path == CANONICAL_TYPES_PATH:
            continue
        for violation in redundant_same_base_cast_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Redundant same-base scalar casts: {offenders}"


def test_forbidden_alias_mutation_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text(
            "from fedsira.domain.types import NonNegativeInt\n"
            "def handler(value: NonNegativeInt) -> int:\n"
            "    return value\n"
        )
        violations = forbidden_alias_symbol_violations(parse(path))
        assert "import:NonNegativeInt:1" in violations
        assert "name:NonNegativeInt:2" in violations


def test_qualified_forbidden_alias_attribute_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text("import fedsira.domain.types as t\nVALUE: t.NonNegativeInt = 0\n")
        assert forbidden_alias_symbol_violations(parse(path)) == ["attribute:NonNegativeInt:2"]


def test_enum_value_in_equality_mutation_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text(
            "from enum import StrEnum\n"
            "class Mode(StrEnum):\n"
            "    LOCAL = 'local'\n"
            "def handler(mode_text: str) -> bool:\n"
            "    return mode_text == Mode.LOCAL.value\n"
        )
        assert enum_value_in_comparison_violations(parse(path)) == ["5"]


def test_enum_value_in_membership_mutation_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text(
            "from enum import StrEnum\n"
            "class Mode(StrEnum):\n"
            "    LOCAL = 'local'\n"
            "def handler(mode_text: str) -> bool:\n"
            "    return mode_text in (Mode.LOCAL.value,)\n"
        )
        assert enum_value_in_comparison_violations(parse(path)) == ["5"]


def test_metric_result_value_comparison_is_not_flagged() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "compliant.py"
        path.write_text(
            "class MetricResult:\n"
            "    value: float | None\n"
            "def handler(result: MetricResult, threshold: float) -> bool:\n"
            "    return result.value is not None and result.value >= threshold\n"
        )
        assert enum_value_in_comparison_violations(parse(path)) == []


def test_redundant_same_base_cast_mutation_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text(
            "def handler(count: int, weight: float, label: str, flag: bool) -> None:\n"
            "    a = int(count)\n"
            "    b = float(weight)\n"
            "    c = str(label)\n"
            "    d = bool(flag)\n"
            "    return None\n"
        )
        violations = redundant_same_base_cast_violations(parse(path))
        assert violations == [
            "handler:2: int(count) where count: int",
            "handler:3: float(weight) where weight: float",
            "handler:4: str(label) where label: str",
            "handler:5: bool(flag) where flag: bool",
        ]


def test_cross_base_conversion_is_not_flagged_as_redundant() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "compliant.py"
        path.write_text("def handler(seed: int) -> str:\n    return str(seed)\n")
        assert redundant_same_base_cast_violations(parse(path)) == []


def test_discovery_scans_new_source_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "pkg"
        root.mkdir()
        (root / "existing.py").write_text("def first() -> None:\n    return None\n")
        scanned = {path.name for path in iter_python_files(root)}
        assert "existing.py" in scanned
        (root / "added_later.py").write_text("def second() -> None:\n    return None\n")
        rescanned = {path.name for path in iter_python_files(root)}
        assert "added_later.py" in rescanned


def test_new_source_file_with_forbidden_alias_is_flagged_by_full_tree_scan() -> None:
    probe = SRC_ROOT / "_architecture_alias_probe.py"
    assert not probe.exists(), "architecture probe file already exists"
    try:
        probe.write_text(
            "from fedsira.domain.types import FiniteFloat\n"
            "def handler(value: FiniteFloat) -> FiniteFloat:\n"
            "    return value\n",
            encoding="utf-8",
        )
        found: list[str] = []
        for path in iter_python_files(SRC_ROOT):
            if path == CANONICAL_TYPES_PATH:
                continue
            for violation in forbidden_alias_symbol_violations(parse(path)):
                found.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
        assert any("_architecture_alias_probe.py" in entry for entry in found)
    finally:
        if probe.exists():
            probe.unlink()
    assert not probe.exists()
