from pathlib import Path

from _repo import SRC_ROOT

JUSTIFIED_LINE_BUDGETS = {
    "config.py": 900,
    "domain/types.py": 500,
    "experiments/definitions.py": 700,
    "experiments/validation.py": 800,
    "experiments/collapse.py": 700,
    "experiments/cells.py": 1700,
    "experiments/cell_support.py": 900,
    "evaluation/comparisons.py": 1200,
    "evaluation/metrics.py": 700,
    "reporting/tables.py": 1600,
    "reporting/figures.py": 900,
    "reporting/export.py": 900,
    "datasets/ciciot2023/preprocessing.py": 1400,
    "application.py": 700,
    "protocol/baselines/outcomes.py": 700,
}

DEFAULT_LINE_BUDGET = 600
DEFAULT_BYTE_BUDGET = 40_000
JUSTIFIED_BYTE_BUDGETS = {
    "experiments/cells.py": 80_000,
    "reporting/tables.py": 55_000,
    "datasets/ciciot2023/preprocessing.py": 50_000,
    "evaluation/comparisons.py": 45_000,
}


def _relative(path: Path) -> str:
    return path.relative_to(SRC_ROOT).as_posix()


def test_production_modules_stay_within_justified_size_budgets() -> None:
    line_offenders: list[str] = []
    byte_offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = _relative(path)
        line_budget = JUSTIFIED_LINE_BUDGETS.get(relative, DEFAULT_LINE_BUDGET)
        byte_budget = JUSTIFIED_BYTE_BUDGETS.get(relative, DEFAULT_BYTE_BUDGET)
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        byte_count = path.stat().st_size
        if line_count > line_budget:
            line_offenders.append(f"{relative}: {line_count} lines > {line_budget}")
        if byte_count > byte_budget:
            byte_offenders.append(f"{relative}: {byte_count} bytes > {byte_budget}")
    assert not line_offenders, "module line budgets exceeded: " + "; ".join(line_offenders)
    assert not byte_offenders, "module byte budgets exceeded: " + "; ".join(byte_offenders)


def test_no_runner_module_exists() -> None:
    runners = [path for path in SRC_ROOT.rglob("*runner*.py") if "__pycache__" not in path.parts]
    assert not runners, f"runner modules must not exist: {runners}"
