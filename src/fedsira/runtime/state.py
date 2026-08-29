from fedsira.domain.enums import (
    CellPhaseState,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
)
from fedsira.domain.records import FailureMessage, FrozenDomainModel

CELL_PHASE_TRANSITIONS: dict[CellPhaseState, frozenset[CellPhaseState]] = {
    CellPhaseState.PLANNED: frozenset({CellPhaseState.RUNNING}),
    CellPhaseState.RUNNING: frozenset({CellPhaseState.COMPLETED, CellPhaseState.FAILED}),
    CellPhaseState.FAILED: frozenset({CellPhaseState.RUNNING, CellPhaseState.INVALID}),
    CellPhaseState.COMPLETED: frozenset(),
    CellPhaseState.INVALID: frozenset(),
}

EXPERIMENT_LIFECYCLE_TRANSITIONS: dict[
    ExperimentLifecycleState, frozenset[ExperimentLifecycleState]
] = {
    ExperimentLifecycleState.NOT_STARTED: frozenset(
        {ExperimentLifecycleState.BLOCKED, ExperimentLifecycleState.READY}
    ),
    ExperimentLifecycleState.BLOCKED: frozenset({ExperimentLifecycleState.READY}),
    ExperimentLifecycleState.READY: frozenset({ExperimentLifecycleState.RUNNING}),
    ExperimentLifecycleState.RUNNING: frozenset(
        {ExperimentLifecycleState.COMPLETED, ExperimentLifecycleState.FAILED}
    ),
    ExperimentLifecycleState.FAILED: frozenset(
        {ExperimentLifecycleState.RUNNING, ExperimentLifecycleState.INVALID}
    ),
    ExperimentLifecycleState.COMPLETED: frozenset(),
    ExperimentLifecycleState.INVALID: frozenset(),
}

AUTOMATICALLY_RETRIABLE_FAILURE_CLASSES = frozenset(
    {FailureClass.INFRASTRUCTURE_INTERRUPTION}
)


class FailureDetail(FrozenDomainModel):
    failure_class: FailureClass
    message: FailureMessage
    cell_phase: ScientificCellPhase | None


def validate_cell_phase_transition(
    current: CellPhaseState,
    target: CellPhaseState,
) -> None:
    if target not in CELL_PHASE_TRANSITIONS[current]:
        raise ValueError(
            f"illegal cell phase transition from {current.value} to {target.value}"
        )


def validate_experiment_lifecycle_transition(
    current: ExperimentLifecycleState,
    target: ExperimentLifecycleState,
) -> None:
    if target not in EXPERIMENT_LIFECYCLE_TRANSITIONS[current]:
        raise ValueError(
            f"illegal experiment lifecycle transition from {current.value} to {target.value}"
        )


def is_automatically_retriable(failure_class: FailureClass) -> bool:
    return failure_class in AUTOMATICALLY_RETRIABLE_FAILURE_CLASSES
