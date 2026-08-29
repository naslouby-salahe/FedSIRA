from __future__ import annotations

import hashlib
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
    ExperimentPrerequisiteState,
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
    (
        ExperimentLifecycleState.COMPLETED,
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
    )
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


class CellExecutionOutcome(FrozenDomainModel):
    cell: ScientificCell
    terminal_state: ExperimentLifecycleState
    failure: FailureDetail | None
    metrics: tuple[MetricObservation, ...] = ()

    @property
    def completed(self) -> CellCompletionStatus:
        return self.terminal_state is ExperimentLifecycleState.COMPLETED


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
    def execute_cell(
        self,
        cell: ScientificCell,
        config: ScientificConfig,
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
        self,
        experiment: ExperimentName,
        semantic_key: ScientificCellSemanticKey,
    ) -> PersistedExecutionRecord | None:
        digest = hashlib.sha256(framed_bytes(semantic_key)).hexdigest()
        path = self._record_directory(experiment) / f"{digest}.json"
        if not path.exists():
            return None
        record = PersistedExecutionRecord.model_validate_json(path.read_text())
        if record.semantic_key != semantic_key or record.experiment != experiment:
            raise ValueError("persisted execution record identity mismatch")
        return record

    def read_all_outcomes(
        self,
        experiment: ExperimentName,
    ) -> tuple[PersistedExecutionRecord, ...]:
        directory = self._record_directory(experiment)
        if not directory.exists():
            return ()
        records = tuple(
            PersistedExecutionRecord.model_validate_json(path.read_text())
            for path in sorted(directory.glob("*.json"))
        )
        for record in records:
            if record.experiment != experiment:
                raise ValueError("persisted execution record experiment mismatch")
        return records


class MetricCellKey(FrozenDomainModel):
    dataset: DatasetId
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    master_seed: MasterSeed
    method: MethodName


class MetricCellRecord(FrozenDomainModel):
    key: MetricCellKey
    metrics: tuple[MetricObservation, ...]


class ExperimentExecutionDigestInput(FrozenDomainModel):
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    semantic_keys: tuple[ScientificCellSemanticKey, ...]


def _merge_metric_record(
    records: tuple[MetricCellRecord, ...],
    incoming: MetricCellRecord,
) -> tuple[MetricCellRecord, ...]:
    retained = tuple(record for record in records if record.key != incoming.key)
    return (*retained, incoming)


def _metric_value(
    records: tuple[MetricCellRecord, ...],
    key: MetricCellKey,
    metric: MetricName,
) -> MetricValue | None:
    for record in reversed(records):
        if record.key != key:
            continue
        for metric_name, metric_value in reversed(record.metrics):
            if metric_name == metric:
                return metric_value
    return None


def _metric_index_from_outcomes(
    dataset: DatasetId,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[MetricCellRecord, ...]:
    records: tuple[MetricCellRecord, ...] = ()
    for outcome in outcomes:
        if outcome.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        record = MetricCellRecord(
            key=MetricCellKey(
                dataset=dataset,
                experiment=outcome.cell.experiment,
                scientific_scenario=outcome.cell.condition,
                master_seed=outcome.cell.master_seed,
                method=outcome.cell.method,
            ),
            metrics=outcome.metrics,
        )
        records = _merge_metric_record(records, record)
    return records


def _extend_index_from_records(
    records: tuple[MetricCellRecord, ...],
    dataset: DatasetId,
    persisted_records: tuple[PersistedExecutionRecord, ...],
) -> tuple[MetricCellRecord, ...]:
    merged = records
    for record in persisted_records:
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        merged = _merge_metric_record(
            merged,
            MetricCellRecord(
                key=MetricCellKey(
                    dataset=dataset,
                    experiment=record.experiment,
                    scientific_scenario=record.condition,
                    master_seed=record.master_seed,
                    method=record.method,
                ),
                metrics=record.metrics,
            ),
        )
    return merged


def _benefit_difference(
    orientation: ComparisonOrientation,
    effect_scale: ComparisonEffectScale,
    method_value: MetricValue,
    reference_value: MetricValue,
) -> PairedDifference | None:
    absolute_difference = (
        method_value - reference_value
        if orientation is ComparisonOrientation.HIGHER_IS_BETTER
        else reference_value - method_value
    )
    if effect_scale is ComparisonEffectScale.ABSOLUTE:
        return absolute_difference
    if reference_value == 0.0:
        return None
    return absolute_difference / abs(reference_value)


def _comparison_pairs(
    definition: ComparisonDefinition,
    dataset: DatasetId,
    metric_index: tuple[MetricCellRecord, ...],
    master_seeds: tuple[MasterSeed, ...],
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
    outcomes: tuple[CellExecutionOutcome, ...],
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
    reference_experiments = frozenset(
        definition.reference_experiment
        for definition in definitions
        if definition.reference_kind is ComparisonReferenceKind.SCIENTIFIC_CELL
        and definition.reference_experiment != experiment
    )
    for reference_experiment in sorted(reference_experiments):
        reference_definition = experiment_by_name(reference_experiment)
        if reference_definition.dataset is not dataset:
            raise ValueError(
                f"comparison reference {reference_experiment} uses "
                f"{reference_definition.dataset.value}, expected {dataset.value}"
            )
        metric_index = _extend_index_from_records(
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
    for metric_name, metric_value in reversed(record.metrics):
        if metric_name == metric:
            return metric_value
    return None


def _record_metric_for_seed_and_method(
    records: tuple[PersistedExecutionRecord, ...],
    condition: ScenarioName,
    master_seed: MasterSeed,
    method: MethodName,
    metric: MetricName,
) -> MetricValue | None:
    for record in reversed(records):
        if (
            record.terminal_state is ExperimentLifecycleState.COMPLETED
            and record.condition == condition
            and record.master_seed == master_seed
            and record.method == method
        ):
            return _record_metric(record, metric)
    return None


def _paired_constraint_means(
    records: tuple[PersistedExecutionRecord, ...],
    method: MethodName,
    reference: MethodName,
    conditions: tuple[ScenarioName, ...],
    metric: MetricName,
    *,
    orientation: ComparisonOrientation,
    minimum_complete_pairs: MinimumCompletePairCount,
) -> tuple[MetricDifference, ...] | None:
    means: list[MetricDifference] = []
    for condition in conditions:
        seeds = tuple(
            sorted(
                frozenset(
                    record.master_seed
                    for record in records
                    if record.terminal_state is ExperimentLifecycleState.COMPLETED
                    and record.condition == condition
                    and record.method in (method, reference)
                )
            )
        )
        differences: list[MetricDifference] = []
        for seed in seeds:
            method_value = _record_metric_for_seed_and_method(
                records,
                condition,
                seed,
                method,
                metric,
            )
            reference_value = _record_metric_for_seed_and_method(
                records,
                condition,
                seed,
                reference,
                metric,
            )
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


def collapse_evaluation_from_records(
    experiment: ExperimentName,
    records: tuple[PersistedExecutionRecord, ...],
    config: ScientificConfig,
) -> CollapseEvaluationInput | None:
    minimum_pairs = (
        config.metrics_and_statistics.technical_completion
        .minimum_complete_pairs_for_claim_support
    )
    if experiment == PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME:
        legitimate = _maximum_constraint(
            _paired_constraint_means(
                records,
                OpeningMode.PROPOSAL_ASSISTED.value,
                OpeningMode.CANDIDATE_FREE.value,
                (ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,),
                ComparisonMetric.LEGITIMATE_ADMISSION.value,
                orientation=ComparisonOrientation.HIGHER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        malicious = _maximum_constraint(
            _paired_constraint_means(
                records,
                OpeningMode.PROPOSAL_ASSISTED.value,
                OpeningMode.CANDIDATE_FREE.value,
                (ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,),
                ComparisonMetric.MALICIOUS_ADMISSION.value,
                orientation=ComparisonOrientation.LOWER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        return CollapseEvaluationInput(
            proposal_legitimate_admission_degradation=legitimate,
            proposal_malicious_admission_worsening=malicious,
            plurality_legitimate_admission_degradation=None,
            plurality_supported_harm=None,
            source_exclusion_target_f1_drop=None,
            source_exclusion_supported_harm=None,
            source_exclusion_benign_far_increase=None,
            external_verification_legitimate_admission_degradation=None,
        )
    if experiment == SINGLE_REPRODUCTION_NECESSITY_NAME:
        conditions = tuple(condition.value for condition in PluralityCondition)
        legitimate = _maximum_constraint(
            _paired_constraint_means(
                records,
                "Full Plurality Path",
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                conditions,
                ComparisonMetric.LEGITIMATE_ADMISSION.value,
                orientation=ComparisonOrientation.HIGHER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        supported = _maximum_constraint(
            _paired_constraint_means(
                records,
                "Full Plurality Path",
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                conditions,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM.value,
                orientation=ComparisonOrientation.LOWER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        return CollapseEvaluationInput(
            proposal_legitimate_admission_degradation=None,
            proposal_malicious_admission_worsening=None,
            plurality_legitimate_admission_degradation=legitimate,
            plurality_supported_harm=supported,
            source_exclusion_target_f1_drop=None,
            source_exclusion_supported_harm=None,
            source_exclusion_benign_far_increase=None,
            external_verification_legitimate_admission_degradation=None,
        )
    if experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
        conditions = (PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,)
        method = SourceExclusionMethod.FULL_FEDSIRA.value
        reference = BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value
        target = _maximum_constraint(
            _paired_constraint_means(
                records,
                method,
                reference,
                conditions,
                ComparisonMetric.TARGET_F1.value,
                orientation=ComparisonOrientation.HIGHER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        supported = _maximum_constraint(
            _paired_constraint_means(
                records,
                method,
                reference,
                conditions,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM.value,
                orientation=ComparisonOrientation.LOWER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        benign = _maximum_constraint(
            _paired_constraint_means(
                records,
                method,
                reference,
                conditions,
                ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE.value,
                orientation=ComparisonOrientation.LOWER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        return CollapseEvaluationInput(
            proposal_legitimate_admission_degradation=None,
            proposal_malicious_admission_worsening=None,
            plurality_legitimate_admission_degradation=None,
            plurality_supported_harm=None,
            source_exclusion_target_f1_drop=target,
            source_exclusion_supported_harm=supported,
            source_exclusion_benign_far_increase=benign,
            external_verification_legitimate_admission_degradation=None,
        )
    if experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME:
        legitimate = _maximum_constraint(
            _paired_constraint_means(
                records,
                SourceExclusionMethod.FULL_FEDSIRA.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
                (ExternalVerificationCondition.LEGITIMATE_TRANSFERABLE_CAPABILITY.value,),
                ComparisonMetric.LEGITIMATE_ADMISSION.value,
                orientation=ComparisonOrientation.HIGHER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        return CollapseEvaluationInput(
            proposal_legitimate_admission_degradation=None,
            proposal_malicious_admission_worsening=None,
            plurality_legitimate_admission_degradation=None,
            plurality_supported_harm=None,
            source_exclusion_target_f1_drop=None,
            source_exclusion_supported_harm=None,
            source_exclusion_benign_far_increase=None,
            external_verification_legitimate_admission_degradation=legitimate,
        )
    return None


def _digest_execution_result(
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


def _execute_cell_with_retry(
    cell: ScientificCell,
    config: ScientificConfig,
    executor: CellExecutor,
) -> CellExecutionOutcome:
    attempts = config.runtime.automatic_infrastructure_retries_per_cell_phase + 1
    last_outcome: CellExecutionOutcome | None = None
    for _attempt in range(attempts):
        outcome = executor.execute_cell(cell, config)
        validate_cell_terminal_record(outcome.terminal_state, outcome.failure)
        if outcome.terminal_state is not ExperimentLifecycleState.FAILED:
            return outcome
        last_outcome = outcome
    if last_outcome is None:
        raise RuntimeError("cell retry loop produced no outcome")
    return last_outcome


def execute_experiment(
    experiment: ExperimentName,
    executor: CellExecutor,
    *,
    config: ScientificConfig | None = None,
    overwrite: OverwriteExisting = False,
    prerequisite_states: tuple[ExperimentPrerequisiteState, ...] | None = None,
) -> ExperimentExecutionResult:
    resolved_config = config or load_scientific_config(PRODUCTION_CONFIG_PATH)
    definition = experiment_by_name(experiment)
    validate_experiment_name_is_registered(experiment)
    validate_condition_vocabulary(experiment, definition.conditions)
    states = prerequisite_states or tuple(
        ExperimentPrerequisiteState(
            experiment=prerequisite,
            state=ExperimentLifecycleState.COMPLETED,
        )
        for prerequisite in definition.prerequisites
    )
    validate_experiment_prerequisites_met(definition.prerequisites, states)
    plan = build_plan(experiment, resolved_config)
    validate_no_duplicate_semantic_cells(plan.cells)
    store = ExecutionRecordStore(
        Path(resolved_config.runtime.repository_layout.execution_workspace)
    )
    outcomes: list[CellExecutionOutcome] = []
    for cell in plan.cells:
        existing = store.read_outcome(experiment, cell.semantic_key)
        if existing is not None and not overwrite:
            outcomes.append(
                CellExecutionOutcome(
                    cell=cell,
                    terminal_state=existing.terminal_state,
                    failure=(
                        None
                        if existing.failure is None
                        else FailureDetail(
                            failure_class=existing.failure.failure_class,
                            message=existing.failure.message,
                            cell_phase=existing.failure.cell_phase,
                        )
                    ),
                    metrics=existing.metrics,
                )
            )
            continue
        outcome = _execute_cell_with_retry(cell, resolved_config, executor)
        store.write_outcome(outcome)
        outcomes.append(outcome)
    outcome_tuple = tuple(outcomes)
    lifecycle_state = (
        ExperimentLifecycleState.COMPLETED
        if all(outcome.completed for outcome in outcome_tuple)
        else ExperimentLifecycleState.FAILED
    )
    comparison_results = comparison_results_for_experiment(
        experiment,
        definition.dataset,
        outcome_tuple,
        resolved_config,
        store,
    )
    return ExperimentExecutionResult(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        outcomes=outcome_tuple,
        comparison_results=comparison_results,
        execution_digest=_digest_execution_result(
            experiment,
            lifecycle_state,
            outcome_tuple,
        ),
    )


def execution_completed(
    result: ExperimentExecutionResult,
) -> TerminalExperimentState:
    return result.lifecycle_state in TERMINAL_EXPERIMENT_STATES


def collapse_decision_passed(
    result: ExperimentExecutionResult,
) -> CollapseDecisionPassed:
    return result.lifecycle_state is ExperimentLifecycleState.COMPLETED


def resolved_core_complete(
    result: ExperimentExecutionResult,
) -> ResolvedCoreComplete:
    return result.lifecycle_state is ExperimentLifecycleState.COMPLETED


def execution_phase_sequence_is_valid(
    phases: tuple[CellPhaseState, ...],
) -> CellCompletionStatus:
    return validate_cell_phase_sequence(phases)
