import ast
import re
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, TESTS_ROOT, iter_python_files, parse


def public_top_level_symbols(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef) and not node.name.startswith("_"):
            names.append(node.name)
    return names


def occurrence_count(text: str, symbol: str) -> int:
    return len(re.findall(rf"\b{re.escape(symbol)}\b", text))


def referenced_in(root: Path, symbol: str, defining_file: Path) -> bool:
    for path in iter_python_files(root):
        text = path.read_text(encoding="utf-8")
        minimum_required = 2 if path == defining_file else 1
        if occurrence_count(text, symbol) >= minimum_required:
            return True
    return False


def test_no_public_production_symbol_used_only_by_tests() -> None:
    offenders: list[str] = []
    for path in iter_python_files(SRC_ROOT):
        if path.name == "__init__.py":
            continue
        for symbol in public_top_level_symbols(parse(path)):
            used_in_src = referenced_in(SRC_ROOT, symbol, path)
            used_in_tests = referenced_in(TESTS_ROOT, symbol, path)
            if used_in_tests and not used_in_src:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{symbol}")
    assert not offenders, f"Production symbols referenced only from tests: {offenders}"


def test_violation_detected_for_test_only_symbol(tmp_path: Path) -> None:
    src_root = tmp_path / "src"
    tests_root = tmp_path / "tests"
    src_root.mkdir()
    tests_root.mkdir()
    producer = src_root / "producer.py"
    producer.write_text("def only_used_by_tests() -> int:\n    return 1\n")
    consumer = tests_root / "test_producer.py"
    consumer.write_text("from producer import only_used_by_tests\n")
    used_in_src = referenced_in(src_root, "only_used_by_tests", producer)
    used_in_tests = referenced_in(tests_root, "only_used_by_tests", producer)
    assert used_in_tests and not used_in_src


def test_symbol_used_elsewhere_in_its_own_file_counts_as_used(tmp_path: Path) -> None:
    src_root = tmp_path / "self_reference_src"
    src_root.mkdir()
    producer = src_root / "producer.py"
    producer.write_text("class Inner:\n    pass\n\nclass Outer:\n    field: Inner\n")
    assert referenced_in(src_root, "Inner", producer)
