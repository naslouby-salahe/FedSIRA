import pytest

from fedsira.domain.enums import CellPhaseState, ExperimentLifecycleState, FailureClass
from fedsira.runtime.state import (
    is_automatically_retriable,
    validate_cell_phase_transition,
    validate_experiment_lifecycle_transition,
)


def test_planned_to_running_is_allowed() -> None:
    validate_cell_phase_transition(CellPhaseState.PLANNED, CellPhaseState.RUNNING)


def test_running_to_completed_is_allowed() -> None:
    validate_cell_phase_transition(CellPhaseState.RUNNING, CellPhaseState.COMPLETED)


def test_planned_to_completed_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_cell_phase_transition(CellPhaseState.PLANNED, CellPhaseState.COMPLETED)


def test_completed_is_terminal() -> None:
    with pytest.raises(ValueError):
        validate_cell_phase_transition(CellPhaseState.COMPLETED, CellPhaseState.RUNNING)


def test_failed_can_retry_to_running() -> None:
    validate_cell_phase_transition(CellPhaseState.FAILED, CellPhaseState.RUNNING)


def test_failed_can_become_invalid() -> None:
    validate_cell_phase_transition(CellPhaseState.FAILED, CellPhaseState.INVALID)


def test_not_started_to_ready_is_allowed() -> None:
    validate_experiment_lifecycle_transition(
        ExperimentLifecycleState.NOT_STARTED, ExperimentLifecycleState.READY
    )


def test_invalid_experiment_state_is_terminal() -> None:
    with pytest.raises(ValueError):
        validate_experiment_lifecycle_transition(
            ExperimentLifecycleState.INVALID, ExperimentLifecycleState.READY
        )


def test_only_infrastructure_interruption_is_automatically_retriable() -> None:
    assert is_automatically_retriable(FailureClass.INFRASTRUCTURE_INTERRUPTION)
    for failure_class in FailureClass:
        if failure_class is not FailureClass.INFRASTRUCTURE_INTERRUPTION:
            assert not is_automatically_retriable(failure_class)
