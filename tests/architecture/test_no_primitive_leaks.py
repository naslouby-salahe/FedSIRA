import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

DOMAIN_CONCEPT_SUFFIXES = ("_id", "_seed", "_hash", "_digest", "_path", "_token")
PRIMITIVE_ANNOTATION_NAMES = {"str", "int", "float", "bool"}
BOUNDARY_PACKAGES = ("domain", "config", "artifacts")


def leak_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        candidates: list[tuple[str, ast.expr | None]] = []
        if isinstance(node, ast.arg):
            candidates.append((node.arg, node.annotation))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            candidates.append((node.target.id, node.annotation))
        for name, annotation in candidates:
            if annotation is None or not isinstance(annotation, ast.Name):
                continue
            if annotation.id not in PRIMITIVE_ANNOTATION_NAMES:
                continue
            if name.lower().endswith(DOMAIN_CONCEPT_SUFFIXES):
                found.append(f"{name}: {annotation.id}")
    return found


def test_no_primitive_leaks_for_domain_concepts() -> None:
    offenders: list[str] = []
    for package in BOUNDARY_PACKAGES:
        for path in iter_python_files(SRC_ROOT / package):
            tree = parse(path)
            for violation in leak_violations(tree):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Primitive-typed domain concepts: {offenders}"


def test_violation_detected_for_primitive_identifier() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text("def handler(experiment_id: str) -> None:\n    return None\n")
        assert leak_violations(parse(offending)) == ["experiment_id: str"]


def test_compliant_domain_type_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        compliant = Path(tmp) / "compliant.py"
        compliant.write_text(
            "from fedsira.domain.records import ExperimentId\n\n"
            "def handler(experiment_id: ExperimentId) -> None:\n    return None\n"
        )
        assert leak_violations(parse(compliant)) == []
