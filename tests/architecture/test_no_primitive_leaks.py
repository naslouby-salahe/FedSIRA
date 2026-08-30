import ast
import tempfile
from collections.abc import Callable
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse

DOMAIN_CONCEPT_SUFFIXES = ("_id", "_seed", "_hash", "_digest", "_path", "_token")
PRIMITIVES = {"bool", "bytearray", "bytes", "complex", "float", "int", "str"}
SCALAR_FOUNDATIONS = {
    "BooleanValue",
    "FiniteFloat",
    "NonNegativeFloat",
    "NonNegativeInt",
    "Percentage",
    "PositiveFloat",
    "PositiveInt",
    "Probability",
    "TextValue",
    "Uint32Bound",
}
CONFIG_SCHEMA_FILE = SRC_ROOT / "config" / "schema.py"
MODEL_BASES = {"BaseModel", "FrozenConfigModel", "FrozenDomainModel", "TensorDomainModel"}

ViolationDetector = Callable[[ast.Module], list[str]]


def _names(annotation: ast.expr) -> set[str]:
    return {node.id for node in ast.walk(annotation) if isinstance(node, ast.Name)}


def _primitives(annotation: ast.expr) -> list[str]:
    return sorted(_names(annotation) & PRIMITIVES)


def _name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _record(class_node: ast.ClassDef) -> bool:
    if any(_name(base) in MODEL_BASES for base in class_node.bases):
        return True
    for decorator in class_node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if _name(target) == "dataclass":
            return True
    return False


def _function_arguments(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.arg]:
    arguments = [
        *function.args.posonlyargs,
        *function.args.args,
        *function.args.kwonlyargs,
    ]
    if function.args.vararg is not None:
        arguments.append(function.args.vararg)
    if function.args.kwarg is not None:
        arguments.append(function.args.kwarg)
    return arguments


def model_field_primitive_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for class_node in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
        if not _record(class_node):
            continue
        for statement in class_node.body:
            if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                for primitive in _primitives(statement.annotation):
                    found.append(f"{class_node.name}.{statement.target.id}: {primitive}")
    return found


def function_boundary_primitive_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for function in (
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ):
        for argument in _function_arguments(function):
            if argument.arg in {"self", "cls"} or argument.annotation is None:
                continue
            for primitive in _primitives(argument.annotation):
                found.append(f"{function.name}.{argument.arg}: {primitive}")
        if function.returns is not None:
            for primitive in _primitives(function.returns):
                found.append(f"{function.name}.return: {primitive}")
    return found


def untyped_function_boundary_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for function in (
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ):
        for argument in _function_arguments(function):
            if argument.arg in {"self", "cls"}:
                continue
            if argument.annotation is None:
                found.append(f"{function.name}.{argument.arg}: missing annotation")
        if function.returns is None:
            found.append(f"{function.name}.return: missing annotation")
    return found


def config_scalar_foundation_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for class_node in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
        if not _record(class_node):
            continue
        for statement in class_node.body:
            if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                for type_name in sorted(_names(statement.annotation) & SCALAR_FOUNDATIONS):
                    found.append(f"{class_node.name}.{statement.target.id}: {type_name}")
    return found


def domain_identifier_violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            name, annotation = node.arg, node.annotation
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, annotation = node.target.id, node.annotation
        else:
            continue
        if annotation is None or not name.lower().endswith(DOMAIN_CONCEPT_SUFFIXES):
            continue
        for primitive in _primitives(annotation):
            found.append(f"{name}: {primitive}")
    return found


def _all_violations(detector: ViolationDetector) -> list[str]:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        for violation in detector(parse(path)):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{violation}")
    return offenders


def test_no_primitive_model_or_record_fields() -> None:
    offenders = _all_violations(model_field_primitive_violations)
    assert not offenders, f"Primitive-typed model/record fields: {offenders}"


def test_no_primitive_function_inputs_or_outputs() -> None:
    offenders = _all_violations(function_boundary_primitive_violations)
    assert not offenders, f"Primitive production method boundaries: {offenders}"


def test_no_untyped_function_inputs_or_outputs() -> None:
    offenders = _all_violations(untyped_function_boundary_violations)
    assert not offenders, f"Untyped production method boundaries: {offenders}"


def test_config_models_use_meaning_specific_aliases() -> None:
    offenders = config_scalar_foundation_violations(parse(CONFIG_SCHEMA_FILE))
    assert not offenders, f"Config fields use storage-oriented scalar aliases: {offenders}"


def test_no_primitive_leaks_for_domain_identifiers() -> None:
    offenders = _all_violations(domain_identifier_violations)
    assert not offenders, f"Primitive-typed domain concepts: {offenders}"


def test_function_boundary_violation_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text("def handler(value: str) -> int:\n    return len(value)\n")
        assert function_boundary_primitive_violations(parse(path)) == [
            "handler.value: str",
            "handler.return: int",
        ]


def test_untyped_function_boundary_violation_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offending.py"
        path.write_text("def handler(value):\n    return value\n")
        assert untyped_function_boundary_violations(parse(path)) == [
            "handler.value: missing annotation",
            "handler.return: missing annotation",
        ]
