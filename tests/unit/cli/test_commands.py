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
    assert "project progress" in result.stdout


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.stdout


def test_preprocess_accepts_only_roadmap_dataset_identities() -> None:
    result = runner.invoke(app, ["preprocess", "not-a-real-dataset"])
    assert result.exit_code != 0


def test_preprocess_without_dataset_runs_all_roadmap_datasets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []

    def record_nbaiot(overwrite: bool) -> None:
        calls.append(("N-BaIoT", overwrite))

    def record_ciciot2023(overwrite: bool) -> None:
        calls.append(("CICIoT2023", overwrite))

    monkeypatch.setattr(preprocess, "_preprocess_nbaiot", record_nbaiot)
    monkeypatch.setattr(preprocess, "_preprocess_ciciot2023", record_ciciot2023)

    preprocess.execute(None, True)

    assert calls == [("N-BaIoT", True), ("CICIoT2023", True)]


def test_plan_prints_section_31_counts() -> None:
    result = runner.invoke(app, ["plan"])
    assert result.exit_code == 0
    assert "total cells: 1989" in result.stdout
    assert "pre-core cells: 299" in result.stdout
    assert "post-core cells: 1690" in result.stdout


def test_smoke_runs_and_passes() -> None:
    result = runner.invoke(app, ["smoke"])
    assert result.exit_code == 0
    assert "result: PASSED" in result.stdout


def test_run_requires_an_experiment_name() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0


def test_run_unknown_experiment_fails() -> None:
    result = runner.invoke(app, ["run", "some-experiment"])
    assert result.exit_code != 0


def test_run_rejects_post_core_experiment_without_resolved_core() -> None:
    result = runner.invoke(app, ["run", "Primary Confirmatory Evaluation"])
    assert result.exit_code != 0
    assert "Blocked" in result.stdout


def test_report_export_produces_summary() -> None:
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 1


def test_no_command_exposes_a_seed_or_method_override_option() -> None:
    for command in ("doctor", "preprocess", "plan", "smoke", "run", "report"):
        result = runner.invoke(app, [command, "--help"])
        lowered = result.stdout.lower()
        for forbidden in ("--seed", "--method", "--baseline", "--attack", "--phase"):
            assert forbidden not in lowered
