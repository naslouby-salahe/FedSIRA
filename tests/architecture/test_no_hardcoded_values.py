import ast
import tempfile
from pathlib import Path

from _repo import CONFIG_PATH, REPO_ROOT, SRC_ROOT, governed_values, iter_python_files, parse


def _intrinsic_numeric_constants(tree: ast.Module) -> set[int]:
    ignored: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "int"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == 16
        ):
            ignored.add(id(node.args[1]))
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "Field":
            continue
        for keyword in node.keywords:
            if keyword.arg not in {"min_length", "max_length"}:
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value == 32:
                ignored.add(id(keyword.value))
    return ignored


def numeric_literals(tree: ast.Module) -> set[float]:
    ignored = _intrinsic_numeric_constants(tree)
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
            if id(value_node) in ignored:
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


def test_sha256_digest_length_and_hex_radix_are_not_treated_as_governed_copies() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        intrinsic = Path(tmp) / "intrinsic.py"
        intrinsic.write_text(
            "from pydantic import Field\n"
            "from typing import Annotated\n"
            "Digest = Annotated[bytes, Field(min_length=32, max_length=32)]\n"
            "value = int('ff', 16)\n"
        )
        assert not find_hardcoded(Path(tmp))
