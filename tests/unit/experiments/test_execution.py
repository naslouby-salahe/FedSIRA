from pathlib import Path

import pydantic
import pytest

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import (
    CellPhaseState,
    ExperimentLifecycleState,
    ScientificCellPhase,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    CellExecutor,
    ExecutionRecordStore,
    PersistedExecutionRecord,
    derive_lifecycle_state,
    execution_record_digest,
    is_terminal_experiment_state,
    run_experiment,
)
from fedsira.experiments.planning import ScientificCell
from fedsira.experiments.validation import (
    validate_cell_phase_sequence,
    validate_cell_terminal_record,
    validate_experiment_name_is_registered,
    validate_experiment_prerequisites_met,
    validate_no_duplicate_semantic_cells,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def _cell(experiment: str, method: str, condition: str, master_seed: int) -> ScientificCell:
    return ScientificCell(
        experiment=experiment,
        method=method,
        condition=condition,
        master_seed=master_seed,
    )


def _completed_outcome(cell: ScientificCell) -> CellExecutionOutcome:
    return CellExecutionOutcome(
        cell=cell,
        terminal_state=ExperimentLifecycleState.COMPLETED,
        failure=None,
        metrics=(("terminal-state", 1.0),),
    )


def test_derive_lifecycle_state_empty_is_not_started() -> None:
    assert derive_lifecycle_state(()) is ExperimentLifecycleState.NOT_STARTED


def test_derive_lifecycle_state_all_completed() -> None:
    states = (ExperimentLifecycleState.COMPLETED.value,) * 3
    assert derive_lifecycle_state(states) is ExperimentLifecycleState.COMPLETED


def test_derive_lifecycle_state_invalid_dominates() -> None:
    states = (
        ExperimentLifecycleState.COMPLETED.value,
        ExperimentLifecycleState.INVALID.value,
    )
    assert derive_lifecycle_state(states) is ExperimentLifecycleState.INVALID


def test_derive_lifecycle_state_failed_without_invalid() -> None:
    states = (
        ExperimentLifecycleState.COMPLETED.value,
        ExperimentLifecycleState.FAILED.value,
    )
    assert derive_lifecycle_state(states) is ExperimentLifecycleState.FAILED


def test_derive_lifecycle_state_running_when_partial() -> None:
    states = (
        ExperimentLifecycleState.COMPLETED.value,
        ExperimentLifecycleState.RUNNING.value,
    )
    assert derive_lifecycle_state(states) is ExperimentLifecycleState.RUNNING


def test_is_terminal_experiment_state_accepts_terminal_only() -> None:
    assert is_terminal_experiment_state(ExperimentLifecycleState.COMPLETED)
    assert is_terminal_experiment_state(ExperimentLifecycleState.FAILED)
    assert is_terminal_experiment_state(ExperimentLifecycleState.INVALID)
    assert not is_terminal_experiment_state(ExperimentLifecycleState.RUNNING)
    assert not is_terminal_experiment_state(ExperimentLifecycleState.BLOCKED)


def test_execution_record_digest_deterministic_and_sensitive() -> None:
    cell = _cell("Single-Reproduction Necessity", "Full FedSIRA", "All Honest", 1)
    first = execution_record_digest((_completed_outcome(cell),))
    second = execution_record_digest((_completed_outcome(cell),))
    assert first == second
    changed = CellExecutionOutcome(
        cell=cell,
        terminal_state=ExperimentLifecycleState.FAILED,
        failure=None,
        metrics=(),
    )
    assert execution_record_digest((changed,)) != first


def test_record_store_round_trip(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    cell = _cell("Single-Reproduction Necessity", "Full FedSIRA", "All Honest", 1)
    outcome = _completed_outcome(cell)
    store.write_outcome(outcome)
    restored = store.read_outcome(cell.experiment, cell.semantic_key)
    assert restored is not None
    assert isinstance(restored, PersistedExecutionRecord)
    assert restored.terminal_state == ExperimentLifecycleState.COMPLETED
    assert restored.semantic_key == cell.semantic_key
    all_outcomes = store.read_all_outcomes(cell.experiment)
    assert len(all_outcomes) == 1


def test_record_store_read_missing_returns_none(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    assert store.read_outcome("Missing-Experiment", "missing-key") is None
    assert store.read_all_outcomes("Missing-Experiment") == ()


def test_record_store_read_malformed_record_is_rejected(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    cell = _cell("Single-Reproduction Necessity", "Full FedSIRA", "All Honest", 1)
    store.write_outcome(_completed_outcome(cell))
    record_dir = tmp_path / "experiments" / cell.experiment / "evaluations" / "records"
    target = next(record_dir.glob("*.json"))
    target.write_text("{not valid json")
    with pytest.raises(pydantic.ValidationError):
        store.read_all_outcomes(cell.experiment)


def test_validate_experiment_name_is_registered_rejects_unknown() -> None:
    validate_experiment_name_is_registered("Single-Reproduction Necessity")
    with pytest.raises(KeyError):
        validate_experiment_name_is_registered("Not-A-Registered-Experiment")


def test_validate_experiment_prerequisites_met() -> None:
    validate_experiment_prerequisites_met(
        "Primary Confirmatory Evaluation",
        {"Proposal-Assisted Opening Necessity": ExperimentLifecycleState.COMPLETED},
    )
    with pytest.raises(ValueError):
        validate_experiment_prerequisites_met(
            "Primary Confirmatory Evaluation",
            {"Proposal-Assisted Opening Necessity": ExperimentLifecycleState.NOT_STARTED},
        )


def test_validate_no_duplicate_semantic_cells() -> None:
    from fedsira.experiments.planning import build_plan

    plan = build_plan()
    validate_no_duplicate_semantic_cells(plan)


def test_validate_cell_phase_sequence_rejects_duplicate_phase() -> None:
    validate_cell_phase_sequence(
        (
            ScientificCellPhase.PREPARE,
            ScientificCellPhase.PROTOCOL_EVALUATION,
            ScientificCellPhase.METRIC_AGGREGATION,
        )
    )
    with pytest.raises(ValueError):
        validate_cell_phase_sequence((ScientificCellPhase.PREPARE, ScientificCellPhase.PREPARE))


def test_validate_cell_terminal_record_accepts_terminal_states_only() -> None:
    cell = _cell("Single-Reproduction Necessity", "Full FedSIRA", "All Honest", 1)
    validate_cell_terminal_record(cell, CellPhaseState.COMPLETED)
    validate_cell_terminal_record(cell, CellPhaseState.FAILED)
    with pytest.raises(ValueError):
        validate_cell_terminal_record(cell, CellPhaseState.RUNNING)


def test_run_experiment_blocks_on_missing_prerequisite() -> None:
    class RecordingExecutor(CellExecutor):
        def execute_cell(self, cell: ScientificCell, config: object) -> CellExecutionOutcome:
            raise AssertionError("no cell may execute when a prerequisite is missing")

    result = run_experiment(
        "Primary Confirmatory Evaluation",
        RecordingExecutor(),
        config_path=PRODUCTION_CONFIG_PATH,
    )
    assert result.lifecycle_state is ExperimentLifecycleState.BLOCKED
    assert result.outcomes == ()


def _override_workspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def path_factory(*args: object) -> Path:
        return tmp_path

    monkeypatch.setattr("fedsira.experiments.execution.Path", path_factory)


def test_run_experiment_reuses_completed_records_without_reexecution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class CountingExecutor(CellExecutor):
        def __init__(self) -> None:
            self.executions = 0

        def execute_cell(self, cell: ScientificCell, config: object) -> CellExecutionOutcome:
            self.executions += 1
            return _completed_outcome(cell)

    _override_workspace_root(tmp_path, monkeypatch)
    executor = CountingExecutor()
    result = run_experiment(
        "Protocol Invariant Validation",
        executor,
        config_path=PRODUCTION_CONFIG_PATH,
    )
    first_executions = executor.executions
    assert first_executions > 0
    assert result.lifecycle_state is ExperimentLifecycleState.COMPLETED
    second = run_experiment(
        "Protocol Invariant Validation",
        executor,
        config_path=PRODUCTION_CONFIG_PATH,
    )
    assert executor.executions == first_executions
    assert second.lifecycle_state is ExperimentLifecycleState.COMPLETED


def test_run_experiment_unknown_name_rejected() -> None:
    class DummyExecutor(CellExecutor):
        def execute_cell(self, cell: ScientificCell, config: object) -> CellExecutionOutcome:
            raise AssertionError("must not execute")

    with pytest.raises(KeyError):
        run_experiment(
            "Not-A-Registered-Experiment",
            DummyExecutor(),
            config_path=PRODUCTION_CONFIG_PATH,
        )


def test_run_experiment_invalid_outcome_yields_invalid_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class InvalidExecutor(CellExecutor):
        def execute_cell(self, cell: ScientificCell, config: object) -> CellExecutionOutcome:
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.INVALID,
                failure=None,
                metrics=(),
            )

    _override_workspace_root(tmp_path, monkeypatch)
    result = run_experiment(
        "Protocol Invariant Validation",
        InvalidExecutor(),
        config_path=PRODUCTION_CONFIG_PATH,
    )
    assert result.lifecycle_state is ExperimentLifecycleState.INVALID


def test_run_experiment_failed_outcome_yields_failed_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailedExecutor(CellExecutor):
        def execute_cell(self, cell: ScientificCell, config: object) -> CellExecutionOutcome:
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.FAILED,
                failure=None,
                metrics=(),
            )

    _override_workspace_root(tmp_path, monkeypatch)
    result = run_experiment(
        "Protocol Invariant Validation",
        FailedExecutor(),
        config_path=PRODUCTION_CONFIG_PATH,
    )
    assert result.lifecycle_state is ExperimentLifecycleState.FAILED
