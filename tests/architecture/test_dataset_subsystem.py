import ast
from pathlib import Path

from _repo import SRC_ROOT, iter_python_files, parse

DATASETS_ROOT = SRC_ROOT / "datasets"
FORBIDDEN_DATASET_IMPORTS = {
    "sqlite3",
    "pandas",
    "pyarrow",
    "struct",
    "heapq",
}
FORBIDDEN_ARROW_NAMES = {
    "_ArrowDataType",
    "_ArrowArray",
    "_ArrowSchema",
    "_ArrowTable",
    "_ArrowModule",
    "_ParquetWriter",
    "_ParquetWriterFactory",
    "_ParquetModule",
    "_ParquetScalarKind",
    "SqliteScalar",
    "ParquetScalar",
    "FeaturePayloadBytes",
    "SecondaryPreparationStore",
}
PRIMITIVES = {"str", "int", "float", "bool", "dict", "object", "Any"}


def _dataset_files() -> list[Path]:
    return list(iter_python_files(DATASETS_ROOT))


def test_datasets_do_not_import_replaced_tabular_libraries() -> None:
    offenders: list[str] = []
    for path in _dataset_files():
        tree = parse(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", maxsplit=1)[0]
                    if root in FORBIDDEN_DATASET_IMPORTS:
                        offenders.append(f"{path.relative_to(SRC_ROOT)}:{root}")
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".", maxsplit=1)[0]
                if root in FORBIDDEN_DATASET_IMPORTS:
                    offenders.append(f"{path.relative_to(SRC_ROOT)}:{root}")
    assert not offenders, f"forbidden dataset library imports: {offenders}"


def test_datasets_do_not_keep_manual_arrow_sqlite_abstractions() -> None:
    offenders: list[str] = []
    for path in _dataset_files():
        names = {node.name for node in ast.walk(parse(path)) if isinstance(node, ast.ClassDef)}
        names.update(
            node.name for node in ast.walk(parse(path)) if isinstance(node, ast.FunctionDef)
        )
        leaked = sorted(names & FORBIDDEN_ARROW_NAMES)
        if leaked:
            offenders.append(f"{path.relative_to(SRC_ROOT)}:{leaked}")
    assert not offenders, f"removed dataset infrastructure still present: {offenders}"


def test_datasets_use_enums_for_closed_identities() -> None:
    source = (DATASETS_ROOT / "common.py").read_text(encoding="utf-8")
    assert "class DatasetExclusionReason" in source
    assert "class RoleWindow" in source
    schema = (DATASETS_ROOT / "nbaiot" / "schema.py").read_text(encoding="utf-8")
    assert "class NBaiotDomain" in schema
    assert "class NBaiotClass" in schema
    secondary = (DATASETS_ROOT / "ciciot2023" / "schema.py").read_text(encoding="utf-8")
    assert "class CICIoT2023PseudoDomain" in secondary
    assert "class CICIoTSpecialLabel" in secondary


def test_preprocess_workflow_calls_materialize_functions() -> None:
    tree = parse(DATASETS_ROOT / "preprocess.py")
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    expected = {
        "materialize_nbaiot_prepared_views",
        "materialize_ciciot2023_prepared_views",
        "publish_or_reuse_artifact_payload",
    }
    assert expected <= names, f"preprocess missing {expected - names}"


def test_dataset_public_functions_avoid_primitive_annotations() -> None:
    offenders: list[str] = []
    for path in _dataset_files():
        tree = parse(path)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
                continue
            for argument in node.args.args + node.args.kwonlyargs:
                if argument.arg in {"self", "cls"} or argument.annotation is None:
                    continue
                primitive_names = {
                    child.id
                    for child in ast.walk(argument.annotation)
                    if isinstance(child, ast.Name) and child.id in PRIMITIVES
                }
                if primitive_names:
                    offenders.append(
                        f"{path.relative_to(SRC_ROOT)}:{node.name}:{argument.arg}:{sorted(primitive_names)}"
                    )
            if node.returns is not None:
                primitive_returns = {
                    child.id
                    for child in ast.walk(node.returns)
                    if isinstance(child, ast.Name) and child.id in PRIMITIVES
                }
                if primitive_returns:
                    offenders.append(
                        f"{path.relative_to(SRC_ROOT)}:{node.name}:return:{sorted(primitive_returns)}"
                    )
    assert not offenders, f"dataset public API primitive leaks: {offenders}"


def test_obsolete_dataset_modules_are_gone() -> None:
    obsolete = (
        DATASETS_ROOT / "roles.py",
        DATASETS_ROOT / "sampling.py",
        DATASETS_ROOT / "scaling.py",
        DATASETS_ROOT / "nbaiot" / "loading.py",
        DATASETS_ROOT / "nbaiot" / "preprocessing.py",
        DATASETS_ROOT / "ciciot2023" / "loading.py",
        DATASETS_ROOT / "ciciot2023" / "preprocessing.py",
        DATASETS_ROOT / "ciciot2023" / "validation.py",
    )
    existing = tuple(str(path.relative_to(SRC_ROOT)) for path in obsolete if path.exists())
    assert not existing, f"obsolete dataset modules still present: {existing}"
