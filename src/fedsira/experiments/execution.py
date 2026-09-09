from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from fedsira.artifacts import ReconstructionProvenance
from fedsira.domain.enums import ExperimentLifecycleState, FailureClass, ScientificCellPhase
from fedsira.domain.types import (
    ArtifactDigest,
    CellCompletionStatus,
    ExecutionSchemaVersion,
    ExperimentName,
    FailureMessage,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricObservation,
    MetricValue,
    ScenarioName,
    ScientificCellCount,
    ScientificCellSemanticKey,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.experiments.planning import PlannedExperiment, ScientificCell
from fedsira.runtime import FailureDetail
from fedsira.runtime_execution import framed_bytes

EXECUTION_RECORD_SCHEMA_VERSION: ExecutionSchemaVersion = "fedsira|execution_record|1"


class PersistedFailureDetail(FrozenDomainModel):
    failure_class: FailureClass
    message: FailureMessage
    cell_phase: ScientificCellPhase | None


class PersistedExecutionRecord(FrozenDomainModel):
    schema_version: ExecutionSchemaVersion
    semantic_key: ScientificCellSemanticKey
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    terminal_state: ExperimentLifecycleState
    metrics: tuple[MetricObservation, ...]
    failure: PersistedFailureDetail | None
    reconstruction_provenance: ReconstructionProvenance | None = None


class CellExecutionOutcome(FrozenDomainModel):
    cell: ScientificCell
    terminal_state: ExperimentLifecycleState
    failure: FailureDetail | None
    metrics: tuple[MetricObservation, ...] = ()

    @property
    def completed(self) -> CellCompletionStatus:
        return self.terminal_state is ExperimentLifecycleState.COMPLETED


class ProtocolPhaseDurations(FrozenDomainModel):
    assignment_seconds: MetricValue = 0.0
    reproduce_seconds: MetricValue = 0.0
    verify_seconds: MetricValue = 0.0
    synthesize_seconds: MetricValue = 0.0

    def with_verify_seconds(self, elapsed_seconds: MetricValue) -> ProtocolPhaseDurations:
        return ProtocolPhaseDurations(
            assignment_seconds=self.assignment_seconds,
            reproduce_seconds=self.reproduce_seconds,
            verify_seconds=elapsed_seconds,
            synthesize_seconds=self.synthesize_seconds,
        )

    def with_synthesize_seconds(self, elapsed_seconds: MetricValue) -> ProtocolPhaseDurations:
        return ProtocolPhaseDurations(
            assignment_seconds=self.assignment_seconds,
            reproduce_seconds=self.reproduce_seconds,
            verify_seconds=self.verify_seconds,
            synthesize_seconds=elapsed_seconds,
        )


TERMINAL_EXPERIMENT_STATES: frozenset[ExperimentLifecycleState] = frozenset(
    (
        ExperimentLifecycleState.COMPLETED,
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
    )
)


class ExperimentExecutionResult(FrozenDomainModel):
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    outcomes: tuple[CellExecutionOutcome, ...]
    comparison_results: tuple[ComparisonFamilyResult, ...] = ()
    execution_digest: ArtifactDigest | None = None

    @property
    def cell_completion_count(self) -> ScientificCellCount:
        return sum(1 for outcome in self.outcomes if outcome.completed)


class CellExecutor(Protocol):
    def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome: ...


class ExecutionRecordStore:
    def __init__(
        self,
        workspace_root: Path,
        reconstruction_provenance: ReconstructionProvenance | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._reconstruction_provenance = reconstruction_provenance

    def _record_directory(self, experiment: ExperimentName) -> Path:
        return self._workspace_root / "experiments" / experiment / "evaluations" / "records"

    def write_outcome(self, outcome: CellExecutionOutcome) -> None:
        directory = self._record_directory(outcome.cell.experiment)
        directory.mkdir(parents=True, exist_ok=True)
        failure = (
            None
            if outcome.failure is None
            else PersistedFailureDetail(
                failure_class=outcome.failure.failure_class,
                message=outcome.failure.message,
                cell_phase=outcome.failure.cell_phase,
            )
        )
        record = PersistedExecutionRecord(
            schema_version=EXECUTION_RECORD_SCHEMA_VERSION,
            semantic_key=outcome.cell.semantic_key,
            experiment=outcome.cell.experiment,
            method=outcome.cell.method,
            condition=outcome.cell.condition,
            master_seed=outcome.cell.master_seed,
            terminal_state=outcome.terminal_state,
            metrics=outcome.metrics,
            failure=failure,
            reconstruction_provenance=self._reconstruction_provenance,
        )
        digest = hashlib.sha256(framed_bytes(outcome.cell.semantic_key)).hexdigest()
        (directory / f"{digest}.json").write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )

    def read_outcome(
        self, experiment: ExperimentName, semantic_key: ScientificCellSemanticKey
    ) -> PersistedExecutionRecord | None:
        digest = hashlib.sha256(framed_bytes(semantic_key)).hexdigest()
        path = self._record_directory(experiment) / f"{digest}.json"
        if not path.exists():
            return None
        record = PersistedExecutionRecord.model_validate_json(path.read_text(encoding="utf-8"))
        if record.semantic_key != semantic_key or record.experiment != experiment:
            raise ValueError("persisted execution record identity mismatch")
        return record

    def read_all_outcomes(self, experiment: ExperimentName) -> tuple[PersistedExecutionRecord, ...]:
        directory = self._record_directory(experiment)
        if not directory.exists():
            return ()
        records = tuple(
            PersistedExecutionRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("*.json"))
        )
        for record in records:
            if record.experiment != experiment:
                raise ValueError("persisted execution record experiment mismatch")
        return records

    def read_planned_outcomes(
        self, planned: PlannedExperiment
    ) -> tuple[PersistedExecutionRecord, ...]:
        expected_keys = frozenset(cell.semantic_key for cell in planned.cells)
        return tuple(
            record
            for record in self.read_all_outcomes(planned.definition.name)
            if record.semantic_key in expected_keys
        )
