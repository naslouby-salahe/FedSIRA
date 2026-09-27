from pathlib import Path
from typing import cast

import pydantic
import pytest

from fedsira.domain.enums import (
    DatasetId,
    ExperimentLifecycleState,
    ExperimentName,
    FailureClass,
    ScientificCellPhase,
    SourceExclusionMethod,
)
from fedsira.domain.models import (
    ScientificCell,
)
from fedsira.domain.types import ConditionName, MasterSeed, MethodName
from fedsira.experiments.definitions import experiment_registry
from fedsira.experiments.engine import (
    EXECUTION_RECORD_SCHEMA_VERSION,
    TERMINAL_EXPERIMENT_STATES,
    CellExecutionOutcome,
    CellExecutor,
    ExecutionLogFields,
    ExecutionProvenance,
    ExecutionRecordStore,
    PersistedExecutionRecord,
    derive_current_experiment_lifecycle,
    derive_experiment_lifecycle,
    execute_cell_with_retry,
)
from fedsira.experiments.execution import (
    ExperimentPrerequisiteState,
    execute_experiment,
    validate_cell_phase_sequence,
    validate_cell_terminal_record,
    validate_experiment_prerequisites_met,
    validate_no_duplicate_semantic_cells,
)
from fedsira.experiments.planning import (
    build_plan,
)
from fedsira.runtime import FailureDetail


def _cell(
    experiment: ExperimentName,
    method: MethodName,
    condition: ConditionName,
    master_seed: MasterSeed,
) -> ScientificCell:
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
    def workspace_factory() -> Path:
        return tmp_path

    monkeypatch.setattr("fedsira.experiments.execution.execution_workspace_root", workspace_factory)


def test_terminal_experiment_states_are_exact() -> None:
    assert (
        frozenset(
            (
                ExperimentLifecycleState.COMPLETED,
                ExperimentLifecycleState.FAILED,
                ExperimentLifecycleState.INVALID,
            )
        )
        == TERMINAL_EXPERIMENT_STATES
    )


def test_derive_experiment_lifecycle_empty_ready_experiment_is_ready() -> None:
    plan = build_plan(resolved_core_complete=False)
    planned = plan.experiment(ExperimentName.PROTOCOL_INVARIANT_VALIDATION)
    assert derive_experiment_lifecycle(planned, ()) is ExperimentLifecycleState.READY


def test_derive_experiment_lifecycle_empty_post_core_experiment_is_blocked() -> None:
    plan = build_plan(resolved_core_complete=False)
    planned = plan.experiment(ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION)
    assert derive_experiment_lifecycle(planned, ()) is ExperimentLifecycleState.BLOCKED


def test_data_validation_status_requires_current_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_plan(resolved_core_complete=False)
    planned = plan.experiment(ExperimentName.DATA_AND_DOMAIN_EVIDENCE_VALIDATION)
    cell = planned.cells[0]
    stale_record = PersistedExecutionRecord(
        schema_version="fedsira|execution_record|2",
        semantic_key=cell.semantic_key,
        experiment=cell.experiment,
        method=cell.method,
        condition=cell.condition,
        master_seed=cell.master_seed,
        terminal_state=ExperimentLifecycleState.COMPLETED,
        metrics=(("terminal-state", 1.0),),
        failure=None,
        provenance=None,
    )
    current_provenance = _provenance()

    def current_provenance_for_dataset(_dataset: DatasetId) -> ExecutionProvenance:
        return current_provenance

    monkeypatch.setattr(
        "fedsira.experiments.engine.current_execution_provenance",
        current_provenance_for_dataset,
    )
    assert (
        derive_current_experiment_lifecycle(
            planned, (stale_record,), ExperimentLifecycleState.READY
        )
        is ExperimentLifecycleState.READY
    )
    assert (
        derive_current_experiment_lifecycle(
            planned, (stale_record,), ExperimentLifecycleState.COMPLETED
        )
        is ExperimentLifecycleState.READY
    )
    current_record = stale_record.model_copy(
        update={
            "schema_version": EXECUTION_RECORD_SCHEMA_VERSION,
            "provenance": current_provenance,
        }
    )
    assert (
        derive_current_experiment_lifecycle(
            planned, (current_record,), ExperimentLifecycleState.COMPLETED
        )
        is ExperimentLifecycleState.COMPLETED
    )


def test_other_experiment_status_also_requires_current_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_plan(resolved_core_complete=False)
    planned = plan.experiment(ExperimentName.PROTOCOL_INVARIANT_VALIDATION)
    cell = planned.cells[0]
    current_provenance = _provenance()
    stale_record = PersistedExecutionRecord(
        schema_version="fedsira|execution_record|2",
        semantic_key=cell.semantic_key,
        experiment=cell.experiment,
        method=cell.method,
        condition=cell.condition,
        master_seed=cell.master_seed,
        terminal_state=ExperimentLifecycleState.COMPLETED,
        metrics=(("terminal-state", 1.0),),
        failure=None,
        provenance=None,
    )

    def current_provenance_for_dataset(_dataset: DatasetId) -> ExecutionProvenance:
        return current_provenance

    monkeypatch.setattr(
        "fedsira.experiments.engine.current_execution_provenance",
        current_provenance_for_dataset,
    )

    assert (
        derive_current_experiment_lifecycle(
            planned, (stale_record,), ExperimentLifecycleState.COMPLETED
        )
        is ExperimentLifecycleState.READY
    )
    current_record = stale_record.model_copy(
        update={
            "schema_version": EXECUTION_RECORD_SCHEMA_VERSION,
            "provenance": current_provenance,
        }
    )
    assert (
        derive_current_experiment_lifecycle(
            planned, (current_record,), ExperimentLifecycleState.COMPLETED
        )
        is ExperimentLifecycleState.COMPLETED
    )


def _provenance() -> ExecutionProvenance:
    return ExecutionProvenance(
        configuration_digest="a" * 64,
        code_revision=None,
        dataset_manifest_hash="b" * 64,
    )


def test_record_store_round_trip(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    cell = _cell(
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        SourceExclusionMethod.FULL_FEDSIRA,
        "All Honest",
        1,
    )
    outcome = _completed_outcome(cell).model_copy(update={"scoring_artifact_ids": ("c" * 64,)})
    store.write_outcome(outcome, _provenance())
    restored = store.read_outcome(cell.experiment, cell.semantic_key)
    assert restored is not None
    assert isinstance(restored, PersistedExecutionRecord)
    assert restored.terminal_state is ExperimentLifecycleState.COMPLETED
    assert restored.semantic_key == cell.semantic_key
    assert restored.scoring_artifact_ids == ("c" * 64,)
    assert len(store.read_all_outcomes(cell.experiment)) == 1


def test_semantic_key_excludes_reuse_provenance() -> None:
    cell = _cell(
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        SourceExclusionMethod.FULL_FEDSIRA,
        "All Honest",
        1,
    )
    first = _provenance()
    changed = first.model_copy(
        update={
            "configuration_digest": "c" * 64,
            "code_revision": "deadbeef",
            "dataset_manifest_hash": "d" * 64,
        }
    )

    assert cell.semantic_key == "Single-Reproduction Necessity|Full FedSIRA|All Honest|1|"
    assert first != changed


def test_infrastructure_retry_reuses_the_same_scientific_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cell = _cell(
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        SourceExclusionMethod.FULL_FEDSIRA,
        "All Honest",
        1,
    )
    calls: list[ScientificCell] = []

    def phase(
        _cell: ScientificCell, _executor: CellExecutor, _timeout: float
    ) -> CellExecutionOutcome:
        calls.append(_cell)
        if len(calls) == 1:
            return CellExecutionOutcome(
                cell=_cell,
                terminal_state=ExperimentLifecycleState.FAILED,
                failure=FailureDetail(
                    failure_class=FailureClass.INFRASTRUCTURE_INTERRUPTION,
                    message="fixture interruption",
                    cell_phase=ScientificCellPhase.PROTOCOL_EVALUATION,
                ),
            )
        return _completed_outcome(_cell)

    monkeypatch.setattr("fedsira.experiments.engine._execute_cell_phase_with_timeout", phase)
    outcome = execute_cell_with_retry(cell, cast(CellExecutor, object()))

    assert outcome.terminal_state is ExperimentLifecycleState.COMPLETED
    assert calls == [cell, cell]
    assert calls[0].semantic_key == calls[1].semantic_key


def test_cell_terminal_log_fields_include_bounded_failure_context() -> None:
    cell = _cell(
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        SourceExclusionMethod.FULL_FEDSIRA,
        "All Honest",
        1,
    )
    failure = FailureDetail(
        failure_class=FailureClass.DATA_INVALID,
        message="x" * 400,
        cell_phase=ScientificCellPhase.PROTOCOL_EVALUATION,
    )

    fields = ExecutionLogFields(
        experiment=cell.experiment,
        dataset=DatasetId.N_BAIOT,
        cell=cell.semantic_key,
    )
    terminal = fields.with_cell_terminal_state(ExperimentLifecycleState.FAILED, 1, failure)
    metric = terminal.with_metric("accuracy")

    assert terminal.failure_class is FailureClass.DATA_INVALID
    assert terminal.dataset is DatasetId.N_BAIOT
    assert terminal.failure_phase is ScientificCellPhase.PROTOCOL_EVALUATION
    assert terminal.failure_message == "x" * 256
    assert metric.failure_class is terminal.failure_class
    assert metric.failure_phase is terminal.failure_phase


def test_record_store_read_missing_returns_none(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    assert (
        store.read_outcome(ExperimentName.SECONDARY_DATASET_GENERALIZATION, "missing-key") is None
    )
    assert store.read_all_outcomes(ExperimentName.SECONDARY_DATASET_GENERALIZATION) == ()


def test_record_store_read_malformed_record_is_rejected(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    cell = _cell(
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        SourceExclusionMethod.FULL_FEDSIRA,
        "All Honest",
        1,
    )
    store.write_outcome(_completed_outcome(cell), _provenance())
    record_dir = tmp_path / "experiments" / cell.experiment / "records"
    next(record_dir.glob("*.json")).write_text("{not valid json")
    with pytest.raises(pydantic.ValidationError):
        store.read_all_outcomes(cell.experiment)


def test_validate_experiment_prerequisites_requires_completed_state() -> None:
    completed = (
        ExperimentPrerequisiteState(
            experiment=ExperimentName.PROPOSAL_ASSISTED_OPENING_NECESSITY,
            lifecycle_state=ExperimentLifecycleState.COMPLETED,
        ),
    )
    validate_experiment_prerequisites_met(ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION, completed)
    incomplete = (
        ExperimentPrerequisiteState(
            experiment=ExperimentName.PROPOSAL_ASSISTED_OPENING_NECESSITY,
            lifecycle_state=ExperimentLifecycleState.NOT_STARTED,
        ),
    )
    with pytest.raises(ValueError):
        validate_experiment_prerequisites_met(
            ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION, incomplete
        )


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
    cell = _cell(
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        SourceExclusionMethod.FULL_FEDSIRA,
        "All Honest",
        1,
    )
    validate_cell_terminal_record(cell, ExperimentLifecycleState.COMPLETED)
    validate_cell_terminal_record(cell, ExperimentLifecycleState.FAILED)
    with pytest.raises(ValueError):
        validate_cell_terminal_record(cell, ExperimentLifecycleState.RUNNING)


def test_execute_experiment_rejects_missing_prerequisite() -> None:
    class NeverExecutor:
        def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome:
            raise AssertionError(f"unexpected execution of {cell.semantic_key}")

    incomplete = (
        ExperimentPrerequisiteState(
            experiment=ExperimentName.DATA_AND_DOMAIN_EVIDENCE_VALIDATION,
            lifecycle_state=ExperimentLifecycleState.NOT_STARTED,
        ),
    )
    with pytest.raises(ValueError, match="requires prerequisite"):
        execute_experiment(
            ExperimentName.PROPOSAL_ASSISTED_OPENING_NECESSITY,
            NeverExecutor(),
            prerequisite_states=incomplete,
        )


def test_execute_experiment_reuses_completed_records_without_reexecution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CountingExecutor:
        def __init__(self) -> None:
            self.executions = 0

        def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome:
            self.executions += 1
            return _completed_outcome(cell)

    _override_workspace_root(tmp_path, monkeypatch)
    executor = CountingExecutor()
    result = execute_experiment(ExperimentName.PROTOCOL_INVARIANT_VALIDATION, executor)
    assert executor.executions == 1
    assert result.lifecycle_state is ExperimentLifecycleState.COMPLETED
    second = execute_experiment(ExperimentName.PROTOCOL_INVARIANT_VALIDATION, executor)
    assert executor.executions == 1
    assert second.lifecycle_state is ExperimentLifecycleState.COMPLETED


def test_experiment_identity_set_closes_over_the_registry() -> None:
    registered = frozenset(definition.name for definition in experiment_registry())
    assert registered == frozenset(ExperimentName)


def test_execute_experiment_invalid_outcome_yields_invalid_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InvalidExecutor:
        def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome:
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.INVALID,
                failure=None,
                metrics=(),
            )

    _override_workspace_root(tmp_path, monkeypatch)
    result = execute_experiment(ExperimentName.PROTOCOL_INVARIANT_VALIDATION, InvalidExecutor())
    assert result.lifecycle_state is ExperimentLifecycleState.INVALID


def test_execute_experiment_failed_outcome_yields_failed_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedExecutor:
        def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome:
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.FAILED,
                failure=None,
                metrics=(),
            )

    _override_workspace_root(tmp_path, monkeypatch)
    result = execute_experiment(ExperimentName.PROTOCOL_INVARIANT_VALIDATION, FailedExecutor())
    assert result.lifecycle_state is ExperimentLifecycleState.FAILED


def test_record_store_rejects_reuse_when_provenance_changed(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    cell = _cell(
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        SourceExclusionMethod.FULL_FEDSIRA,
        "All Honest",
        1,
    )
    store.write_outcome(_completed_outcome(cell), _provenance())
    provenance = _provenance()
    assert store.reusable_outcome(cell.experiment, cell.semantic_key, provenance) is not None
    changed = provenance.model_copy(update={"configuration_digest": "c" * 64})
    assert store.reusable_outcome(cell.experiment, cell.semantic_key, changed) is None
    changed_revision = provenance.model_copy(update={"code_revision": "deadbeef"})
    assert store.reusable_outcome(cell.experiment, cell.semantic_key, changed_revision) is None
    changed_dataset = provenance.model_copy(update={"dataset_manifest_hash": "d" * 64})
    assert store.reusable_outcome(cell.experiment, cell.semantic_key, changed_dataset) is None


def test_record_store_does_not_reuse_an_incomplete_record(tmp_path: Path) -> None:
    store = ExecutionRecordStore(tmp_path)
    cell = _cell(
        ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        SourceExclusionMethod.FULL_FEDSIRA,
        "All Honest",
        1,
    )
    store.write_outcome(
        CellExecutionOutcome(
            cell=cell,
            terminal_state=ExperimentLifecycleState.FAILED,
            failure=None,
        ),
        _provenance(),
    )
    assert store.reusable_outcome(cell.experiment, cell.semantic_key, _provenance()) is None
