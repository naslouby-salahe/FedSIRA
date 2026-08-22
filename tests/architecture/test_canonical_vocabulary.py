import re
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files

STALE_ALIAS_PATTERNS = (
    re.compile(r"\bFedSira\b"),
    re.compile(r"\bFEDSIRA\b"),
    re.compile(r"\bfed[_-]sira\b", re.IGNORECASE),
    re.compile(r"\bKrumm\b"),
)


def vocabulary_violations(text: str) -> list[str]:
    found: list[str] = []
    for pattern in STALE_ALIAS_PATTERNS:
        if pattern.search(text):
            found.append(pattern.pattern)
    return found


def test_no_stale_project_or_algorithm_aliases() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        violations = vocabulary_violations(path.read_text(encoding="utf-8"))
        if violations:
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violations}")
    assert not offenders, f"Stale/non-canonical vocabulary found: {offenders}"


def test_violation_detected_for_stale_alias() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "module.py"
        offending.write_text('PROJECT_NAME = "FedSira"\n')
        assert vocabulary_violations(offending.read_text(encoding="utf-8"))
