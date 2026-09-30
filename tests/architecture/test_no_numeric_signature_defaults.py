import ast
import tempfile
from pathlib import Path

from _repo import SRC_ROOT, iter_python_files, parse


def _numeric_constant(node: ast.expr) -> bool:
    value = node.operand if isinstance(node, ast.UnaryOp) else node
    return (
        isinstance(value, ast.Constant)
        and isinstance(value.value, int | float)
        and not isinstance(value.value, bool)
    )


def numeric_signature_defaults(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        defaults = (
            *node.args.defaults,
            *(item for item in node.args.kw_defaults if item is not None),
        )
        for default in defaults:
            if _numeric_constant(default):
                found.append(f"{node.name}:{node.lineno}")
    return found


def numeric_or_fallbacks(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BoolOp) or not isinstance(node.op, ast.Or):
            continue
        if any(_numeric_constant(value) for value in node.values):
            found.append(f"line {node.lineno}")
    return found


def test_signature_defaults_are_not_numeric_and_have_no_numeric_or_fallback() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        tree = parse(path)
        relative = path.relative_to(SRC_ROOT)
        offenders.extend(f"{relative}:{item}" for item in numeric_signature_defaults(tree))
        offenders.extend(f"{relative}:{item}" for item in numeric_or_fallbacks(tree))
    assert not offenders, f"Numeric signature defaults or or-fallbacks: {offenders}"


def test_numeric_signature_default_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text("def measure(warmup: int = 0) -> int:\n    return warmup\n")
        assert numeric_signature_defaults(parse(path))


def test_numeric_or_fallback_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text("def value(observed: int | None) -> int:\n    return observed or 0\n")
        assert numeric_or_fallbacks(parse(path))
