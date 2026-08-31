import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, governed_values, iter_python_files, parse


def _uppercase_targets(node: ast.stmt) -> list[ast.Name]:
    if isinstance(node, ast.Assign):
        return [
            target
            for target in node.targets
            if isinstance(target, ast.Name) and target.id.isupper()
        ]
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id.isupper()
    ):
        return [node.target]
    return []


def module_level_constant_values(tree: ast.Module) -> set[float]:
    found: set[float] = set()
    for node in tree.body:
        if not _uppercase_targets(node):
            continue
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        value_expr: ast.expr | None = node.value
        if value_expr is None:
            continue
        value_node: ast.expr = value_expr
        sign = 1.0
        if isinstance(value_node, ast.UnaryOp) and isinstance(value_node.op, ast.USub | ast.UAdd):
            sign = -1.0 if isinstance(value_node.op, ast.USub) else 1.0
            value_node = value_node.operand
        if (
            isinstance(value_node, ast.Constant)
            and isinstance(value_node.value, int | float)
            and not isinstance(value_node.value, bool)
        ):
            found.add(sign * float(value_node.value))
    return found


def test_no_module_level_constants_duplicate_governed_values() -> None:
    values = governed_values()
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        found = module_level_constant_values(parse(path))
        matches = found & values
        if matches:
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{sorted(matches)}")
    assert not offenders, f"Duplicate configuration-authority constants: {offenders}"


def test_violation_detected_for_duplicated_constant() -> None:
    values = governed_values()
    if not values:
        return
    sample_value = sorted(values)[0]
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text(f"MIRRORED_THRESHOLD = {sample_value!r}\n")
        found = module_level_constant_values(parse(offending))
        assert found & values
        annotated = Path(tmp) / "annotated.py"
        annotated.write_text(f"MIRRORED_THRESHOLD: int = {sample_value!r}\n")
        found_annotated = module_level_constant_values(parse(annotated))
        assert found_annotated & values
