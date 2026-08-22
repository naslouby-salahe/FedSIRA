import ast
import tempfile
from pathlib import Path

from _repo import SRC_ROOT, iter_python_files, parse

BOUNDARY_PACKAGES = ("domain", "config", "artifacts")


def public_top_level_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]


def is_fully_annotated(function: ast.FunctionDef) -> bool:
    if function.returns is None:
        return False
    for argument in function.args.args + function.args.kwonlyargs:
        if argument.arg == "self":
            continue
        if argument.annotation is None:
            return False
    return True


def violations_in_tree(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for function in public_top_level_functions(tree):
        if not is_fully_annotated(function):
            found.append(function.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for member in node.body:
                if (
                    isinstance(member, ast.FunctionDef)
                    and not member.name.startswith("_")
                    and not is_fully_annotated(member)
                ):
                    found.append(f"{node.name}.{member.name}")
    return found


def test_public_boundary_functions_are_fully_annotated() -> None:
    offenders: list[str] = []
    for package in BOUNDARY_PACKAGES:
        for path in iter_python_files(SRC_ROOT / package):
            tree = parse(path)
            for name in violations_in_tree(tree):
                offenders.append(f"{path.relative_to(SRC_ROOT.parent.parent)}:{name}")
    assert not offenders, f"Unannotated public boundary members: {offenders}"


def test_violation_detected_for_unannotated_public_function() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text("def public_entry(value):\n    return value\n")
        tree = parse(offending)
        assert violations_in_tree(tree) == ["public_entry"]


def test_compliant_function_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        compliant = Path(tmp) / "compliant.py"
        compliant.write_text("def public_entry(value: int) -> int:\n    return value\n")
        tree = parse(compliant)
        assert violations_in_tree(tree) == []
