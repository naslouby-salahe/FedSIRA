import re
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files

STALE_ALIAS_PATTERNS = (
    re.compile(r"\bFedSira\b"),
    re.compile(r"\bFEDSIRA\b"),
    re.compile(r"\bfed[_-]sira\b", re.IGNORECASE),
    re.compile(r"\bKrumm\b"),
    re.compile(r"\bmilestone\b", re.IGNORECASE),
    re.compile(r"\bGitHub\s+issue\b", re.IGNORECASE),
    re.compile(r"\bREQ-\d{4}\b"),
    re.compile(r"\bM0\d\s*[—–-]\s*I\d{1,3}\b"),
    re.compile(r"\bM0\d\b\s+(experiment|dataset|invariant|reporting|reproduction)"),
)


def vocabulary_violations(text: str) -> list[str]:
    return [pattern.pattern for pattern in STALE_ALIAS_PATTERNS if pattern.search(text)]


def test_no_stale_project_or_algorithm_aliases() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        violations = vocabulary_violations(path.read_text(encoding="utf-8"))
        if violations:
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violations}")
    assert not offenders, f"Stale project vocabulary found: {offenders}"


def test_violation_detected_for_stale_alias() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "module.py"
        offending.write_text('PROJECT_NAME = "FedSira"\n')
        assert vocabulary_violations(offending.read_text(encoding="utf-8"))


def test_violation_detected_for_milestone_or_issue_reference() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "module.py"
        offending.write_text(
            'MESSAGE = "not implemented until the M02 dataset milestone (M02 — I10)"\n'
        )
        assert vocabulary_violations(offending.read_text(encoding="utf-8"))
