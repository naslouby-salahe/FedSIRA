from pathlib import Path

import pytest

from fedsira.experiments.smoke import (
    SMOKE_RECORD_SCHEMA_VERSION,
    SmokeSuiteResult,
    render_smoke,
    run_smoke_suite,
)


def test_smoke_suite_passes_on_production_config() -> None:
    result = run_smoke_suite(overwrite=False)
    assert isinstance(result, SmokeSuiteResult)
    assert result.passed
    assert result.checks


def test_smoke_suite_check_names_are_populated() -> None:
    result = run_smoke_suite()
    assert all(check.name for check in result.checks)
    assert all(not check.name.isspace() for check in result.checks)


def test_render_smoke_lists_checks() -> None:
    result = run_smoke_suite()
    rendered = render_smoke(result)
    assert "FedSIRA smoke suite" in rendered
    for check in result.checks:
        assert check.name in rendered


def test_run_smoke_suite_writes_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    record_path = tmp_path / "smoke_record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("fedsira.experiments.smoke.smoke_record_path", lambda: record_path)
    result = run_smoke_suite(overwrite=True)
    assert record_path.exists()
    import json

    payload = json.loads(record_path.read_text())
    assert payload["schema_version"] == SMOKE_RECORD_SCHEMA_VERSION
    assert payload["passed"] is result.passed
    assert len(payload["checks"]) == len(result.checks)


def test_run_smoke_suite_respects_no_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_path = tmp_path / "smoke_record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text("sentinel")
    monkeypatch.setattr("fedsira.experiments.smoke.smoke_record_path", lambda: record_path)
    run_smoke_suite(overwrite=False)
    assert record_path.read_text() == "sentinel"
