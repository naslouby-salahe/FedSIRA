import ast
import tempfile
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

GENERIC_WRAPPERS = {
    "BooleanValue",
    "FiniteFloat",
    "NonNegativeFloat",
    "NonNegativeInt",
    "PositiveFloat",
    "PositiveInt",
    "TextValue",
}


def _annotation_names(annotation: ast.expr | None) -> set[str]:
    if annotation is None:
        return set()
    return {node.id for node in ast.walk(annotation) if isinstance(node, ast.Name)}


def _iter_public_callables(
    tree: ast.Module,
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith(
            "_"
        ):
            found.append((node.name, node))
        if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
            continue
        for member in node.body:
            if not isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if member.name.startswith("_") and member.name != "__init__":
                continue
            found.append((f"{node.name}.{member.name}", member))
    return found


def generic_wrapper_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for owner, function in _iter_public_callables(tree):
        for argument in function.args.args + function.args.kwonlyargs:
            if argument.arg in {"self", "cls"}:
                continue
            wrappers = sorted(_annotation_names(argument.annotation) & GENERIC_WRAPPERS)
            for wrapper in wrappers:
                found.append(f"{owner}.{argument.arg}:{wrapper}")
        wrappers = sorted(_annotation_names(function.returns) & GENERIC_WRAPPERS)
        for wrapper in wrappers:
            found.append(f"{owner}->:{wrapper}")
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
            continue
        for member in node.body:
            if not isinstance(member, ast.AnnAssign) or not isinstance(member.target, ast.Name):
                continue
            if member.target.id.startswith("_"):
                continue
            wrappers = sorted(_annotation_names(member.annotation) & GENERIC_WRAPPERS)
            for wrapper in wrappers:
                found.append(f"{node.name}.{member.target.id}:{wrapper}")
    return found


def test_public_production_apis_do_not_use_generic_numeric_wrappers() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path.name == "records.py" and path.parent.name == "domain":
            continue
        for violation in generic_wrapper_violations(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    assert not offenders, f"Generic primitive wrappers on public APIs: {offenders}"


def test_violation_detected_for_generic_wrapper_parameter() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text("def count_items(value: PositiveInt) -> BooleanValue:\n    return True\n")
        assert generic_wrapper_violations(parse(path)) == [
            "count_items.value:PositiveInt",
            "count_items->:BooleanValue",
        ]


def test_violation_detected_for_generic_wrapper_field_and_init() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text(
            "class Result:\n"
            "    survives: BooleanValue\n"
            "    def __init__(self, count: PositiveInt) -> FiniteFloat:\n"
            "        self.count = count\n"
        )
        assert generic_wrapper_violations(parse(path)) == [
            "Result.__init__.count:PositiveInt",
            "Result.__init__->:FiniteFloat",
            "Result.survives:BooleanValue",
        ]
