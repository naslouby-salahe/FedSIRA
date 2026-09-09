from pathlib import Path

from fedsira.domain.enums import FailureClass
from fedsira.runtime.state import (
    ApplicationContext,
    bound_application_context,
    current_application_context,
    is_automatically_retriable,
)


def test_only_infrastructure_interruption_is_automatically_retriable() -> None:
    assert is_automatically_retriable(FailureClass.INFRASTRUCTURE_INTERRUPTION)
    assert not is_automatically_retriable(FailureClass.DATA_INVALID)


def test_bound_application_context_is_retrievable(application_context: ApplicationContext) -> None:
    assert current_application_context() is application_context
    nested = ApplicationContext.load(application_context.repository_root)
    with bound_application_context(nested):
        assert current_application_context() is nested
    assert current_application_context() is application_context
    assert application_context.repository_root == Path(__file__).resolve().parents[3]
