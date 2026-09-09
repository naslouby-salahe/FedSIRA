from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Self

from fedsira.config import PRODUCTION_CONFIG_PATH, ScientificConfig, load_scientific_config
from fedsira.domain.enums import (
    FailureClass,
    ScientificCellPhase,
)
from fedsira.domain.types import (
    AutomaticallyRetriable,
    AutomaticRecoveryPermitted,
    FailureMessage,
    FrozenDomainModel,
    RetryCount,
)

AUTOMATICALLY_RETRIABLE_FAILURE_CLASSES = frozenset({FailureClass.INFRASTRUCTURE_INTERRUPTION})


class FailureDetail(FrozenDomainModel):
    failure_class: FailureClass
    message: FailureMessage
    cell_phase: ScientificCellPhase | None


class ApplicationContext(FrozenDomainModel):
    scientific_config: ScientificConfig
    repository_root: Path

    @classmethod
    def load(cls: type[Self], repository_root: Path, config_path: Path | None = None) -> Self:
        resolved_path = (
            config_path if config_path is not None else repository_root / PRODUCTION_CONFIG_PATH
        )
        return cls(
            scientific_config=load_scientific_config(resolved_path),
            repository_root=repository_root,
        )


_APPLICATION_CONTEXT: ContextVar[ApplicationContext | None] = ContextVar(
    "fedsira_application_context",
    default=None,
)


@contextmanager
def bound_application_context(context: ApplicationContext) -> Iterator[ApplicationContext]:
    token = _APPLICATION_CONTEXT.set(context)
    try:
        yield context
    finally:
        _APPLICATION_CONTEXT.reset(token)


def current_application_context() -> ApplicationContext:
    context = _APPLICATION_CONTEXT.get()
    if context is None:
        raise RuntimeError("application context is not bound")
    return context


def is_automatically_retriable(failure_class: FailureClass) -> AutomaticallyRetriable:
    return failure_class in AUTOMATICALLY_RETRIABLE_FAILURE_CLASSES


def automatic_recovery_permitted(
    failure_class: FailureClass,
    attempts_used: RetryCount,
    automatic_infrastructure_retries_per_cell_phase: RetryCount,
) -> AutomaticRecoveryPermitted:
    if not is_automatically_retriable(failure_class):
        return False
    return attempts_used < automatic_infrastructure_retries_per_cell_phase
