import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

DOMAIN_CONCEPT_SUFFIXES = ("_id", "_seed", "_hash", "_digest", "_path", "_token")
PRIMITIVE_ANNOTATION_NAMES = {"str", "int", "float", "bool"}
SEMANTIC_TYPE_DEFINITION_FILE = SRC_ROOT / "domain" / "records.py"
MODEL_BASE_NAMES = {"BaseModel", "FrozenModel", "FrozenDomainModel"}
DATACLASS_DECORATOR_NAMES = {"dataclass"}


def _annotation_primitive_names(annotation: ast.expr) -> list[str]:
    found: list[str] = []
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name) and node.id in PRIMITIVE_ANNOTATION_NAMES:
            found.append(node.id)
    return found


def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _decorator_name(decorator: ast.expr) -> str | None:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _is_model_or_record(class_node: ast.ClassDef) -> bool:
    if any(_base_name(base) in MODEL_BASE_NAMES for base in class_node.bases):
        return True
    return any(
        _decorator_name(decorator) in DATACLASS_DECORATOR_NAMES
        for decorator in class_node.decorator_list
    )


def model_field_primitive_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for class_node in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
        if not _is_model_or_record(class_node):
            continue
        for statement in class_node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
                continue
            for primitive in _annotation_primitive_names(statement.annotation):
                found.append(f"{class_node.name}.{statement.target.id}: {primitive}")
    return found


def domain_identifier_violations(tree: ast.Module) -> list[str]:
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


def test_no_primitive_model_or_record_fields() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path == SEMANTIC_TYPE_DEFINITION_FILE:
            continue
        for violation in model_field_primitive_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Primitive-typed model/record fields: {offenders}"


def test_no_primitive_leaks_for_domain_identifiers() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        tree = parse(path)
        for violation in domain_identifier_violations(tree):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Primitive-typed domain concepts: {offenders}"


def test_model_field_violation_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text(
            "from dataclasses import dataclass\n\n"
            "@dataclass(frozen=True)\n"
            "class Sample:\n"
            "    count: int\n"
            "    enabled: bool\n"
        )
        assert model_field_primitive_violations(parse(offending)) == [
            "Sample.count: int",
            "Sample.enabled: bool",
        ]


def test_identifier_violation_detected_for_primitive_identifier() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text("def handler(experiment_id: str) -> None:\n    return None\n")
        assert domain_identifier_violations(parse(offending)) == ["experiment_id: str"]


def test_semantic_model_fields_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        compliant = Path(tmp) / "compliant.py"
        compliant.write_text(
            "from dataclasses import dataclass\n"
            "from fedsira.domain.records import CanonicalToken, PositiveInt\n\n"
            "@dataclass(frozen=True)\n"
            "class Sample:\n"
            "    identity: CanonicalToken\n"
            "    count: PositiveInt\n"
        )
        assert model_field_primitive_violations(parse(compliant)) == []
