import ast
import re
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

BANNED_GENERIC_STEMS = {"utils", "helper", "helpers", "manager", "processor", "base", "misc"}
ARTIFICIAL_VERSION_PATTERN = re.compile(r"(_v\d+$|_final\d*$|_new$|_old$|_copy$)", re.IGNORECASE)


def naming_violations(tree: ast.Module, module_stem: str) -> list[str]:
    found: list[str] = []
    if module_stem.lower() in BANNED_GENERIC_STEMS:
        found.append(f"module:{module_stem}")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef):
            name = node.name
            if name.lower() in BANNED_GENERIC_STEMS:
                found.append(f"symbol:{name}")
            if ARTIFICIAL_VERSION_PATTERN.search(name):
                found.append(f"symbol:{name}")
            if len(name.strip("_")) <= 1 and name not in {"_"}:
                found.append(f"symbol:{name}")
    return found


def test_no_banned_generic_or_artificial_names() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        for violation in naming_violations(parse(path), path.stem):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Naming policy violations: {offenders}"


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
