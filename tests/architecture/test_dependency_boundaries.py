import subprocess
import sys
import textwrap
from pathlib import Path

from _repo import REPO_ROOT

FORBIDDEN_EDGES = {
    "fedsira.domain": {
        "fedsira.cli",
        "fedsira.reporting",
        "fedsira.runtime",
        "fedsira.artifacts",
        "fedsira.experiments",
        "fedsira.config",
    },
    "fedsira.config": {
        "fedsira.cli",
        "fedsira.reporting",
        "fedsira.runtime",
        "fedsira.artifacts",
        "fedsira.experiments",
    },
    "fedsira.cli": {
        "fedsira.learning",
        "fedsira.protocol",
        "fedsira.analysis",
    },
}


def lint_imports_executable() -> str:
    return str(Path(sys.executable).parent / "lint-imports")


def test_import_linter_contracts_pass() -> None:
    result = subprocess.run(
        [lint_imports_executable(), "--config", "pyproject.toml"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_forbidden_edges_are_declared_in_pyproject() -> None:
    contracts_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for lower, uppers in FORBIDDEN_EDGES.items():
        assert lower in contracts_text
        for upper in uppers:
            assert upper in contracts_text


def test_import_linter_detects_injected_violation(tmp_path: Path) -> None:
    package_root = tmp_path / "violating_project"
    src = package_root / "src" / "violating"
    (src / "lower").mkdir(parents=True)
    (src / "upper").mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "lower" / "__init__.py").write_text("import violating.upper\n")
    (src / "upper" / "__init__.py").write_text("")
    pyproject = package_root / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """
            [tool.importlinter]
            root_package = "violating"

            [[tool.importlinter.contracts]]
            name = "lower must not import upper"
            type = "forbidden"
            source_modules = ["violating.lower"]
            forbidden_modules = ["violating.upper"]
            """
        )
    )
    result = subprocess.run(
        [lint_imports_executable(), "--config", str(pyproject)],
        cwd=package_root,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(package_root / "src")},
    )
    assert result.returncode != 0
