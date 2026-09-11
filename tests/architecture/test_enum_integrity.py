import ast
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

ENUM_BASE_NAMES = {"Enum", "StrEnum", "IntEnum"}


def enum_class_defs(tree: ast.Module) -> list[ast.ClassDef]:
    found: list[ast.ClassDef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            base_names = {base.id for base in node.bases if isinstance(base, ast.Name)}
            if base_names & ENUM_BASE_NAMES:
                found.append(node)
    return found


def usages_outside(root: Path, defining_file: Path, symbol: str) -> int:
    count = 0
    for path in iter_python_files(root):
        if path == defining_file:
            continue
        source = path.read_text(encoding="utf-8")
        if symbol in source:
            count += 1
    return count


def annotation_names(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            found |= {
                child.id for child in ast.walk(node.annotation) if isinstance(child, ast.Name)
            }
    return found


def test_every_enum_is_referenced_outside_or_used_as_a_typed_field() -> None:
    unused: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        tree = parse(path)
        typed_names = annotation_names(tree)
        for enum_def in enum_class_defs(tree):
            if enum_def.name in typed_names:
                continue
            if usages_outside(SRC_ROOT, path, enum_def.name) == 0:
                unused.append(f"{path.relative_to(REPO_ROOT)}:{enum_def.name}")
    assert not unused, f"Enums defined but never referenced elsewhere: {unused}"


def test_enum_used_only_as_its_own_annotation_is_still_flagged(tmp_path: Path) -> None:
    defining = tmp_path / "defining.py"
    defining.write_text("from enum import Enum\n\nclass SelfAnnotatedEnum(Enum):\n    ONLY = 1\n")
    tree = parse(defining)
    assert "SelfAnnotatedEnum" not in annotation_names(tree)


def test_violation_detected_for_unused_enum(tmp_path: Path) -> None:
    defining = tmp_path / "defining.py"
    defining.write_text(
        "from enum import Enum\n\nclass NeverReferencedElsewhereEnum(Enum):\n    ONLY = 1\n"
    )
    other = tmp_path / "other.py"
    other.write_text("VALUE = 1\n")
    enum_defs = enum_class_defs(parse(defining))
    assert len(enum_defs) == 1
    assert usages_outside(tmp_path, defining, enum_defs[0].name) == 0
