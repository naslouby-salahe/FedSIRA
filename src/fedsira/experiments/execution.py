from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pydantic

from fedsira.analysis.comparisons import (
    ComparisonFamilyResult,
    ComparisonOrientation,
    ComparisonResult,
    ComparisonTestKind,
    PairingKey,
    apply_holm_adjustment,
    build_comparison_registry,
    complete_paired_seeds,
    evaluate_comparison,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.config.schema import ScientificConfig
from fedsira.domain.enums import (
    CellPhaseState,
    DatasetId,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
)
from fedsira.domain.records import ArtifactDigest, CanonicalToken, MasterSeed
from fedsira.experiments.planning import ScientificCell, build_plan
from fedsira.experiments.registry import ClaimFamily
from fedsira.experiments.validation import (
    validate_cell_phase_sequence,
    validate_cell_terminal_record,
    validate_condition_vocabulary,
    validate_experiment_name_is_registered,
    validate_experiment_prerequisites_met,
    validate_no_duplicate_semantic_cells,
)
from fedsira.runtime.determinism import canonical_bytes
from fedsira.runtime.state import FailureDetail

EXECUTION_RECORD_SCHEMA_VERSION = "fedsira|execution_record|1"

TERMINAL_EXPERIMENT_STATES = frozenset(
    {
        ExperimentLifecycleState.COMPLETED,
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
    }
)


class PersistedFailureDetail(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")

    failure_class: FailureClass
    message: CanonicalToken
    cell_phase: ScientificCellPhase | None


class PersistedExecutionRecord(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")

    schema_version: str
    semantic_key: CanonicalToken
    experiment: CanonicalToken
    method: CanonicalToken
    condition: CanonicalToken
    master_seed: MasterSeed
    terminal_state: CanonicalToken
    metrics: tuple[tuple[CanonicalToken, float | None], ...]
    failure: PersistedFailureDetail | None


@dataclass(frozen=True)
class CellExecutionOutcome:
    cell: ScientificCell
    terminal_state: str
    failure: FailureDetail | None
    metrics: tuple[tuple[CanonicalToken, float | None], ...] = ()

    @property
    def completed(self) -> bool:
        return self.terminal_state == ExperimentLifecycleState.COMPLETED.value


@dataclass(frozen=True)
class ExperimentExecutionResult:
    experiment: CanonicalToken
    lifecycle_state: ExperimentLifecycleState
    outcomes: tuple[CellExecutionOutcome, ...]
    comparison_results: tuple[ComparisonFamilyResult, ...] = ()
    execution_digest: ArtifactDigest = ""

    @property
    def cell_completion_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.completed)


class CellExecutor(Protocol):
    def execute_cell(
        self, cell: ScientificCell, config: ScientificConfig
    ) -> CellExecutionOutcome: ...


class ExecutionRecordStore:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    def _record_directory(self, experiment: CanonicalToken) -> Path:
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
        )
        digest = hashlib.sha256(canonical_bytes(outcome.cell.semantic_key)).hexdigest()
        (directory / f"{digest}.json").write_text(record.model_dump_json(indent=2))

    def read_outcome(
        self, experiment: CanonicalToken, semantic_key: CanonicalToken
    ) -> PersistedExecutionRecord | None:
        digest = hashlib.sha256(canonical_bytes(semantic_key)).hexdigest()
        path = self._record_directory(experiment) / f"{digest}.json"
        if not path.exists():
            return None
        return PersistedExecutionRecord.model_validate_json(path.read_text())

    def read_all_outcomes(self, experiment: CanonicalToken) -> tuple[PersistedExecutionRecord, ...]:
        directory = self._record_directory(experiment)
        if not directory.exists():
            return ()
        return tuple(
            PersistedExecutionRecord.model_validate_json(path.read_text())
            for path in sorted(directory.glob("*.json"))
        )


def comparison_results_for_experiment(
    experiment: CanonicalToken,
    dataset: DatasetId,
    outcomes: Sequence[CellExecutionOutcome],
    config: ScientificConfig,
) -> tuple[ComparisonFamilyResult, ...]:
    capability_boundary = config.claim_support_thresholds.capability_granularity_boundary
    capability_minimum = capability_boundary.false_same_capability_certification_rate_minimum
    definitions = tuple(
        definition
        for definition in build_comparison_registry(
            config.metrics_and_statistics.materiality, capability_minimum
        )
        if definition.experiment == experiment
    )
    if not definitions:
        return ()
    seed_metrics: dict[tuple[PairingKey, CanonicalToken], dict[CanonicalToken, float | None]] = {}
    for outcome in outcomes:
        pairing = PairingKey(
            dataset=dataset.value,
            experiment=experiment,
            scientific_scenario=outcome.cell.condition,
            master_seed=outcome.cell.master_seed,
        )
        seed_metrics.setdefault((pairing, outcome.cell.method), {}).update(dict(outcome.metrics))
    families: list[ComparisonFamilyResult] = []
    for family in ClaimFamily:
        family_definitions = tuple(
            definition for definition in definitions if definition.family is family
        )
        if not family_definitions:
            continue
        results: list[ComparisonResult] = []
        for definition in family_definitions:
            if definition.test_kind not in (
                ComparisonTestKind.SUPERIORITY,
                ComparisonTestKind.NON_INFERIORITY,
            ):
                raise ValueError(f"unsupported comparison test kind {definition.test_kind}")
            paired: list[float] = []
            complete_seeds = 0
            scenario = definition.scientific_scenario
            scenario_metrics: dict[MasterSeed, dict[CanonicalToken, float | None]] = {}
            for (pairing, method), values in seed_metrics.items():
                if pairing.experiment == experiment and pairing.scientific_scenario == scenario:
                    scenario_metrics.setdefault(pairing.master_seed, {})[method] = values.get(
                        definition.metric
                    )
            paired_seeds = complete_paired_seeds(
                scenario_metrics, definition.method, definition.reference, definition.metric
            )
            for seed in paired_seeds:
                seed_values = scenario_metrics.get(seed)
                if seed_values is None:
                    continue
                method_metric = seed_values.get(definition.method)
                reference_metric = seed_values.get(definition.reference)
                if method_metric is None or reference_metric is None:
                    continue
                complete_seeds += 1
                if definition.orientation is ComparisonOrientation.HIGHER_IS_BETTER:
                    paired.append(method_metric - reference_metric)
                else:
                    paired.append(reference_metric - method_metric)
            technical_completion = config.metrics_and_statistics.technical_completion
            minimum_complete_pairs = technical_completion.minimum_complete_pairs_for_claim_support
            if complete_seeds < minimum_complete_pairs:
                results.append(
                    ComparisonResult(
                        definition=definition,
                        paired_differences=tuple(paired),
                        complete_seed_count=complete_seeds,
                        mean_paired_difference=None,
                        median_paired_difference=None,
                        paired_standardized_effect=None,
                        raw_p_value=None,
                        adjusted_p_value=None,
                        confidence_interval=None,
                        materiality_passes=None,
                        comparison_state="Inconclusive Technical",
                    )
                )
                continue
            results.append(
                evaluate_comparison(
                    definition,
                    paired,
                    config.metrics_and_statistics.multiplicity,
                    config.metrics_and_statistics.bootstrap,
                    config.seeds_and_determinism.analysis_seed,
                )
            )
        families.append(
            apply_holm_adjustment(
                ComparisonFamilyResult(family, tuple(results)),
                config.metrics_and_statistics.multiplicity,
            )
        )
    return tuple(families)


def run_experiment(
    experiment: CanonicalToken,
    executor: CellExecutor,
    overwrite: bool = False,
    config_path: Path = PRODUCTION_CONFIG_PATH,
    resolved_core_complete: bool = False,
    collapse_decision_states: Sequence[tuple[CanonicalToken, bool]] | None = None,
) -> ExperimentExecutionResult:
    validate_experiment_name_is_registered(experiment)
    config = load_scientific_config(config_path)
    plan = build_plan(
        resolved_core_complete=resolved_core_complete,
        collapse_decision_states=collapse_decision_states,
    )
    validate_no_duplicate_semantic_cells(plan)
    validate_condition_vocabulary(plan)
    planned = plan.experiment(experiment)
    if planned.resolved_core_dependent and not resolved_core_complete:
        return ExperimentExecutionResult(
            experiment=experiment,
            lifecycle_state=ExperimentLifecycleState.BLOCKED,
            outcomes=(),
        )
    store = ExecutionRecordStore(Path("outputs"))
    prerequisite_states: dict[CanonicalToken, ExperimentLifecycleState] = {}
    for prereq in planned.prerequisites:
        prereq_outcomes = store.read_all_outcomes(prereq)
        if prereq_outcomes and all(
            outcome.terminal_state == ExperimentLifecycleState.COMPLETED.value
            for outcome in prereq_outcomes
        ):
            prerequisite_states[prereq] = ExperimentLifecycleState.COMPLETED
        else:
            prerequisite_states[prereq] = ExperimentLifecycleState.NOT_STARTED
    validate_experiment_prerequisites_met(experiment, prerequisite_states)

    outcomes: list[CellExecutionOutcome] = []
    for cell in planned.cells:
        existing = store.read_outcome(experiment, cell.semantic_key)
        if existing is not None and not overwrite:
            outcomes.append(
                CellExecutionOutcome(
                    cell=cell,
                    terminal_state=existing.terminal_state,
                    failure=_to_failure_detail(existing.failure),
                    metrics=existing.metrics,
                )
            )
            continue
        outcome = executor.execute_cell(cell, config)
        validate_cell_phase_sequence(
            (
                ScientificCellPhase.PREPARE,
                ScientificCellPhase.PROTOCOL_EVALUATION,
                ScientificCellPhase.METRIC_AGGREGATION,
            )
        )
        terminal_phase = (
            CellPhaseState.COMPLETED
            if outcome.terminal_state == ExperimentLifecycleState.COMPLETED.value
            else CellPhaseState.FAILED
        )
        validate_cell_terminal_record(cell, terminal_phase)
        store.write_outcome(outcome)
        outcomes.append(outcome)

    comparison_results = comparison_results_for_experiment(
        experiment,
        planned.definition.dataset,
        outcomes,
        config,
    )
    lifecycle_state = derive_lifecycle_state(tuple(outcome.terminal_state for outcome in outcomes))
    completed_digest = execution_record_digest(outcomes)
    return ExperimentExecutionResult(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        outcomes=tuple(outcomes),
        comparison_results=comparison_results,
        execution_digest=completed_digest,
    )


def derive_lifecycle_state(terminal_states: Sequence[str]) -> ExperimentLifecycleState:
    if not terminal_states:
        return ExperimentLifecycleState.NOT_STARTED
    terminal_state_set = set(terminal_states)
    invalid_state = ExperimentLifecycleState.INVALID.value
    failed_state = ExperimentLifecycleState.FAILED.value
    if terminal_state_set & {invalid_state, failed_state}:
        return (
            ExperimentLifecycleState.INVALID
            if invalid_state in terminal_state_set
            else ExperimentLifecycleState.FAILED
        )
    completed_state = ExperimentLifecycleState.COMPLETED.value
    if all(state == completed_state for state in terminal_states):
        return ExperimentLifecycleState.COMPLETED
    return ExperimentLifecycleState.RUNNING


def is_terminal_experiment_state(state: ExperimentLifecycleState) -> bool:
    return state in TERMINAL_EXPERIMENT_STATES


def _to_failure_detail(failure: PersistedFailureDetail | None) -> FailureDetail | None:
    if failure is None:
        return None
    return FailureDetail(
        failure_class=failure.failure_class,
        message=failure.message,
        cell_phase=failure.cell_phase,
    )


def execution_record_digest(outcomes: Sequence[CellExecutionOutcome]) -> ArtifactDigest:
    hasher = hashlib.sha256()
    for outcome in outcomes:
        hasher.update(canonical_bytes(outcome.cell.semantic_key, outcome.terminal_state))
    return hasher.hexdigest()
