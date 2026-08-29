from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fedsira.analysis.comparisons import (
    ComparisonDefinition,
    ComparisonEffectScale,
    ComparisonFamilyResult,
    ComparisonOrientation,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
    ComparisonTestKind,
    apply_holm_adjustment,
    build_comparison_registry,
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
from fedsira.domain.records import (
    ArtifactDigest,
    CellCompletionStatus,
    CollapseDecisionPassed,
    CompleteSeedCount,
    ExecutionSchemaVersion,
    ExperimentName,
    FailureMessage,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricDifference,
    MetricName,
    MetricObservation,
    MetricValue,
    MinimumCompletePairCount,
    OverwriteExisting,
    PairedDifference,
    ResolvedCoreComplete,
    ScenarioName,
    ScientificCellCount,
    ScientificCellSemanticKey,
    TerminalExperimentState,
)
from fedsira.experiments.collapse import CollapseEvaluationInput
from fedsira.experiments.planning import ScientificCell, build_plan
from fedsira.experiments.registry import (
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    ClaimFamily,
    ExternalVerificationCondition,
    OpeningMode,
    PluralityCondition,
    PrimaryScenario,
    ProposalEpisode,
    SourceExclusionMethod,
    experiment_by_name,
)
from fedsira.experiments.validation import (
    validate_cell_phase_sequence,
    validate_cell_terminal_record,
    validate_condition_vocabulary,
    validate_experiment_name_is_registered,
    validate_experiment_prerequisites_met,
    validate_no_duplicate_semantic_cells,
)
from fedsira.runtime.determinism import framed_bytes
from fedsira.runtime.state import FailureDetail

EXECUTION_RECORD_SCHEMA_VERSION: ExecutionSchemaVersion = "fedsira|execution_record|1"

TERMINAL_EXPERIMENT_STATES = frozenset(
    {
        ExperimentLifecycleState.COMPLETED,
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
    }
)


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


@dataclass(frozen=True)
class CellExecutionOutcome:
    cell: ScientificCell
    terminal_state: ExperimentLifecycleState
    failure: FailureDetail | None
    metrics: tuple[MetricObservation, ...] = ()

    @property
    def completed(self) -> CellCompletionStatus:
        return self.terminal_state is ExperimentLifecycleState.COMPLETED


@dataclass(frozen=True)
class ExperimentExecutionResult:
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    outcomes: tuple[CellExecutionOutcome, ...]
    comparison_results: tuple[ComparisonFamilyResult, ...] = ()
    execution_digest: ArtifactDigest | None = None

    @property
    def cell_completion_count(self) -> ScientificCellCount:
        return sum(1 for outcome in self.outcomes if outcome.completed)


class CellExecutor(Protocol):
    def execute_cell(
        self, cell: ScientificCell, config: ScientificConfig
    ) -> CellExecutionOutcome: ...


class ExecutionRecordStore:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

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
        )
        digest = hashlib.sha256(framed_bytes(outcome.cell.semantic_key)).hexdigest()
        (directory / f"{digest}.json").write_text(record.model_dump_json(indent=2))

    def read_outcome(
        self, experiment: ExperimentName, semantic_key: ScientificCellSemanticKey
    ) -> PersistedExecutionRecord | None:
        digest = hashlib.sha256(framed_bytes(semantic_key)).hexdigest()
        path = self._record_directory(experiment) / f"{digest}.json"
        if not path.exists():
            return None
        return PersistedExecutionRecord.model_validate_json(path.read_text())

    def read_all_outcomes(
        self, experiment: ExperimentName
    ) -> tuple[PersistedExecutionRecord, ...]:
        directory = self._record_directory(experiment)
        if not directory.exists():
            return ()
        return tuple(
            PersistedExecutionRecord.model_validate_json(path.read_text())
            for path in sorted(directory.glob("*.json"))
        )


class MetricCellKey(FrozenDomainModel):
    dataset: DatasetId
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    master_seed: MasterSeed
    method: MethodName


MetricIndex = dict[MetricCellKey, dict[MetricName, MetricValue | None]]


def _metric_index_from_outcomes(
    dataset: DatasetId,
    outcomes: Sequence[CellExecutionOutcome],
) -> MetricIndex:
    index: MetricIndex = {}
    for outcome in outcomes:
        key = MetricCellKey(
            dataset=dataset,
            experiment=outcome.cell.experiment,
            scientific_scenario=outcome.cell.condition,
            master_seed=outcome.cell.master_seed,
            method=outcome.cell.method,
        )
        index.setdefault(key, {}).update(dict(outcome.metrics))
    return index


def _extend_index_from_records(
    index: MetricIndex,
    dataset: DatasetId,
    records: Sequence[PersistedExecutionRecord],
) -> None:
    for record in records:
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        key = MetricCellKey(
            dataset=dataset,
            experiment=record.experiment,
            scientific_scenario=record.condition,
            master_seed=record.master_seed,
            method=record.method,
        )
        index.setdefault(key, {}).update(dict(record.metrics))


def _metric_value(
    index: Mapping[MetricCellKey, Mapping[MetricName, MetricValue | None]],
    key: MetricCellKey,
    metric: MetricName,
) -> MetricValue | None:
    values = index.get(key)
    return None if values is None else values.get(metric)


def _benefit_difference(
    orientation: ComparisonOrientation,
    effect_scale: ComparisonEffectScale,
    method_value: MetricValue,
    reference_value: MetricValue,
) -> PairedDifference | None:
    if effect_scale is ComparisonEffectScale.RELATIVE_REFERENCE_REDUCTION:
        if orientation is not ComparisonOrientation.LOWER_IS_BETTER:
            raise ValueError("relative reduction is defined only for lower-is-better metrics")
        if reference_value == 0.0:
            return None
        return (reference_value - method_value) / reference_value
    if orientation is ComparisonOrientation.HIGHER_IS_BETTER:
        return method_value - reference_value
    return reference_value - method_value


def _comparison_pairs(
    definition: ComparisonDefinition,
    dataset: DatasetId,
    metric_index: Mapping[MetricCellKey, Mapping[MetricName, MetricValue | None]],
    master_seeds: Sequence[MasterSeed],
) -> tuple[PairedDifference, ...]:
    paired: list[PairedDifference] = []
    for seed in master_seeds:
        method_key = MetricCellKey(
            dataset=dataset,
            experiment=definition.experiment,
            scientific_scenario=definition.scientific_scenario,
            master_seed=seed,
            method=definition.method,
        )
        method_value = _metric_value(metric_index, method_key, definition.metric.value)
        if method_value is None:
            continue
        if definition.reference_kind is ComparisonReferenceKind.ZERO:
            reference_value: MetricValue | None = 0.0
        else:
            reference_key = MetricCellKey(
                dataset=dataset,
                experiment=definition.reference_experiment,
                scientific_scenario=definition.reference_scenario,
                master_seed=seed,
                method=definition.reference_method,
            )
            reference_value = _metric_value(
                metric_index,
                reference_key,
                definition.metric.value,
            )
        if reference_value is None:
            continue
        difference = _benefit_difference(
            definition.orientation,
            definition.effect_scale,
            method_value,
            reference_value,
        )
        if difference is not None:
            paired.append(difference)
    return tuple(paired)


def comparison_results_for_experiment(
    experiment: ExperimentName,
    dataset: DatasetId,
    outcomes: Sequence[CellExecutionOutcome],
    config: ScientificConfig,
    store: ExecutionRecordStore | None = None,
) -> tuple[ComparisonFamilyResult, ...]:
    definitions = tuple(
        definition
        for definition in build_comparison_registry(config)
        if definition.experiment == experiment
    )
    if not definitions:
        return ()

    execution_store = store or ExecutionRecordStore(
        Path(config.runtime.repository_layout.execution_workspace)
    )
    metric_index = _metric_index_from_outcomes(dataset, outcomes)
    reference_experiments = {
        definition.reference_experiment
        for definition in definitions
        if definition.reference_kind is ComparisonReferenceKind.SCIENTIFIC_CELL
        and definition.reference_experiment != experiment
    }
    for reference_experiment in sorted(reference_experiments):
        reference_definition = experiment_by_name(reference_experiment)
        if reference_definition.dataset is not dataset:
            raise ValueError(
                f"comparison reference {reference_experiment} uses "
                f"{reference_definition.dataset.value}, expected {dataset.value}"
            )
        _extend_index_from_records(
            metric_index,
            dataset,
            execution_store.read_all_outcomes(reference_experiment),
        )

    minimum_complete_pairs = (
        config.metrics_and_statistics.technical_completion
        .minimum_complete_pairs_for_claim_support
    )
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
                raise ValueError(
                    f"unsupported comparison test kind {definition.test_kind}"
                )
            paired = _comparison_pairs(
                definition,
                dataset,
                metric_index,
                config.seeds_and_determinism.master_seeds,
            )
            complete_seeds: CompleteSeedCount = len(paired)
            if complete_seeds < minimum_complete_pairs:
                state = (
                    ComparisonState.UNDEFINED
                    if complete_seeds == 0
                    else ComparisonState.INCONCLUSIVE_TECHNICAL
                )
                results.append(
                    ComparisonResult(
                        definition=definition,
                        paired_differences=paired,
                        complete_seed_count=complete_seeds,
                        mean_paired_difference=None,
                        median_paired_difference=None,
                        paired_standardized_effect=None,
                        raw_p_value=None,
                        adjusted_p_value=None,
                        confidence_interval=None,
                        materiality_passes=None,
                        comparison_state=state,
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
                ComparisonFamilyResult(family=family, comparisons=tuple(results)),
                config.metrics_and_statistics.multiplicity,
            )
        )
    return tuple(families)


def _record_metric(
    record: PersistedExecutionRecord,
    metric: MetricName,
) -> MetricValue | None:
    return dict(record.metrics).get(metric)


def _paired_constraint_means(
    records: Sequence[PersistedExecutionRecord],
    method: MethodName,
    reference: MethodName,
    conditions: Sequence[ScenarioName],
    metric: MetricName,
    *,
    orientation: ComparisonOrientation,
    minimum_complete_pairs: MinimumCompletePairCount,
) -> tuple[MetricDifference, ...] | None:
    means: list[MetricDifference] = []
    for condition in conditions:
        by_seed: dict[MasterSeed, dict[MethodName, MetricValue | None]] = {}
        for record in records:
            if (
                record.terminal_state is ExperimentLifecycleState.COMPLETED
                and record.condition == condition
                and record.method in (method, reference)
            ):
                by_seed.setdefault(record.master_seed, {})[record.method] = _record_metric(
                    record,
                    metric,
                )
        differences: list[MetricDifference] = []
        for values in by_seed.values():
            method_value = values.get(method)
            reference_value = values.get(reference)
            if method_value is None or reference_value is None:
                continue
            differences.append(
                method_value - reference_value
                if orientation is ComparisonOrientation.LOWER_IS_BETTER
                else reference_value - method_value
            )
        if len(differences) < minimum_complete_pairs:
            return None
        means.append(sum(differences) / len(differences))
    return tuple(means)


def _maximum_constraint(
    values: tuple[MetricDifference, ...] | None,
) -> MetricDifference | None:
    return None if values is None else max(values)


def collapse_evaluation_from_store(
    store: ExecutionRecordStore,
    config: ScientificConfig,
) -> CollapseEvaluationInput:
    minimum = (
        config.metrics_and_statistics.technical_completion
        .minimum_complete_pairs_for_claim_support
    )

    proposal_records = store.read_all_outcomes(
        PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME
    )
    proposal_lar = _maximum_constraint(
        _paired_constraint_means(
            proposal_records,
            OpeningMode.PROPOSAL_ASSISTED.value,
            OpeningMode.CANDIDATE_FREE.value,
            (ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,),
            "legitimate-admission",
            orientation=ComparisonOrientation.HIGHER_IS_BETTER,
            minimum_complete_pairs=minimum,
        )
    )
    proposal_mar = _maximum_constraint(
        _paired_constraint_means(
            proposal_records,
            OpeningMode.PROPOSAL_ASSISTED.value,
            OpeningMode.CANDIDATE_FREE.value,
            (ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,),
            "malicious-admission",
            orientation=ComparisonOrientation.LOWER_IS_BETTER,
            minimum_complete_pairs=minimum,
        )
    )

    plurality_records = store.read_all_outcomes(SINGLE_REPRODUCTION_NECESSITY_NAME)
    plurality_conditions = tuple(condition.value for condition in PluralityCondition)
    plurality_lar = _maximum_constraint(
        _paired_constraint_means(
            plurality_records,
            "Full Plurality Path",
            "One Independent Retrain",
            plurality_conditions,
            "legitimate-admission",
            orientation=ComparisonOrientation.HIGHER_IS_BETTER,
            minimum_complete_pairs=minimum,
        )
    )
    plurality_supported = _maximum_constraint(
        _paired_constraint_means(
            plurality_records,
            "Full Plurality Path",
            "One Independent Retrain",
            plurality_conditions,
            "supported-macro-f1-harm",
            orientation=ComparisonOrientation.LOWER_IS_BETTER,
            minimum_complete_pairs=minimum,
        )
    )

    source_records = store.read_all_outcomes(
        SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
    )
    source_condition = (
        PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
    )
    source_target = _maximum_constraint(
        _paired_constraint_means(
            source_records,
            SourceExclusionMethod.FULL_FEDSIRA.value,
            SourceExclusionMethod.SOURCE_UPDATE_SANITIZATION_REFERENCE.value,
            source_condition,
            "target-f1",
            orientation=ComparisonOrientation.HIGHER_IS_BETTER,
            minimum_complete_pairs=minimum,
        )
    )
    source_supported = _maximum_constraint(
        _paired_constraint_means(
            source_records,
            SourceExclusionMethod.FULL_FEDSIRA.value,
            SourceExclusionMethod.SOURCE_UPDATE_SANITIZATION_REFERENCE.value,
            source_condition,
            "supported-macro-f1-harm",
            orientation=ComparisonOrientation.LOWER_IS_BETTER,
            minimum_complete_pairs=minimum,
        )
    )
    source_far = _maximum_constraint(
        _paired_constraint_means(
            source_records,
            SourceExclusionMethod.FULL_FEDSIRA.value,
            SourceExclusionMethod.SOURCE_UPDATE_SANITIZATION_REFERENCE.value,
            source_condition,
            "benign-far-increase",
            orientation=ComparisonOrientation.LOWER_IS_BETTER,
            minimum_complete_pairs=minimum,
        )
    )

    verification_records = store.read_all_outcomes(
        EXTERNAL_VERIFICATION_NECESSITY_NAME
    )
    verification_lar = _maximum_constraint(
        _paired_constraint_means(
            verification_records,
            SourceExclusionMethod.FULL_FEDSIRA.value,
            "Multiple Retrains with Direct Krum",
            (
                ExternalVerificationCondition.LEGITIMATE_TRANSFERABLE_CAPABILITY.value,
            ),
            "legitimate-admission",
            orientation=ComparisonOrientation.HIGHER_IS_BETTER,
            minimum_complete_pairs=minimum,
        )
    )

    return CollapseEvaluationInput(
        proposal_legitimate_admission_degradation=proposal_lar,
        proposal_malicious_admission_worsening=proposal_mar,
        plurality_legitimate_admission_degradation=plurality_lar,
        plurality_supported_harm=plurality_supported,
        source_exclusion_target_f1_drop=source_target,
        source_exclusion_supported_harm=source_supported,
        source_exclusion_benign_far_increase=source_far,
        external_verification_legitimate_admission_degradation=verification_lar,
    )


def run_experiment(
    experiment: ExperimentName,
    executor: CellExecutor,
    overwrite: OverwriteExisting = False,
    config_path: Path = PRODUCTION_CONFIG_PATH,
    resolved_core_complete: ResolvedCoreComplete = False,
    collapse_decision_states: Sequence[
        tuple[ExperimentName, CollapseDecisionPassed]
    ]
    | None = None,
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

    store = ExecutionRecordStore(
        Path(config.runtime.repository_layout.execution_workspace)
    )
    prerequisite_states: dict[ExperimentName, ExperimentLifecycleState] = {}
    for prerequisite in planned.prerequisites:
        prerequisite_outcomes = store.read_all_outcomes(prerequisite)
        if prerequisite_outcomes and all(
            outcome.terminal_state is ExperimentLifecycleState.COMPLETED
            for outcome in prerequisite_outcomes
        ):
            prerequisite_states[prerequisite] = ExperimentLifecycleState.COMPLETED
        else:
            prerequisite_states[prerequisite] = ExperimentLifecycleState.NOT_STARTED
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
            if outcome.terminal_state is ExperimentLifecycleState.COMPLETED
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
        store,
    )
    lifecycle_state = derive_lifecycle_state(
        tuple(outcome.terminal_state for outcome in outcomes)
    )
    completed_digest = execution_record_digest(outcomes)
    return ExperimentExecutionResult(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        outcomes=tuple(outcomes),
        comparison_results=comparison_results,
        execution_digest=completed_digest,
    )


def derive_lifecycle_state(
    terminal_states: Sequence[ExperimentLifecycleState],
) -> ExperimentLifecycleState:
    if not terminal_states:
        return ExperimentLifecycleState.NOT_STARTED
    terminal_state_set = set(terminal_states)
    invalid_state = ExperimentLifecycleState.INVALID
    failed_state = ExperimentLifecycleState.FAILED
    if terminal_state_set & {invalid_state, failed_state}:
        return (
            ExperimentLifecycleState.INVALID
            if invalid_state in terminal_state_set
            else ExperimentLifecycleState.FAILED
        )
    completed_state = ExperimentLifecycleState.COMPLETED
    if all(state == completed_state for state in terminal_states):
        return ExperimentLifecycleState.COMPLETED
    return ExperimentLifecycleState.RUNNING


def is_terminal_experiment_state(
    state: ExperimentLifecycleState,
) -> TerminalExperimentState:
    return state in TERMINAL_EXPERIMENT_STATES


def _to_failure_detail(
    failure: PersistedFailureDetail | None,
) -> FailureDetail | None:
    if failure is None:
        return None
    return FailureDetail(
        failure_class=failure.failure_class,
        message=failure.message,
        cell_phase=failure.cell_phase,
    )


def execution_record_digest(
    outcomes: Sequence[CellExecutionOutcome],
) -> ArtifactDigest:
    hasher = hashlib.sha256()
    for outcome in outcomes:
        hasher.update(
            framed_bytes(
                outcome.cell.semantic_key,
                outcome.terminal_state.value,
            )
        )
    return hasher.hexdigest()
