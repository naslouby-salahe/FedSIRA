from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from fedsira.artifacts import ReconstructionProvenance, collect_reconstruction_provenance
from fedsira.domain.enums import (
    DatasetId,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
)
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
    OverwriteExisting,
    ResolvedCoreComplete,
    ScenarioName,
    ScientificCellCount,
    ScientificCellSemanticKey,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.experiments.definitions import experiment_by_name
from fedsira.experiments.planning import (
    ExperimentPlan,
    PlannedExperiment,
    ScientificCell,
    build_plan,
)
from fedsira.experiments.validation import (
    ExperimentPrerequisiteState,
    validate_cell_terminal_record,
    validate_condition_vocabulary,
    validate_experiment_prerequisites_met,
    validate_no_duplicate_semantic_cells,
)
from fedsira.runtime import FailureDetail, automatic_recovery_permitted, current_application_context
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


class ExperimentExecutionDigestInput(FrozenDomainModel):
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    semantic_keys: tuple[ScientificCellSemanticKey, ...]


def execution_digest(
    experiment: ExperimentName,
    lifecycle_state: ExperimentLifecycleState,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> ArtifactDigest:
    payload = ExperimentExecutionDigestInput(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        semantic_keys=tuple(outcome.cell.semantic_key for outcome in outcomes),
    )
    return hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()


def execute_cell_with_retry(cell: ScientificCell, executor: CellExecutor) -> CellExecutionOutcome:
    config = current_application_context().scientific_config
    attempts = config.execution.automatic_infrastructure_retries_per_cell_phase + 1
    last_outcome: CellExecutionOutcome | None = None
    for attempt in range(attempts):
        outcome = executor.execute_cell(cell)
        validate_cell_terminal_record(cell, outcome.terminal_state)
        if outcome.terminal_state is not ExperimentLifecycleState.FAILED:
            return outcome
        if outcome.failure is None or not automatic_recovery_permitted(
            outcome.failure.failure_class,
            attempt,
            config.execution.automatic_infrastructure_retries_per_cell_phase,
        ):
            return outcome
        last_outcome = outcome
    if last_outcome is None:
        raise RuntimeError("cell retry loop produced no outcome")
    return last_outcome


def planned_execution_records(
    planned: PlannedExperiment, records: tuple[PersistedExecutionRecord, ...]
) -> tuple[PersistedExecutionRecord, ...]:
    planned_keys = frozenset(cell.semantic_key for cell in planned.cells)
    return tuple(record for record in records if record.semantic_key in planned_keys)


def derive_experiment_lifecycle(
    planned: PlannedExperiment, records: tuple[PersistedExecutionRecord, ...]
) -> ExperimentLifecycleState:
    if planned.lifecycle_state is ExperimentLifecycleState.BLOCKED:
        return ExperimentLifecycleState.BLOCKED
    relevant = planned_execution_records(planned, records)
    if not relevant:
        return ExperimentLifecycleState.READY
    if any(record.terminal_state is ExperimentLifecycleState.INVALID for record in relevant):
        return ExperimentLifecycleState.INVALID
    if any(record.terminal_state is ExperimentLifecycleState.FAILED for record in relevant):
        return ExperimentLifecycleState.FAILED
    complete = all(
        any(
            record.semantic_key == cell.semantic_key
            and record.terminal_state is ExperimentLifecycleState.COMPLETED
            for record in relevant
        )
        for cell in planned.cells
    )
    return ExperimentLifecycleState.COMPLETED if complete else ExperimentLifecycleState.RUNNING


class ComparisonResultBuilder(Protocol):
    def __call__(
        self,
        experiment: ExperimentName,
        dataset: DatasetId,
        outcomes: tuple[CellExecutionOutcome, ...],
        store: ExecutionRecordStore,
    ) -> tuple[ComparisonFamilyResult, ...]: ...


def _prerequisite_states_from_store(
    plan: ExperimentPlan, experiment: ExperimentName, store: ExecutionRecordStore
) -> tuple[ExperimentPrerequisiteState, ...]:
    definition = experiment_by_name(experiment)
    return tuple(
        ExperimentPrerequisiteState(
            experiment=prerequisite,
            lifecycle_state=derive_experiment_lifecycle(
                plan.experiment(prerequisite),
                store.read_planned_outcomes(plan.experiment(prerequisite)),
            ),
        )
        for prerequisite in definition.prerequisites
    )


def execute_experiment(
    experiment: ExperimentName,
    executor: CellExecutor,
    comparison_builder: ComparisonResultBuilder | None = None,
    *,
    overwrite: OverwriteExisting = False,
    resolved_core_complete: ResolvedCoreComplete = False,
    prerequisite_states: tuple[ExperimentPrerequisiteState, ...] | None = None,
) -> ExperimentExecutionResult:
    resolved_config = current_application_context().scientific_config
    definition = experiment_by_name(experiment)
    plan = build_plan(
        resolved_core_complete=resolved_core_complete,
        master_seeds=resolved_config.seeds_and_determinism.master_seeds,
        smoke_seed=resolved_config.seeds_and_determinism.smoke_seed,
    )
    validate_condition_vocabulary(plan)
    validate_no_duplicate_semantic_cells(plan)
    planned = plan.experiment(experiment)
    if planned.lifecycle_state is ExperimentLifecycleState.BLOCKED:
        return ExperimentExecutionResult(
            experiment=experiment, lifecycle_state=ExperimentLifecycleState.BLOCKED, outcomes=()
        )
    store = ExecutionRecordStore(
        Path(resolved_config.execution.repository_layout.execution_workspace),
        reconstruction_provenance=collect_reconstruction_provenance(
            current_application_context().repository_root
        ),
    )
    states = prerequisite_states or _prerequisite_states_from_store(plan, experiment, store)
    validate_experiment_prerequisites_met(experiment, states)
    outcomes: list[CellExecutionOutcome] = []
    for cell in planned.cells:
        existing = store.read_outcome(experiment, cell.semantic_key)
        if (
            existing is not None
            and not overwrite
            and existing.terminal_state is ExperimentLifecycleState.COMPLETED
        ):
            outcomes.append(
                CellExecutionOutcome(
                    cell=cell,
                    terminal_state=existing.terminal_state,
                    failure=None,
                    metrics=existing.metrics,
                )
            )
            continue
        outcome = execute_cell_with_retry(cell, executor)
        store.write_outcome(outcome)
        outcomes.append(outcome)
    outcome_tuple = tuple(outcomes)
    lifecycle_state = derive_experiment_lifecycle(planned, store.read_planned_outcomes(planned))
    comparisons = (
        ()
        if comparison_builder is None
        else comparison_builder(experiment, definition.dataset, outcome_tuple, store)
    )
    return ExperimentExecutionResult(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        outcomes=outcome_tuple,
        comparison_results=comparisons,
        execution_digest=execution_digest(experiment, lifecycle_state, outcome_tuple),
    )


class ExecutionRecordStore:
    def __init__(
        self,
        workspace_root: Path,
        reconstruction_provenance: ReconstructionProvenance | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._reconstruction_provenance = reconstruction_provenance

    def _record_directory(self, experiment: ExperimentName) -> Path:
        return self._workspace_root / "experiments" / experiment / "records"

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
