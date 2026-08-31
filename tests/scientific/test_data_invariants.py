from fedsira.experiments.validation import run_smoke_suite


def test_smoke_suite_includes_passing_data_invariants() -> None:
    result = run_smoke_suite()
    names = tuple(check.name for check in result.checks)
    assert any("role" in name.lower() or "interval" in name.lower() for name in names)
    assert result.passed
