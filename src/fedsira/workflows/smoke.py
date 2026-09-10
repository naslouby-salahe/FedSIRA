from fedsira.domain.types import OverwriteExisting
from fedsira.experiments.validation import render_smoke, run_smoke_suite
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ApplicationContext,
    bound_application_context,
    configure_deterministic_backend,
)


def execute(overwrite: OverwriteExisting) -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        configure_deterministic_backend()
        result = run_smoke_suite(overwrite=overwrite)
    print(render_smoke(result))
    if not result.passed:
        raise SystemExit(1)
