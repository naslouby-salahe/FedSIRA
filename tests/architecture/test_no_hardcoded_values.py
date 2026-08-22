import ast
import tempfile
from pathlib import Path

from _repo import CONFIG_PATH, REPO_ROOT, SRC_ROOT, governed_values, iter_python_files, parse


def numeric_literals(tree: ast.Module) -> set[float]:
    found: set[float] = set()
    for node in ast.walk(tree):
        value_node = node
        sign = 1.0
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
            value_node = node.operand
            sign = -1.0 if isinstance(node.op, ast.USub) else 1.0
        if isinstance(value_node, ast.Constant) and isinstance(value_node.value, int | float):
            if isinstance(value_node.value, bool):
                continue
            found.add(sign * float(value_node.value))
    return found


def display_path(path: Path) -> str:
    if REPO_ROOT in path.parents:
        return str(path.relative_to(REPO_ROOT))
    return str(path)


def find_hardcoded(root: Path) -> list[str]:
    values = governed_values()
    offenders: list[str] = []
    for path in iter_python_files(root):
        literals = numeric_literals(parse(path))
        matches = literals & values
        if matches:
            offenders.append(f"{display_path(path)}:{sorted(matches)}")
    return offenders


def test_no_governed_values_hardcoded_anywhere_in_src() -> None:
    offenders = find_hardcoded(SRC_ROOT)
    assert not offenders, f"Governed values hardcoded outside configs/fedsira.yaml: {offenders}"


def test_violation_detected_for_hardcoded_governed_value() -> None:
    if not CONFIG_PATH.exists():
        return
    sample_value = sorted(governed_values())[0]
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text(f"THRESHOLD = {sample_value!r}\n")
        offenders = find_hardcoded(Path(tmp))
        assert offenders
