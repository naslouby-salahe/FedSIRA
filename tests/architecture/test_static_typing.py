import subprocess
import sys
import tempfile
from pathlib import Path

from _repo import REPO_ROOT


def run_pyright(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pyright"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_strict_pyright_passes_across_src_and_tests() -> None:
    result = run_pyright(REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_violation_detected_for_typing_error() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pyrightconfig.json").write_text(
            '{"typeCheckingMode": "strict", "include": ["offending.py"]}\n'
        )
        (root / "offending.py").write_text(
            "def add(a: int, b: int) -> int:\n    return a + b\n\nadd('x', 1)\n"
        )
        result = run_pyright(root)
        assert result.returncode != 0
