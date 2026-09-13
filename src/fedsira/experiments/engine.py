from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from fedsira.artifacts.paths import artifact_instance_token
from fedsira.artifacts.store import ArtifactSlot
from fedsira.datasets.common import PreparedViewSidecar, Role
from fedsira.datasets.prepared_validation import prepared_view_publication_failures
from fedsira.domain.enums import (
    AdmissionState,
    ArtifactFamily,
    DatasetId,
    ExperimentLifecycleState,
    FailureClass,
    LogEvent,
    ScientificCellPhase,
    WorkspaceDirectoryToken,
)
from fedsira.domain.models import (
    PreparedEvidenceCounts,
    ScientificCell,
)
from fedsira.domain.types import (
    ArtifactDigest,
    CellCompletionStatus,
    DatasetClassToken,
    DomainId,
    EvidenceCycleIndex,
    ExecutionSchemaVersion,
    ExperimentName,
    FailureMessage,
    FrozenDomainModel,
    LogRecordText,
    MasterSeed,
    MethodName,
    MetricName,
    MetricObservation,
    MetricValue,
    OverwriteExisting,
    ProcedureIdentity,
    RepetitionIndex,
    ScenarioName,
    ScientificCellCount,
    ScientificCellSemanticKey,
    TextValue,
    TimeoutSeconds,
)
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.experiments.definitions import MECHANISM_ABLATION_NAME, experiment_by_name
from fedsira.experiments.planning import (
    ExperimentPlan,
    PlannedExperiment,
)
from fedsira.runtime import (
    FailureDetail,
    OperationTimeoutError,
    automatic_recovery_permitted,
    current_application_context,
    framed_bytes,
    get_structured_logger,
    run_bounded,
)

if TYPE_CHECKING:
    from fedsira.experiments.execution import ExperimentPrerequisiteState

EXECUTION_RECORD_SCHEMA_VERSION: ExecutionSchemaVersion = "fedsira|execution_record|2"
ABLATION_REFERENCE_SCHEMA_VERSION: ExecutionSchemaVersion = "fedsira|ablation_reference|1"
ABLATION_REFERENCE_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|ablation_reference|1"
EXECUTION_LOGGER = get_structured_logger(WorkspaceDirectoryToken.EXECUTION)


class CellPhaseLogFields(FrozenDomainModel):
    cell: ScientificCellSemanticKey
    timeout_seconds: TimeoutSeconds | None = None


class PersistedFailureDetail(FrozenDomainModel):
    failure_class: FailureClass
    message: FailureMessage
    cell_phase: ScientificCellPhase | None


class AdmissionStateObservation(FrozenDomainModel):
    cycle: EvidenceCycleIndex
    state: AdmissionState


class ExecutionProvenance(FrozenDomainModel):
    configuration_digest: ArtifactDigest
    code_revision: TextValue | None
    dataset_manifest_hash: ArtifactDigest


class PersistedExecutionRecord(FrozenDomainModel):
    schema_version: ExecutionSchemaVersion
    semantic_key: ScientificCellSemanticKey
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    repetition: RepetitionIndex | None = None
    terminal_state: ExperimentLifecycleState
    metrics: tuple[MetricObservation, ...]
    state_trajectory: tuple[AdmissionStateObservation, ...] = ()
    failure: PersistedFailureDetail | None
    provenance: ExecutionProvenance | None = None


def ablation_reference_slot(
    scientific_scenario: ScenarioName, master_seed: MasterSeed
) -> ArtifactSlot:
    return ArtifactSlot(
        family=ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT,
        instance=artifact_instance_token(scientific_scenario, master_seed),
        experiment=MECHANISM_ABLATION_NAME,
    )


class PersistedAblationReference(FrozenDomainModel):
    schema_version: ExecutionSchemaVersion
    scientific_scenario: ScenarioName
    master_seed: MasterSeed
    metrics: tuple[MetricObservation, ...]
    state_trajectory: tuple[AdmissionStateObservation, ...] = ()


class CellExecutionOutcome(FrozenDomainModel):
    cell: ScientificCell
    terminal_state: ExperimentLifecycleState
    failure: FailureDetail | None
    metrics: tuple[MetricObservation, ...] = ()
    state_trajectory: tuple[AdmissionStateObservation, ...] = ()

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


class ExecutionLogFields(FrozenDomainModel):
    experiment: ExperimentName
    dataset: DatasetId | None = None
    overwrite: OverwriteExisting | None = None
    cell: ScientificCellSemanticKey | None = None
    method: MethodName | None = None
    condition: ScenarioName | None = None
    master_seed: MasterSeed | None = None
    metric: MetricName | None = None
    terminal_state: ExperimentLifecycleState | None = None
    completed_cells: ScientificCellCount | None = None
    total_cells: ScientificCellCount | None = None
    elapsed_seconds: MetricValue | None = None

    def with_cell_terminal_state(
        self,
        terminal_state: ExperimentLifecycleState,
        completed_cells: ScientificCellCount,
    ) -> ExecutionLogFields:
        return ExecutionLogFields(
            experiment=self.experiment,
            overwrite=self.overwrite,
            cell=self.cell,
            method=self.method,
            condition=self.condition,
            master_seed=self.master_seed,
            metric=self.metric,
            terminal_state=terminal_state,
            completed_cells=completed_cells,
            total_cells=self.total_cells,
            elapsed_seconds=self.elapsed_seconds,
        )

    def with_metric(self, metric: MetricName) -> ExecutionLogFields:
        return ExecutionLogFields(
            experiment=self.experiment,
            overwrite=self.overwrite,
            cell=self.cell,
            method=self.method,
            condition=self.condition,
            master_seed=self.master_seed,
            metric=metric,
            terminal_state=self.terminal_state,
            completed_cells=self.completed_cells,
            total_cells=self.total_cells,
            elapsed_seconds=self.elapsed_seconds,
        )


def log_execution_event(event: LogRecordText, fields: ExecutionLogFields) -> None:
    EXECUTION_LOGGER.info(event, extra=fields.model_dump())


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

    @property
    def execution_digest(self) -> ArtifactDigest:
        return experiment_execution_digest(self.experiment, self.lifecycle_state, self.outcomes)

    @property
    def cell_completion_count(self) -> ScientificCellCount:
        return sum(1 for outcome in self.outcomes if outcome.completed)


class CellExecutor(Protocol):
    def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome: ...


class ExperimentExecutionDigestInput(FrozenDomainModel):
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    semantic_keys: tuple[ScientificCellSemanticKey, ...]


def experiment_execution_digest(
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
    from fedsira.experiments.execution import validate_cell_terminal_record

    config = current_application_context().scientific_config
    attempts = config.execution.automatic_infrastructure_retries_per_cell_phase + 1
    cell_phase_timeout = config.execution.timeouts_seconds.scientific_cell_phase
    last_outcome: CellExecutionOutcome | None = None
    for attempt in range(attempts):
        outcome = _execute_cell_phase_with_timeout(cell, executor, cell_phase_timeout)
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


def _execute_cell_phase_with_timeout(
    cell: ScientificCell,
    executor: CellExecutor,
    timeout_seconds: TimeoutSeconds,
) -> CellExecutionOutcome:
    EXECUTION_LOGGER.info(
        LogEvent.CELL_PHASE_STARTED,
        extra=CellPhaseLogFields(
            cell=cell.semantic_key, timeout_seconds=timeout_seconds
        ).model_dump(),
    )
    try:
        outcome = run_bounded(
            "scientific_cell_phase", #TODO: use enum not hardcoded string
            timeout_seconds, lambda: executor.execute_cell(cell)
        )
    except OperationTimeoutError:
        EXECUTION_LOGGER.info(
            LogEvent.CELL_PHASE_TIMEOUT,
            extra=CellPhaseLogFields(
                cell=cell.semantic_key, timeout_seconds=timeout_seconds
            ).model_dump(),
        )
        return CellExecutionOutcome(
            cell=cell,
            terminal_state=ExperimentLifecycleState.FAILED,
            failure=FailureDetail(
                failure_class=FailureClass.TIMEOUT,
                message=(
                    "scientific cell phase exceeded "
                    f"execution.timeouts_seconds.scientific_cell_phase={timeout_seconds}"
                ),
                cell_phase=ScientificCellPhase.PROTOCOL_EVALUATION,
            ),
        )
    EXECUTION_LOGGER.info(
        LogEvent.CELL_PHASE_COMPLETED, extra=CellPhaseLogFields(cell=cell.semantic_key).model_dump()
    )
    return outcome


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


def prerequisite_states_from_store(
    plan: ExperimentPlan, experiment: ExperimentName, store: ExecutionRecordStore
) -> tuple[ExperimentPrerequisiteState, ...]:
    from fedsira.experiments.execution import ExperimentPrerequisiteState

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


class ExecutionRecordStore:
    def __init__(
        self,
        workspace_root: Path,
    ) -> None:
        self._workspace_root = workspace_root

    def _record_directory(self, experiment: ExperimentName) -> Path:
        return (
            self._workspace_root
            / WorkspaceDirectoryToken.EXPERIMENTS
            / experiment
            / WorkspaceDirectoryToken.RECORDS
        )

    def write_outcome(self, outcome: CellExecutionOutcome, provenance: ExecutionProvenance) -> None:
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
            repetition=outcome.cell.repetition,
            terminal_state=outcome.terminal_state,
            metrics=outcome.metrics,
            state_trajectory=outcome.state_trajectory,
            failure=failure,
            provenance=provenance,
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

    def reusable_outcome(
        self,
        experiment: ExperimentName,
        semantic_key: ScientificCellSemanticKey,
        provenance: ExecutionProvenance,
    ) -> PersistedExecutionRecord | None:
        record = self.read_outcome(experiment, semantic_key)
        if record is None:
            return None
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            return None
        if record.provenance != provenance:
            log_execution_event(
                LogEvent.CELL_REUSE_REJECTED,
                ExecutionLogFields(experiment=experiment, cell=semantic_key),
            )
            return None
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


class PreparedEvidenceProvenanceError(ValueError):
    def __init__(self, failures: tuple[FailureMessage, ...]) -> None:
        super().__init__("; ".join(failures))
        self.failures = failures


def invalid_prepared_evidence_outcome(
    cell: ScientificCell,
    failure_class: FailureClass,
    message: FailureMessage,
) -> CellExecutionOutcome:
    return CellExecutionOutcome(
        cell=cell,
        terminal_state=ExperimentLifecycleState.INVALID,
        failure=FailureDetail(
            failure_class=failure_class,
            message=message,
            cell_phase=ScientificCellPhase.PREPARE,
        ),
    )


def load_prepared_evidence_counts(
    prepared_root: Path, target_class_token: DatasetClassToken
) -> PreparedEvidenceCounts | None:
    if not prepared_root.exists():
        return None
    provenance_failures = prepared_view_publication_failures(prepared_root)
    if provenance_failures:
        raise PreparedEvidenceProvenanceError(provenance_failures)
    screen_target_count = 0
    reproduction_target_count = 0
    reproduction_supported_count = 0
    final_gate_target_domains: set[DomainId] = set()
    for metadata_path in sorted(prepared_root.glob("*.json")):
        try:
            payload = PreparedViewSidecar.model_validate_json(metadata_path.read_text())
        except (ValueError, json.JSONDecodeError, OSError):
            continue
        if payload.role is Role.CANDIDATE_SCREEN and payload.class_id == target_class_token:
            screen_target_count += payload.row_count
        elif payload.role is Role.REPRODUCTION and payload.class_id == target_class_token:
            reproduction_target_count += payload.row_count
        elif payload.role is Role.POST_REFERENCE_REPLAY and payload.class_id != target_class_token:
            reproduction_supported_count += payload.row_count
        elif payload.role is Role.FINAL_GATE and payload.class_id == target_class_token:
            final_gate_target_domains.add(payload.domain)
    if screen_target_count == 0 and reproduction_target_count == 0:
        return None
    return PreparedEvidenceCounts(
        screen_target_count=screen_target_count,
        reproduction_target_count=reproduction_target_count,
        reproduction_supported_count=reproduction_supported_count,
        final_gate_adequate_domain_count=len(final_gate_target_domains),
    )
