import re
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, iter_python_files

TEMPORARY_MARKER_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")


def temporary_marker_violations(source: str) -> list[str]:
    return TEMPORARY_MARKER_PATTERN.findall(source)


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


def test_violation_detected_for_todo_marker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "module.py"
        offending.write_text('MESSAGE = "TODO replace this"\n')
        assert temporary_marker_violations(offending.read_text(encoding="utf-8"))
