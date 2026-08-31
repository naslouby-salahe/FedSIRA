from fedsira.cli.commands import REPOSITORY_ROOT
from fedsira.domain.records import OverwriteExisting
from fedsira.experiments.validation import render_smoke, run_smoke_suite
from fedsira.runtime.environment import configure_deterministic_backend
from fedsira.runtime.state import ApplicationContext, bound_application_context


def execute(overwrite: OverwriteExisting) -> None:
    context = ApplicationContext.load(REPOSITORY_ROOT)
    with bound_application_context(context):
        configure_deterministic_backend()
        result = run_smoke_suite(overwrite=overwrite)
    print(render_smoke(result))
    if not result.passed:
        raise SystemExit(1)
