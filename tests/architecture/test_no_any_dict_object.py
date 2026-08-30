import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

FORBIDDEN_TYPE_NAMES = {"Any", "Dict", "dict", "object"}


def annotation_occurrences(annotation: ast.expr) -> list[str]:
    return sorted(
        node.id
        for node in ast.walk(annotation)
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_TYPE_NAMES
    )


def annotation_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        annotation: ast.expr | None = None
        if isinstance(node, ast.arg | ast.AnnAssign):
            annotation = node.annotation
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            annotation = node.returns
        if annotation is not None:
            found.extend(annotation_occurrences(annotation))
    return found


def forbidden_symbol_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_TYPE_NAMES:
            found.append(f"name:{node.id}:{node.lineno}")
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_TYPE_NAMES:
            found.append(f"attribute:{node.attr}:{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            for imported in node.names:
                if imported.name in FORBIDDEN_TYPE_NAMES:
                    found.append(f"import:{imported.name}:{node.lineno}")
        elif isinstance(node, ast.Import):
            for imported in node.names:
                terminal_name = imported.name.rsplit(".", maxsplit=1)[-1]
                if terminal_name in FORBIDDEN_TYPE_NAMES:
                    found.append(f"import:{terminal_name}:{node.lineno}")
    return found


def raw_mapping_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            found.append(f"dict-literal:{node.lineno}")
        elif isinstance(node, ast.DictComp):
            found.append(f"dict-comprehension:{node.lineno}")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "dict"
        ):
            found.append(f"dict-constructor:{node.lineno}")
    return found


def test_no_any_dict_or_object_annotations() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        for name in annotation_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{name}")
    assert not offenders, f"Forbidden Any/dict/object annotations: {offenders}"


def test_no_any_dict_or_object_symbols() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        for violation in forbidden_symbol_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Forbidden Any/dict/object symbols: {offenders}"


def test_no_raw_dictionary_construction() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        for violation in raw_mapping_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Raw dictionaries are forbidden: {offenders}"


def test_any_annotation_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text(
            "from typing import Any\n\ndef handler(value: Any) -> None:\n    return None\n"
        )
        assert annotation_violations(parse(offending)) == ["Any"]


def test_parameterized_dict_annotation_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text("def handler(value: dict[str, int]) -> None:\n    return None\n")
        assert annotation_violations(parse(offending)) == ["dict"]


def test_dictionary_construction_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text('VALUE = {"a": 1}\n')
        assert raw_mapping_violations(parse(offending)) == ["dict-literal:1"]


def test_forbidden_symbol_usage_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text(
            "import typing\n\n"
            "def handler(value):\n"
            "    return isinstance(value, dict) or typing.Any is object\n"
        )
        violations = forbidden_symbol_violations(parse(offending))
        assert "name:dict:4" in violations
        assert "attribute:Any:4" in violations
        assert "name:object:4" in violations
