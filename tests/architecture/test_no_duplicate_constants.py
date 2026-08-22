import ast
import tempfile
from collections import defaultdict
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT, iter_python_files, parse


def module_constant_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    names.add(target.id)
    return names


def find_duplicate_constant_names(root: Path) -> dict[str, list[Path]]:
    owners: dict[str, list[Path]] = defaultdict(list)
    for path in iter_python_files(root):
        if path.name == "__init__.py":
            continue
        for name in module_constant_names(parse(path)):
            owners[name].append(path)
    return {name: paths for name, paths in owners.items() if len(paths) > 1}


def test_no_constant_name_defined_in_more_than_one_module() -> None:
    duplicates = find_duplicate_constant_names(SRC_ROOT)
    offenders = {
        name: [str(p.relative_to(REPO_ROOT)) for p in paths] for name, paths in duplicates.items()
    }
    assert not offenders, f"Constant names owned by more than one module: {offenders}"


def test_violation_detected_for_duplicate_constant_name() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.py").write_text("SHARED_LIMIT = 5\n")
        (root / "b.py").write_text("SHARED_LIMIT = 5\n")
        duplicates = find_duplicate_constant_names(root)
        assert "SHARED_LIMIT" in duplicates
