from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Self

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.config.schema import ScientificConfig
from fedsira.domain.enums import (
    CellPhaseState,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
)
from fedsira.domain.records import AutomaticallyRetriable, FailureMessage, FrozenDomainModel

CELL_PHASE_TRANSITIONS: tuple[tuple[CellPhaseState, frozenset[CellPhaseState]], ...] = (
    (CellPhaseState.PLANNED, frozenset({CellPhaseState.RUNNING})),
    (CellPhaseState.RUNNING, frozenset({CellPhaseState.COMPLETED, CellPhaseState.FAILED})),
    (CellPhaseState.FAILED, frozenset({CellPhaseState.RUNNING, CellPhaseState.INVALID})),
    (CellPhaseState.COMPLETED, frozenset()),
    (CellPhaseState.INVALID, frozenset()),
)

EXPERIMENT_LIFECYCLE_TRANSITIONS: tuple[
    tuple[ExperimentLifecycleState, frozenset[ExperimentLifecycleState]], ...
] = (
    (
        ExperimentLifecycleState.NOT_STARTED,
        frozenset({ExperimentLifecycleState.BLOCKED, ExperimentLifecycleState.READY}),
    ),
    (
        ExperimentLifecycleState.BLOCKED,
        frozenset({ExperimentLifecycleState.READY}),
    ),
    (
        ExperimentLifecycleState.READY,
        frozenset({ExperimentLifecycleState.RUNNING}),
    ),
    (
        ExperimentLifecycleState.RUNNING,
        frozenset({ExperimentLifecycleState.COMPLETED, ExperimentLifecycleState.FAILED}),
    ),
    (
        ExperimentLifecycleState.FAILED,
        frozenset({ExperimentLifecycleState.RUNNING, ExperimentLifecycleState.INVALID}),
    ),
    (ExperimentLifecycleState.COMPLETED, frozenset()),
    (ExperimentLifecycleState.INVALID, frozenset()),
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


def _allowed_cell_phase_targets(current: CellPhaseState) -> frozenset[CellPhaseState]:
    for state, allowed_targets in CELL_PHASE_TRANSITIONS:
        if state is current:
            return allowed_targets
    raise ValueError(f"unknown cell phase state: {current.value}")


def _allowed_experiment_lifecycle_targets(
    current: ExperimentLifecycleState,
) -> frozenset[ExperimentLifecycleState]:
    for state, allowed_targets in EXPERIMENT_LIFECYCLE_TRANSITIONS:
        if state is current:
            return allowed_targets
    raise ValueError(f"unknown experiment lifecycle state: {current.value}")


def validate_cell_phase_transition(
    current: CellPhaseState,
    target: CellPhaseState,
) -> None:
    if target not in _allowed_cell_phase_targets(current):
        raise ValueError(f"illegal cell phase transition from {current.value} to {target.value}")


def validate_experiment_lifecycle_transition(
    current: ExperimentLifecycleState,
    target: ExperimentLifecycleState,
) -> None:
    if target not in _allowed_experiment_lifecycle_targets(current):
        raise ValueError(
            f"illegal experiment lifecycle transition from {current.value} to {target.value}"
        )


def is_automatically_retriable(failure_class: FailureClass) -> AutomaticallyRetriable:
    return failure_class in AUTOMATICALLY_RETRIABLE_FAILURE_CLASSES
