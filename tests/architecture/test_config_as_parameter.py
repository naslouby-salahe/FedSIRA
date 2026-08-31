import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

BOOTSTRAP_RELATIVE = frozenset(
    {
        "config/loading.py",
        "config/validation.py",
        "runtime/state.py",
    }
)
FORBIDDEN_TYPE_NAMES = frozenset({"ScientificConfig"})


def _annotation_names(annotation: ast.expr | None) -> set[str]:
    if annotation is None:
        return set()
    return {node.id for node in ast.walk(annotation) if isinstance(node, ast.Name)}


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def config_parameter_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _is_public(node.name):
            for argument in node.args.args + node.args.kwonlyargs:
                if argument.arg in {"self", "cls"}:
                    continue
                if FORBIDDEN_TYPE_NAMES & _annotation_names(argument.annotation):
                    found.append(f"{node.name}.{argument.arg}")
        if not isinstance(node, ast.ClassDef) or not _is_public(node.name):
            continue
        if node.name == "ApplicationContext":
            continue
        for member in node.body:
            if not isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not _is_public(member.name):
                continue
            for argument in member.args.args + member.args.kwonlyargs:
                if argument.arg in {"self", "cls"}:
                    continue
                if FORBIDDEN_TYPE_NAMES & _annotation_names(argument.annotation):
                    found.append(f"{node.name}.{member.name}.{argument.arg}")
    return found


def test_public_production_apis_do_not_take_scientific_config() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        relative = path.relative_to(SRC_ROOT).as_posix()
        if relative in BOOTSTRAP_RELATIVE:
            continue
        for violation in config_parameter_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"ScientificConfig passed as an ordinary public parameter: {offenders}"


def test_violation_detected_for_public_config_parameter() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text("def run(config: ScientificConfig) -> None:\n    return None\n")
        assert config_parameter_violations(parse(path)) == ["run.config"]
