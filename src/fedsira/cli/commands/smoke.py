from fedsira.experiments.validation import render_smoke, run_smoke_suite


def execute(overwrite: bool) -> None:
    result = run_smoke_suite(overwrite=overwrite)
    print(render_smoke(result))
    if not result.passed:
        raise SystemExit(1)
