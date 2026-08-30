import ast
import re
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, iter_python_files

TEMPORARY_MARKER_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")


def temporary_marker_violations(source: str) -> list[str]:
    return TEMPORARY_MARKER_PATTERN.findall(source)


def unfinished_statement_violations(source: str) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Pass):
            violations.append(f"pass@{node.lineno}")
            continue
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if isinstance(raised, ast.Name) and raised.id == "NotImplementedError":
            violations.append(f"NotImplementedError@{node.lineno}")
    return violations


def test_no_temporary_markers_in_repository_python_source() -> None:
    offenders: list[str] = []
    for path in iter_python_files(REPO_ROOT):
        if ".venv" in path.parts or ".nox" in path.parts:
            continue
        if path == Path(__file__):
            continue
        markers = temporary_marker_violations(path.read_text(encoding="utf-8"))
        if markers:
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{markers}")
    assert not offenders, f"Temporary development markers found: {offenders}"


def test_no_unfinished_statements_in_production_source() -> None:
    offenders: list[str] = []
    source_root = REPO_ROOT / "src"
    for path in iter_python_files(source_root):
        violations = unfinished_statement_violations(path.read_text(encoding="utf-8"))
        if violations:
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violations}")
    assert not offenders, f"Unfinished production statements found: {offenders}"


def test_violation_detected_for_todo_marker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "module.py"
        offending.write_text('MESSAGE = "TODO replace this"\n')
        assert temporary_marker_violations(offending.read_text(encoding="utf-8"))


def test_violation_detected_for_unfinished_statements() -> None:
    source = (
        "def unfinished() -> None:\n    pass\n\n"
        "def unsupported() -> None:\n    raise NotImplementedError\n"
    )
    assert unfinished_statement_violations(source) == ["pass@2", "NotImplementedError@5"]
