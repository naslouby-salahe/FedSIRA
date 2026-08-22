import ast
from pathlib import Path
from typing import Union

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "fedsira"
TESTS_ROOT = REPO_ROOT / "tests"
CONFIG_PATH = REPO_ROOT / "configs" / "fedsira.yaml"
COMMON_LITERALS = {0, 1, -1, 2, 3, 4, 8, 100.0, 0.1, 1e-05, 256, 0.25, 0.75, 10.0}

YamlValue = Union[None, bool, int, float, str, "list[YamlValue]", "dict[str, YamlValue]"]


def iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def module_name(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT / "src")
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def find_all_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def flatten_governed_values(node: YamlValue) -> set[float]:
    values: set[float] = set()
    if isinstance(node, dict):
        for value in node.values():
            values |= flatten_governed_values(value)
    elif isinstance(node, list):
        for item in node:
            values |= flatten_governed_values(item)
    elif isinstance(node, bool):
        return values
    elif isinstance(node, int | float):
        values.add(float(node))
    return values


def governed_values() -> set[float]:
    if not CONFIG_PATH.exists():
        return set()
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        parsed: YamlValue = yaml.safe_load(handle)
    return flatten_governed_values(parsed) - COMMON_LITERALS
