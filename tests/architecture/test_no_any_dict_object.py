import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

ALLOWED_RAW_TYPE_FILES = {
    SRC_ROOT / "config" / "loading.py",
    SRC_ROOT / "runtime" / "logging.py",
}

ALWAYS_FORBIDDEN_NAMES = {"Any", "object"}
BARE_MAPPING_NAMES = {"dict", "Dict"}


def annotation_occurrences(annotation: ast.expr) -> list[ast.Name]:
    occurrences: list[ast.Name] = []

    def visit(node: ast.expr, parent_is_subscript_value: bool) -> None:
        if isinstance(node, ast.Name):
            if (
                node.id in ALWAYS_FORBIDDEN_NAMES
                or node.id in BARE_MAPPING_NAMES
                and not parent_is_subscript_value
            ):
                occurrences.append(node)
        elif isinstance(node, ast.Subscript):
            visit(node.value, True)
            visit(node.slice, False)
        elif isinstance(node, ast.Tuple):
            for element in node.elts:
                visit(element, False)
        elif isinstance(node, ast.BinOp):
            visit(node.left, False)
            visit(node.right, False)

    visit(annotation, False)
    return occurrences


def annotation_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        annotation = None
        if isinstance(node, ast.arg | ast.AnnAssign):
            annotation = node.annotation
        elif isinstance(node, ast.FunctionDef):
            annotation = node.returns
        if annotation is None:
            continue
        found.extend(occurrence.id for occurrence in annotation_occurrences(annotation))
    return found


def test_no_forbidden_annotations_outside_allowed_boundary() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path in ALLOWED_RAW_TYPE_FILES:
            continue
        tree = parse(path)
        for name in annotation_violations(tree):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{name}")
    assert not offenders, f"Forbidden Any/dict/object annotations: {offenders}"


def test_violation_detected_for_any_annotation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text(
            "from typing import Any\n\ndef handler(value: Any) -> None:\n    return None\n"
        )
        assert "Any" in annotation_violations(parse(offending))


def test_violation_detected_for_bare_dict_annotation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text("def handler(value: dict) -> None:\n    return None\n")
        assert "dict" in annotation_violations(parse(offending))


def test_parameterized_dict_annotation_is_allowed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        compliant = Path(tmp) / "compliant.py"
        compliant.write_text("def handler(value: dict[str, int]) -> None:\n    return None\n")
        assert annotation_violations(parse(compliant)) == []


def test_compliant_annotation_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        compliant = Path(tmp) / "compliant.py"
        compliant.write_text("def handler(value: int) -> None:\n    return None\n")
        assert annotation_violations(parse(compliant)) == []
