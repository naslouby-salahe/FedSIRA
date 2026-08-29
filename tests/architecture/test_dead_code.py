import subprocess
import sys
from pathlib import Path

from _repo import REPO_ROOT, SRC_ROOT


def run_vulture(*targets: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "vulture", *[str(target) for target in targets]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_no_dead_code_in_src() -> None:
    result = run_vulture(SRC_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_violation_detected_for_unused_function(tmp_path: Path) -> None:
    package = tmp_path / "dead_code_fixture"
    package.mkdir()
    (package / "module.py").write_text(
        "def used() -> int:\n"
        "    return 1\n\n"
        "def never_called_anywhere_in_this_fixture() -> int:\n"
        "    return 2\n\n"
        "print(used())\n"
    )
    result = run_vulture(package)
    assert result.returncode != 0
    assert "never_called_anywhere_in_this_fixture" in result.stdout
