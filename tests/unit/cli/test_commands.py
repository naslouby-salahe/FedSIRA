import pytest
from typer.testing import CliRunner

from fedsira.cli.commands import doctor, preprocess
from fedsira.cli.main import app
from fedsira.runtime.environment import EnvironmentMismatch

runner = CliRunner()

REAL_NBAIOT_ROOT = preprocess.REPOSITORY_ROOT / "data" / "raw" / "N-BaIoT"


def _no_mismatches(
    _workspace_path: object, _rar_archives_present: object
) -> tuple[EnvironmentMismatch, ...]:
    return ()


def test_doctor_exits_zero_when_environment_and_config_are_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "collect_environment_mismatches", _no_mismatches)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "project stage" in result.stdout


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.stdout


def test_preprocess_accepts_only_roadmap_dataset_identities() -> None:
    result = runner.invoke(app, ["preprocess", "not-a-real-dataset"])
    assert result.exit_code != 0


@pytest.mark.skipif(not REAL_NBAIOT_ROOT.is_dir(), reason="real N-BaIoT raw data not available")
def test_preprocess_routes_and_reports_not_yet_implemented() -> None:
    result = runner.invoke(app, ["preprocess", "N-BaIoT"])
    assert result.exit_code == 1
    assert "not yet implemented" in result.stdout
    assert "dataset_file_manifest_hash=" in result.stdout


def test_plan_routes_and_reports_not_yet_implemented() -> None:
    result = runner.invoke(app, ["plan"])
    assert result.exit_code == 1


def test_smoke_routes_and_reports_not_yet_implemented() -> None:
    result = runner.invoke(app, ["smoke"])
    assert result.exit_code == 1


def test_run_requires_an_experiment_name() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0


def test_run_routes_and_reports_not_yet_implemented() -> None:
    result = runner.invoke(app, ["run", "some-experiment"])
    assert result.exit_code == 1


def test_report_routes_and_reports_not_yet_implemented() -> None:
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 1


def test_no_command_exposes_a_seed_or_method_override_option() -> None:
    for command in ("doctor", "preprocess", "plan", "smoke", "run", "report"):
        result = runner.invoke(app, [command, "--help"])
        lowered = result.stdout.lower()
        for forbidden in ("--seed", "--method", "--baseline", "--attack", "--phase"):
            assert forbidden not in lowered
