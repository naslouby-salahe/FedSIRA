import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse


def is_pure_redirect(tree: ast.Module) -> bool:
    statements = [node for node in tree.body if not isinstance(node, ast.Expr)]
    if not statements:
        return False
    return all(isinstance(node, ast.Import | ast.ImportFrom) for node in statements)


def test_no_non_init_module_is_a_pure_redirect() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path.name == "__init__.py":
            continue
        if is_pure_redirect(parse(path)):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"Pure redirect/shim modules found: {offenders}"


def test_violation_detected_for_redirect_module() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        redirect = Path(tmp) / "legacy_alias.py"
        redirect.write_text("from fedsira.domain.enums import ExperimentState\n")
        assert is_pure_redirect(parse(redirect))


def test_compliant_module_with_definitions_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        compliant = Path(tmp) / "module.py"
        compliant.write_text("def compute(value: int) -> int:\n    return value + 1\n")
        assert not is_pure_redirect(parse(compliant))
