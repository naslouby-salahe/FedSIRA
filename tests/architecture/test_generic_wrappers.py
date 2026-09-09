import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

FORBIDDEN_GENERIC_ALIASES = {
    "FiniteFloat",
    "NonNegativeFloat",
    "NonNegativeInt",
    "OpenUnitInterval",
    "PositiveFloat",
    "PositiveInt",
    "SignedInt",
    "UnitInterval",
}
CANONICAL_TYPES_PATH = SRC_ROOT / "domain" / "types.py"


def generic_wrapper_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_GENERIC_ALIASES:
            found.append(f"name:{node.id}:{node.lineno}")
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_GENERIC_ALIASES:
            found.append(f"attribute:{node.attr}:{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            for imported in node.names:
                if imported.name in FORBIDDEN_GENERIC_ALIASES:
                    found.append(f"import:{imported.name}:{node.lineno}")
    return found


def test_production_code_uses_no_generic_numeric_wrappers() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path == CANONICAL_TYPES_PATH:
            continue
        for violation in generic_wrapper_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Generic primitive wrappers in production code: {offenders}"


def test_violation_detected_in_private_nested_generic_and_alias() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text(
            "from fedsira.domain.types import PositiveInt\n"
            "import fedsira.domain.types as domain_types\n"
            "Alias = tuple[PositiveInt, ...]\n"
            "def _private(values: list[domain_types.FiniteFloat]) -> None:\n"
            "    def nested(value: PositiveInt) -> None:\n"
            "        return None\n"
            "    return None\n"
        )
        violations = generic_wrapper_violations(parse(path))
        assert "import:PositiveInt:1" in violations
        assert "name:PositiveInt:3" in violations
        assert "attribute:FiniteFloat:4" in violations
        assert "name:PositiveInt:5" in violations


def test_qualified_forbidden_alias_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text("import fedsira.domain.types as t\nVALUE: t.NonNegativeInt = 0\n")
        assert generic_wrapper_violations(parse(path)) == ["attribute:NonNegativeInt:2"]
