import ast
import re
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

BANNED_GENERIC_STEMS = {"utils", "helper", "helpers", "manager", "processor", "base", "misc"}
ARTIFICIAL_VERSION_PATTERN = re.compile(r"(_v\d+$|_final\d*$|_new$|_old$|_copy$)", re.IGNORECASE)
FORBIDDEN_NAMING_PATTERN = re.compile("c" "anonical", re.IGNORECASE)
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


def naming_violations(tree: ast.Module, module_stem: str) -> list[str]:
    found: list[str] = []
    if module_stem.lower() in BANNED_GENERIC_STEMS:
        found.append(f"module:{module_stem}")
    if FORBIDDEN_NAMING_PATTERN.search(module_stem):
        found.append(f"module:{module_stem}")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef):
            name = node.name
            if name.lower() in BANNED_GENERIC_STEMS:
                found.append(f"symbol:{name}")
            if ARTIFICIAL_VERSION_PATTERN.search(name):
                found.append(f"symbol:{name}")
            if FORBIDDEN_NAMING_PATTERN.search(name):
                found.append(f"symbol:{name}")
            if len(name.strip("_")) <= 1 and name not in {"_"}:
                found.append(f"symbol:{name}")
        if isinstance(node, ast.Name) and FORBIDDEN_NAMING_PATTERN.search(node.id):
            found.append(f"identifier:{node.id}")
        if isinstance(node, ast.arg) and FORBIDDEN_NAMING_PATTERN.search(node.arg):
            found.append(f"argument:{node.arg}")
        if isinstance(node, ast.Attribute) and FORBIDDEN_NAMING_PATTERN.search(node.attr):
            found.append(f"attribute:{node.attr}")
    return found


def vocabulary_violations(text: str) -> list[str]:
    return [pattern.pattern for pattern in STALE_ALIAS_PATTERNS if pattern.search(text)]


def test_no_banned_generic_artificial_or_forbidden_names() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        for violation in naming_violations(parse(path), path.stem):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Naming policy violations: {offenders}"


def test_no_stale_project_or_algorithm_aliases() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        violations = vocabulary_violations(path.read_text(encoding="utf-8"))
        if violations:
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violations}")
    assert not offenders, f"Stale project vocabulary found: {offenders}"


def test_violation_detected_for_generic_module_name() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "utils.py"
        offending.write_text("def f() -> int:\n    return 1\n")
        assert naming_violations(parse(offending), offending.stem)


def test_violation_detected_for_versioned_symbol_name() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "module.py"
        offending.write_text("def compute_final2() -> int:\n    return 1\n")
        violations = naming_violations(parse(offending), offending.stem)
        assert "symbol:compute_final2" in violations


def test_violation_detected_for_forbidden_identifier() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "module.py"
        forbidden_name = "c" "anonical_value"
        offending.write_text(f"{forbidden_name} = 1\n")
        assert naming_violations(parse(offending), offending.stem)


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
