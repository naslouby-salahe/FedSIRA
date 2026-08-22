import subprocess
import sys
import tempfile
from pathlib import Path

from _repo import REPO_ROOT


def test_ruff_format_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_ruff_lint_passes() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_violation_detected_for_unformatted_code() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        offending = Path(tmp) / "offending.py"
        offending.write_text("def f(  a:int,b:int )->int:\n    return a+b\n")
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", str(offending)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
