from collections.abc import Iterator
from pathlib import Path

import pytest

from fedsira.runtime.state import ApplicationContext, bound_application_context

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def application_context() -> ApplicationContext:
    return ApplicationContext.load(REPOSITORY_ROOT)


@pytest.fixture(autouse=True)
def bind_application_context(application_context: ApplicationContext) -> Iterator[None]:
    with bound_application_context(application_context):
        yield
