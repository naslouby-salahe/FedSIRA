import json
import subprocess
import sys
from pathlib import Path

from _repo import REPO_ROOT


def run_deptry() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "deptry", "src", "-o", "deptry-report.json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_deptry_reports_no_dependency_issues() -> None:
    result = run_deptry()
    report_path = REPO_ROOT / "deptry-report.json"
    issues: list[object] = []
    if report_path.exists():
        issues = json.loads(report_path.read_text(encoding="utf-8"))
        report_path.unlink()
    assert result.returncode == 0 and not issues, result.stdout + result.stderr


def test_violation_detected_for_unused_dependency(tmp_path: Path) -> None:
    project = tmp_path / "unused_dependency_fixture"
    src = project / "src" / "fixture"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (project / "pyproject.toml").write_text(
        "[project]\n"
        'name = "fixture"\n'
        'version = "0.1.0"\n'
        'dependencies = ["requests"]\n'
        "[build-system]\n"
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
    )
    result = subprocess.run(
        [sys.executable, "-m", "deptry", "src"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
