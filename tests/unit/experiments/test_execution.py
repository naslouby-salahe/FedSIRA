from pathlib import Path

import pydantic
import pytest

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.config.schema import ScientificConfig
from fedsira.domain.enums import ExperimentLifecycleState, ScientificCellPhase
from fedsira.experiments.execution import (
    TERMINAL_EXPERIMENT_STATES,
    CellExecutionOutcome,
    ExecutionRecordStore,
    PersistedExecutionRecord,
    derive_experiment_lifecycle,
    execute_experiment,
)
from fedsira.experiments.planning import ScientificCell, build_plan
from fedsira.experiments.validation import (
    ExperimentPrerequisiteState,
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


def _override_workspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def path_factory(_value: str) -> Path:
        return tmp_path

    monkeypatch.setattr("fedsira.experiments.execution.Path", path_factory)


def test_terminal_experiment_states_are_exact() -> None:
    assert TERMINAL_EXPERIMENT_STATES == frozenset(
        (
            ExperimentLifecycleState.COMPLETED,
            ExperimentLifecycleState.FAILED,
            ExperimentLifecycleState.INVALID,
        )
    )


def test_derive_experiment_lifecycle_empty_ready_experiment_is_ready() -> None:
    plan = build_plan(resolved_core_complete=False)
    planned = plan.experiment("Protocol Invariant Validation")
    assert derive_experiment_lifecycle(planned, ()) is ExperimentLifecycleState.READY


def test_derive_experiment_lifecycle_empty_post_core_experiment_is_blocked() -> None:
    plan = build_plan(resolved_core_complete=False)
    planned = plan.experiment("Primary Confirmatory Evaluation")
    assert derive_experiment_lifecycle(planned, ()) is ExperimentLifecycleState.BLOCKED


def test_record_store_round_trip(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    cell = _cell("Single-Reproduction Necessity", "Full FedSIRA", "All Honest", 1)
    outcome = _completed_outcome(cell)
    store.write_outcome(outcome)
    restored = store.read_outcome(cell.experiment, cell.semantic_key)
    assert restored is not None
    assert isinstance(restored, PersistedExecutionRecord)
    assert restored.terminal_state is ExperimentLifecycleState.COMPLETED
    assert restored.semantic_key == cell.semantic_key
    assert len(store.read_all_outcomes(cell.experiment)) == 1


def test_record_store_read_missing_returns_none(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    assert store.read_outcome("Missing-Experiment", "missing-key") is None
    assert store.read_all_outcomes("Missing-Experiment") == ()


def test_record_store_read_malformed_record_is_rejected(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    cell = _cell("Single-Reproduction Necessity", "Full FedSIRA", "All Honest", 1)
    store.write_outcome(_completed_outcome(cell))
    record_dir = tmp_path / "experiments" / cell.experiment / "evaluations" / "records"
    next(record_dir.glob("*.json")).write_text("{not valid json")
    with pytest.raises(pydantic.ValidationError):
        store.read_all_outcomes(cell.experiment)


def test_validate_experiment_name_is_registered_rejects_unknown() -> None:
    validate_experiment_name_is_registered("Single-Reproduction Necessity")
    with pytest.raises(KeyError):
        validate_experiment_name_is_registered("Not-A-Registered-Experiment")


def test_validate_experiment_prerequisites_requires_completed_state() -> None:
    completed = (
        ExperimentPrerequisiteState(
            experiment="Proposal-Assisted Opening Necessity",
            lifecycle_state=ExperimentLifecycleState.COMPLETED,
        ),
    )
    validate_experiment_prerequisites_met("Primary Confirmatory Evaluation", completed)
    incomplete = (
        ExperimentPrerequisiteState(
            experiment="Proposal-Assisted Opening Necessity",
            lifecycle_state=ExperimentLifecycleState.NOT_STARTED,
        ),
    )
    with pytest.raises(ValueError):
        validate_experiment_prerequisites_met("Primary Confirmatory Evaluation", incomplete)


def test_validate_no_duplicate_semantic_cells() -> None:
    validate_no_duplicate_semantic_cells(build_plan())


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
    validate_cell_terminal_record(cell, ExperimentLifecycleState.COMPLETED)
    validate_cell_terminal_record(cell, ExperimentLifecycleState.FAILED)
    with pytest.raises(ValueError):
        validate_cell_terminal_record(cell, ExperimentLifecycleState.RUNNING)


def test_execute_experiment_rejects_missing_prerequisite() -> None:
    class NeverExecutor:
        def execute_cell(
            self,
            cell: ScientificCell,
            config: ScientificConfig,
        ) -> CellExecutionOutcome:
            raise AssertionError(f"unexpected execution of {cell.semantic_key}")

    incomplete = (
        ExperimentPrerequisiteState(
            experiment="Data and Domain Evidence Validation",
            lifecycle_state=ExperimentLifecycleState.NOT_STARTED,
        ),
    )
    with pytest.raises(ValueError, match="requires prerequisite"):
        execute_experiment(
            "Proposal-Assisted Opening Necessity",
            NeverExecutor(),
            config=CONFIG,
            prerequisite_states=incomplete,
        )


def test_execute_experiment_reuses_completed_records_without_reexecution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CountingExecutor:
        def __init__(self) -> None:
            self.executions = 0

        def execute_cell(
            self,
            cell: ScientificCell,
            config: ScientificConfig,
        ) -> CellExecutionOutcome:
            del config
            self.executions += 1
            return _completed_outcome(cell)

    _override_workspace_root(tmp_path, monkeypatch)
    executor = CountingExecutor()
    result = execute_experiment("Protocol Invariant Validation", executor, config=CONFIG)
    assert executor.executions == 1
    assert result.lifecycle_state is ExperimentLifecycleState.COMPLETED
    second = execute_experiment("Protocol Invariant Validation", executor, config=CONFIG)
    assert executor.executions == 1
    assert second.lifecycle_state is ExperimentLifecycleState.COMPLETED


def test_execute_experiment_unknown_name_rejected() -> None:
    class NeverExecutor:
        def execute_cell(
            self,
            cell: ScientificCell,
            config: ScientificConfig,
        ) -> CellExecutionOutcome:
            raise AssertionError(f"unexpected execution of {cell.semantic_key}: {config}")

    with pytest.raises(KeyError):
        execute_experiment("Not-A-Registered-Experiment", NeverExecutor(), config=CONFIG)


def test_execute_experiment_invalid_outcome_yields_invalid_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InvalidExecutor:
        def execute_cell(
            self,
            cell: ScientificCell,
            config: ScientificConfig,
        ) -> CellExecutionOutcome:
            del config
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.INVALID,
                failure=None,
                metrics=(),
            )

    _override_workspace_root(tmp_path, monkeypatch)
    result = execute_experiment("Protocol Invariant Validation", InvalidExecutor(), config=CONFIG)
    assert result.lifecycle_state is ExperimentLifecycleState.INVALID


def test_execute_experiment_failed_outcome_yields_failed_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedExecutor:
        def execute_cell(
            self,
            cell: ScientificCell,
            config: ScientificConfig,
        ) -> CellExecutionOutcome:
            del config
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.FAILED,
                failure=None,
                metrics=(),
            )

    _override_workspace_root(tmp_path, monkeypatch)
    result = execute_experiment("Protocol Invariant Validation", FailedExecutor(), config=CONFIG)
    assert result.lifecycle_state is ExperimentLifecycleState.FAILED
