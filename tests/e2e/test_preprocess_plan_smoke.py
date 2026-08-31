import pytest
from typer.testing import CliRunner

from fedsira.cli.commands import doctor
from fedsira.cli.main import app
from fedsira.runtime.environment import EnvironmentMismatch

runner = CliRunner()


def _no_mismatches(
    _workspace_path: object, _rar_archives_present: object
) -> tuple[EnvironmentMismatch, ...]:
    return ()


def test_plan_command_prints_roadmap_cell_counts() -> None:
    result = runner.invoke(app, ["plan"])
    assert result.exit_code == 0
    assert "total cells: 1989" in result.stdout
    assert "pre-core cells: 299" in result.stdout
    assert "post-core cells: 1690" in result.stdout


def test_smoke_command_passes_protocol_invariants() -> None:
    result = runner.invoke(app, ["smoke"])
    assert result.exit_code == 0
    assert "result: PASSED" in result.stdout


def test_doctor_command_reports_configuration_and_next_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "collect_environment_mismatches", _no_mismatches)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "configuration: valid" in result.stdout
    assert "next valid action:" in result.stdout
    assert "project stage:" in result.stdout
