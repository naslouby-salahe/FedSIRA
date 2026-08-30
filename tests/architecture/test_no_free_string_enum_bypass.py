import ast
import tempfile
from collections import defaultdict
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

ENUM_BASE_NAMES = {"Enum", "StrEnum", "IntEnum"}
PRESENTATION_OR_PATH_STRINGS = {
    "NA",
    "Passed",
    "Failed",
    "Undefined",
    "Pending",
    "preprocessing",
    "BENIGN",
    "CANDIDATE_SCREEN",
    "none",
}


def enum_member_values(tree: ast.Module, module_path: Path) -> dict[str, list[str]]:
    values: dict[str, list[str]] = defaultdict(list)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = {base.id for base in node.bases if isinstance(base, ast.Name)}
        if not (base_names & ENUM_BASE_NAMES):
            continue
        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue
            for target in item.targets:
                if (
                    isinstance(target, ast.Name)
                    and isinstance(item.value, ast.Constant)
                    and (isinstance(item.value.value, str))
                ):
                    values[item.value.value].append(f"{module_path}:{node.name}.{target.id}")
    return values


def string_literals(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append(node.value)
    return found


def test_no_free_string_enum_value_bypass_across_modules() -> None:
    member_values: dict[str, list[str]] = {}
    for path in iter_python_files(SRC_ROOT):
        for value, owners in enum_member_values(parse(path), path).items():
            member_values.setdefault(value, []).extend(owners)
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        tree = parse(path)
        module_owners = {
            value
            for value, owners in member_values.items()
            if any(str(path) in owner for owner in owners)
        }
        for literal in string_literals(tree):
            if literal in PRESENTATION_OR_PATH_STRINGS:
                continue
            if literal not in member_values:
                continue
            if literal in module_owners:
                continue
            owners = member_values[literal]
            owners_text = ", ".join(sorted(owners)[:3])
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{literal!r} (owned by {owners_text})")
    assert not offenders, (
        "Free-string enum values used outside their defining module; "
        f"reference the enum member instead: {offenders}"
    )


def test_violation_detected_for_free_string_enum_value() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "owner.py").write_text(
            "from enum import StrEnum\n\nclass Status(StrEnum):\n    ACTIVE = 'active'\n"
        )
        (root / "user.py").write_text("def handler() -> str:\n    return 'active'\n")
        member_values: dict[str, list[str]] = {}
        for path in root.glob("*.py"):
            for value, owners in enum_member_values(parse(path), path).items():
                member_values.setdefault(value, []).extend(owners)
        offenders: list[str] = []
        for path in root.glob("*.py"):
            tree = parse(path)
            module_owners = {
                value
                for value, owners in member_values.items()
                if any(str(path) in owner for owner in owners)
            }
            for literal in string_literals(tree):
                if literal in PRESENTATION_OR_PATH_STRINGS:
                    continue
                if literal not in member_values:
                    continue
                if literal in module_owners:
                    continue
                offenders.append(literal)
        assert offenders == ["active"]


def test_owner_module_usage_not_flagged() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "owner.py").write_text(
            "from enum import StrEnum\n\n"
            "class Status(StrEnum):\n    ACTIVE = 'active'\n\n"
            "VALUE = Status.ACTIVE.value\n"
        )
        member_values: dict[str, list[str]] = {}
        for path in root.glob("*.py"):
            for value, owners in enum_member_values(parse(path), path).items():
                member_values.setdefault(value, []).extend(owners)
        offenders: list[str] = []
        for path in root.glob("*.py"):
            tree = parse(path)
            module_owners = {
                value
                for value, owners in member_values.items()
                if any(str(path) in owner for owner in owners)
            }
            for literal in string_literals(tree):
                if literal in PRESENTATION_OR_PATH_STRINGS:
                    continue
                if literal not in member_values:
                    continue
                if literal in module_owners:
                    continue
                offenders.append(literal)
        assert offenders == []
