from fedsira.domain.enums import (
    CellPhaseState,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
)
from fedsira.domain.records import BooleanValue, FailureMessage, FrozenDomainModel

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


def is_automatically_retriable(failure_class: FailureClass) -> BooleanValue:
    return failure_class in AUTOMATICALLY_RETRIABLE_FAILURE_CLASSES
