from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from fedsira.domain.enums import AdmissionState, DatasetId, ExperimentLifecycleState
from fedsira.domain.types import (
    ByteCount,
    CompleteSeedCount,
    ConditionName,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricName,
    MetricObservation,
    MetricValue,
    ModelTransmissionCount,
    PairedDifference,
    PeakMemoryBytes,
    RepetitionIndex,
    ScenarioName,
    ScientificCellSemanticKey,
    WallClockSeconds,
)
from fedsira.evaluation.comparisons import (
    ComparisonDefinition,
    ComparisonEffectScale,
    ComparisonFamilyResult,
    ComparisonOrientation,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
    apply_holm_adjustment,
    build_comparison_registry,
    evaluate_comparison,
)
from fedsira.experiments.definitions import ComparisonFamily, experiment_by_name
from fedsira.experiments.engine import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    PersistedExecutionRecord,
)
from fedsira.runtime import (
    CudaIntervalTimer,
    ElapsedTimer,
    current_application_context,
    peak_gpu_memory_bytes,
    peak_host_resident_set_bytes,
    reset_peak_gpu_memory_counter,
)


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
        method_value = metric_value(metric_index, method_key, definition.metric.value)
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
            reference_value = metric_value(metric_index, reference_key, definition.metric.value)
        if reference_value is None:
            continue
        difference = _benefit_difference(
            definition.orientation, definition.effect_scale, method_value, reference_value
        )
        if difference is not None:
            paired.append(difference)
    return tuple(paired)


def comparison_results_for_experiment(
    experiment: ExperimentName,
    dataset: DatasetId,
    outcomes: tuple[CellExecutionOutcome, ...],
    store: ExecutionRecordStore | None = None,
) -> tuple[ComparisonFamilyResult, ...]:
    config = current_application_context().scientific_config
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.experiment == experiment
    )
    if not definitions:
        return ()
    execution_store = store or ExecutionRecordStore(
        Path(config.execution.repository_layout.execution_workspace)
    )
    metric_index = metric_index_from_outcomes(dataset, outcomes)
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
        metric_index = extend_index_from_records(
            metric_index, dataset, execution_store.read_all_outcomes(reference_experiment)
        )
    minimum_complete_pairs = (
        config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_inference
    )
    families: list[ComparisonFamilyResult] = []
    for family in ComparisonFamily:
        family_definitions = tuple(
            definition for definition in definitions if definition.family is family
        )
        if not family_definitions:
            continue
        results: list[ComparisonResult] = []
        for definition in family_definitions:
            paired = _comparison_pairs(
                definition, dataset, metric_index, config.seeds_and_determinism.master_seeds
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


class MetricCellKey(FrozenDomainModel):
    dataset: DatasetId
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    master_seed: MasterSeed
    method: MethodName


class MetricCellRecord(FrozenDomainModel):
    key: MetricCellKey
    metrics: tuple[MetricObservation, ...]


def merge_metric_record(
    records: tuple[MetricCellRecord, ...], incoming: MetricCellRecord
) -> tuple[MetricCellRecord, ...]:
    retained = tuple(record for record in records if record.key != incoming.key)
    return (*retained, incoming)


def metric_value(
    records: tuple[MetricCellRecord, ...], key: MetricCellKey, metric: MetricName
) -> MetricValue | None:
    for record in reversed(records):
        if record.key != key:
            continue
        for metric_name, metric_result in reversed(record.metrics):
            if metric_name == metric:
                return metric_result
    return None


def metric_index_from_outcomes(
    dataset: DatasetId, outcomes: tuple[CellExecutionOutcome, ...]
) -> tuple[MetricCellRecord, ...]:
    records: tuple[MetricCellRecord, ...] = ()
    for outcome in outcomes:
        if outcome.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        records = merge_metric_record(
            records,
            MetricCellRecord(
                key=MetricCellKey(
                    dataset=dataset,
                    experiment=outcome.cell.experiment,
                    scientific_scenario=outcome.cell.condition,
                    master_seed=outcome.cell.master_seed,
                    method=outcome.cell.method,
                ),
                metrics=outcome.metrics,
            ),
        )
    return records


def extend_index_from_records(
    records: tuple[MetricCellRecord, ...],
    dataset: DatasetId,
    persisted_records: tuple[PersistedExecutionRecord, ...],
) -> tuple[MetricCellRecord, ...]:
    merged = records
    for record in persisted_records:
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        merged = merge_metric_record(
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


class TimingRepetitionObservation(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ConditionName
    master_seed: MasterSeed
    repetition: RepetitionIndex
    semantic_key: ScientificCellSemanticKey
    wall_clock_seconds: WallClockSeconds
    gpu_seconds: WallClockSeconds
    peak_gpu_memory_bytes: PeakMemoryBytes
    peak_host_rss_bytes: PeakMemoryBytes
    communication_bytes: ByteCount
    model_transmissions: ModelTransmissionCount


@dataclass(frozen=True)
class TimingWorkerObservation:
    value: tuple[AdmissionState, ByteCount, ByteCount]
    wall_clock_seconds: MetricValue
    gpu_seconds: MetricValue
    peak_gpu_memory_bytes: PeakMemoryBytes
    peak_host_rss_bytes: PeakMemoryBytes


TimingWorkerResult: TypeAlias = tuple[AdmissionState, ByteCount, ByteCount]


class SingleProcessTimingWorker:
    def measure(
        self,
        action: Callable[[], TimingWorkerResult],
    ) -> TimingWorkerObservation:
        reset_peak_gpu_memory_counter()
        timer = ElapsedTimer()
        gpu_timer = CudaIntervalTimer()
        gpu_timer.start()
        state, communication_bytes_total, transmissions = action()
        gpu_seconds = gpu_timer.elapsed_seconds()
        return TimingWorkerObservation(
            value=(state, communication_bytes_total, transmissions),
            wall_clock_seconds=timer.elapsed_seconds(),
            gpu_seconds=gpu_seconds,
            peak_gpu_memory_bytes=int(peak_gpu_memory_bytes()),
            peak_host_rss_bytes=int(peak_host_resident_set_bytes()),
        )
