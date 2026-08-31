from typer.testing import CliRunner

from fedsira.cli.main import app

runner = CliRunner()


def test_run_without_experiment_name_is_rejected() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0


def test_run_unknown_experiment_is_rejected() -> None:
    result = runner.invoke(app, ["run", "not-a-roadmap-experiment"])
    assert result.exit_code != 0


def test_run_post_core_experiment_is_blocked_without_resolved_core() -> None:
    result = runner.invoke(app, ["run", "Primary Confirmatory Evaluation"])
    assert result.exit_code != 0
    assert "Blocked" in result.stdout


def test_report_without_complete_evidence_exits_nonzero() -> None:
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 1
