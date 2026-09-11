from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TypeAlias

import torch

from fedsira.datasets.common import (
    DatasetAdapter,
    EpistemicFailureScope,
    PreparedRows,
    RealAnchor,
    Role,
    RootCauseScope,
    mark_epistemic_rows,
    select_spurious_feature_rows,
)
from fedsira.domain.enums import (
    AdmissionState,
    CapabilityContractScope,
    DatasetId,
    EpistemicFailureType,
    EvaluationInsufficiencyReason,
    ExperimentLifecycleState,
)
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    ByteCount,
    CompleteSeedCount,
    ConditionName,
    DomainCount,
    DomainId,
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
from fedsira.evaluation.metrics import (
    evaluate_domain,
    non_source_domains,
    supported_macro_f1_harm,
)
from fedsira.evaluation.statistics import (
    diagnostic_marker_metric_or_insufficient,
    equal_weight_domain_mean,
    match_diagnostic_benign_report_test_rows,
)
from fedsira.experiments.definitions import ComparisonFamily, experiment_by_name
from fedsira.experiments.engine import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    PersistedExecutionRecord,
)
from fedsira.learning.model import (
    FedSIRAClassifier,
    load_flat_trainable_parameters,
    logits_for_samples,
    per_sample_cross_entropy,
)
from fedsira.learning.post_reference import train_domain_reproduction_delta
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


@dataclass(frozen=True)
class CapabilityUnderSpecificationSummary:
    defined_domain_count: DomainCount
    aggregate_target_f1: MetricResult
    target_f1_gain: MetricResult
    supported_macro_f1_drop: MetricResult
    benign_far_increase: MetricResult
    root_cause_a_target_f1: MetricResult
    root_cause_b_target_f1: MetricResult


def _root_cause_scoped_scope(
    root_cause_scope: RootCauseScope,
    contract_scope: CapabilityContractScope,
) -> RootCauseScope:
    return replace(root_cause_scope, contract_scope=contract_scope)


def compute_capability_under_specification_summary(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
    root_cause_scope: RootCauseScope,
) -> CapabilityUnderSpecificationSummary:
    target_f1_values: list[MetricResult] = []
    anchor_target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    root_cause_a_target_f1_values: list[MetricResult] = []
    root_cause_b_target_f1_values: list[MetricResult] = []
    a_scoped_scope = _root_cause_scoped_scope(
        root_cause_scope, CapabilityContractScope.ROOT_CAUSE_A_SCOPED
    )
    b_scoped_scope = _root_cause_scoped_scope(
        root_cause_scope, CapabilityContractScope.ROOT_CAUSE_B_SCOPED
    )
    for domain in non_source_domains(adapter, source_domain):
        delta = train_domain_reproduction_delta(
            adapter, master_seed, anchor, domain, root_cause_scope
        )
        if delta is None:
            continue
        production_flat = anchor.flat_parameters + delta
        anchor_metrics = evaluate_domain(
            adapter,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=root_cause_scope,
        )
        scoped_metrics = evaluate_domain(
            adapter,
            anchor,
            production_flat,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=root_cause_scope,
        )
        if anchor_metrics is None or scoped_metrics is None:
            continue
        target_f1_values.append(scoped_metrics.target_f1)
        anchor_target_f1_values.append(anchor_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, scoped_metrics.supported_macro_f1
            )
        )
        if anchor_metrics.benign_far.value is None or scoped_metrics.benign_far.value is None:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
        else:
            benign_far_increases.append(
                MetricResult(
                    value=scoped_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        a_scoped_metrics = evaluate_domain(
            adapter,
            anchor,
            production_flat,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=a_scoped_scope,
        )
        b_scoped_metrics = evaluate_domain(
            adapter,
            anchor,
            production_flat,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=b_scoped_scope,
        )
        if a_scoped_metrics is not None:
            root_cause_a_target_f1_values.append(a_scoped_metrics.target_f1)
        if b_scoped_metrics is not None:
            root_cause_b_target_f1_values.append(b_scoped_metrics.target_f1)
    aggregate_target_f1 = equal_weight_domain_mean(tuple(target_f1_values), 1)
    anchor_target_f1 = equal_weight_domain_mean(tuple(anchor_target_f1_values), 1)
    target_f1_gain = (
        MetricResult(value=aggregate_target_f1.value - anchor_target_f1.value, denominator=1)
        if aggregate_target_f1.value is not None and anchor_target_f1.value is not None
        else MetricResult(value=None, denominator=0)
    )
    return CapabilityUnderSpecificationSummary(
        defined_domain_count=len(target_f1_values),
        aggregate_target_f1=aggregate_target_f1,
        target_f1_gain=target_f1_gain,
        supported_macro_f1_drop=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
        root_cause_a_target_f1=equal_weight_domain_mean(tuple(root_cause_a_target_f1_values), 1),
        root_cause_b_target_f1=equal_weight_domain_mean(tuple(root_cause_b_target_f1_values), 1),
    )


def _diagnostic_marker_for_domain(
    adapter: DatasetAdapter,
    anchor: RealAnchor,
    production_flat: torch.Tensor,
    domain: DomainId,
    scope: EpistemicFailureScope,
) -> tuple[MetricResult, EvaluationInsufficiencyReason | None]:
    target_rows = adapter.load_rows(domain, adapter.target_class_token, Role.REPORT_TEST)
    benign_rows = adapter.load_rows(domain, adapter.benign_class_token, Role.REPORT_TEST)
    if target_rows is None or benign_rows is None:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    selected_target_ids = (
        select_spurious_feature_rows(
            target_rows.sample_ids, scope.strength, scope.attack_generation_seed
        )
        or ()
    )
    if not selected_target_ids:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    target_index_by_id = OrderedDict(
        (sample_id, index) for index, sample_id in enumerate(target_rows.sample_ids)
    )
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    target_class_index = adapter.class_tokens.index(adapter.target_class_token)
    selected_target_features = torch.tensor(
        [target_rows.features[target_index_by_id[sample_id]] for sample_id in selected_target_ids],
        dtype=torch.float32,
    )
    target_confidence_labels = torch.argmax(
        logits_for_samples(anchor_model, selected_target_features), dim=-1
    )
    target_report_losses = tuple(
        zip(
            selected_target_ids,
            (
                float(value)
                for value in per_sample_cross_entropy(
                    anchor_model, selected_target_features, target_confidence_labels
                )
            ),
            strict=True,
        )
    )
    benign_features = torch.tensor(benign_rows.features, dtype=torch.float32)
    benign_confidence_labels = torch.argmax(
        logits_for_samples(anchor_model, benign_features), dim=-1
    )
    benign_report_losses = tuple(
        zip(
            benign_rows.sample_ids,
            (
                float(value)
                for value in per_sample_cross_entropy(
                    anchor_model, benign_features, benign_confidence_labels
                )
            ),
            strict=True,
        )
    )
    matched_pairs = match_diagnostic_benign_report_test_rows(
        target_report_losses, benign_report_losses
    )
    if matched_pairs is None:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    matched_benign_ids = tuple(benign_id for _target_id, benign_id in matched_pairs)
    benign_index_by_id = OrderedDict(
        (sample_id, index) for index, sample_id in enumerate(benign_rows.sample_ids)
    )
    matched_benign_rows = PreparedRows(
        sample_ids=matched_benign_ids,
        features=tuple(
            benign_rows.features[benign_index_by_id[sample_id]] for sample_id in matched_benign_ids
        ),
        labels=tuple(adapter.benign_class_token for _ in matched_benign_ids),
    )
    marked_rows = mark_epistemic_rows(matched_benign_rows, scope, frozenset(matched_benign_ids))
    production_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(production_model, production_flat)
    production_model.eval()
    with torch.no_grad():
        marked_features = torch.tensor(marked_rows.features, dtype=torch.float32)
        predictions = torch.argmax(logits_for_samples(production_model, marked_features), dim=-1)
    marker_rate = float((predictions == target_class_index).float().mean())
    return diagnostic_marker_metric_or_insufficient(matched_pairs, marker_rate)


@dataclass(frozen=True)
class SharedEpistemicFailureSummary:
    defined_domain_count: DomainCount
    aggregate_target_f1: MetricResult
    target_f1_gain: MetricResult
    supported_macro_f1_drop: MetricResult
    benign_far_increase: MetricResult
    diagnostic_marker: MetricResult


def compute_shared_epistemic_failure_summary(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId | None,
    epistemic_failure_scope: EpistemicFailureScope,
) -> SharedEpistemicFailureSummary:
    target_f1_values: list[MetricResult] = []
    anchor_target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    diagnostic_markers: list[MetricResult] = []
    has_diagnostic_marker = epistemic_failure_scope.failure_type in (
        EpistemicFailureType.SHARED_SPURIOUS_FEATURE,
        EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT,
    )
    for domain in non_source_domains(adapter, source_domain):
        delta = train_domain_reproduction_delta(
            adapter,
            master_seed,
            anchor,
            domain,
            epistemic_failure_scope=epistemic_failure_scope,
        )
        if delta is None:
            continue
        production_flat = anchor.flat_parameters + delta
        anchor_metrics = evaluate_domain(
            adapter, anchor, anchor.flat_parameters, domain, Role.REPORT_TEST
        )
        production_metrics = evaluate_domain(
            adapter, anchor, production_flat, domain, Role.REPORT_TEST
        )
        if anchor_metrics is None or production_metrics is None:
            continue
        target_f1_values.append(production_metrics.target_f1)
        anchor_target_f1_values.append(anchor_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, production_metrics.supported_macro_f1
            )
        )
        if anchor_metrics.benign_far.value is None or production_metrics.benign_far.value is None:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
        else:
            benign_far_increases.append(
                MetricResult(
                    value=production_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        if has_diagnostic_marker:
            marker_result, _reason = _diagnostic_marker_for_domain(
                adapter, anchor, production_flat, domain, epistemic_failure_scope
            )
            diagnostic_markers.append(marker_result)
    aggregate_target_f1 = equal_weight_domain_mean(tuple(target_f1_values), 1)
    anchor_target_f1 = equal_weight_domain_mean(tuple(anchor_target_f1_values), 1)
    target_f1_gain = (
        MetricResult(value=aggregate_target_f1.value - anchor_target_f1.value, denominator=1)
        if aggregate_target_f1.value is not None and anchor_target_f1.value is not None
        else MetricResult(value=None, denominator=0)
    )
    return SharedEpistemicFailureSummary(
        defined_domain_count=len(target_f1_values),
        aggregate_target_f1=aggregate_target_f1,
        target_f1_gain=target_f1_gain,
        supported_macro_f1_drop=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
        diagnostic_marker=equal_weight_domain_mean(tuple(diagnostic_markers), 1),
    )
