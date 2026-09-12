from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np
import torch
from sklearn.metrics import accuracy_score as _accuracy_score
from sklearn.metrics import balanced_accuracy_score as _balanced_accuracy_score
from sklearn.metrics import f1_score as _f1_score

from fedsira.config import CapabilityContractConfig, CleanOracleMaterialityConfig
from fedsira.datasets.common import (
    DatasetAdapter,
    DomainTargetMetrics,
    HeterogeneityScope,
    RealAnchor,
    Role,
    RootCauseScope,
    apply_attacker_induced_common_context,
    apply_heterogeneity_shift,
    root_cause_for_sample,
    scope_and_shift_rows,
)
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    RootCause,
)
from fedsira.domain.models import (
    ConfusionCounts,
    FalseSameCapabilityReason,
    MetricResult,
    ProposalOracleLabel,
)
from fedsira.domain.types import (
    AdmissionCount,
    AdmissionIndicatorSeries,
    ArtifactDigest,
    BinaryLabelMaskSeries,
    ClassLabel,
    CleanOracleDegradationMaterial,
    DatasetClassToken,
    DomainCount,
    DomainId,
    ExampleCount,
    FailureMessage,
    FalseCertificationCount,
    FalseSameEquivalenceCheck,
    FeatureIndex,
    FeatureName,
    FoldIndex,
    LegitimateAdmissionEligible,
    MasterSeed,
    MetricName,
    MetricObservation,
    MetricValue,
    OptionalTriggeredSampleMaskSeries,
    PredicateSatisfied,
    Probability,
    ReproductionAttemptCount,
    ReproductionOpportunityCount,
    RowCount,
    ScopedContractActive,
    TriggeredSampleMaskSeries,
    TriggerFeatureValue,
    VerifierReportCount,
)
from fedsira.evaluation.comparisons import ComparisonMetric
from fedsira.evaluation.statistics import (
    coefficient_of_variation,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    minimum_defined_domain_count,
    percentile_10_domain_target_f1,
    worst_domain_target_f1,
)
from fedsira.experiments.definitions import (
    AblationVariant,
    DescriptiveScientificMetric,
)
from fedsira.learning.model import (
    FedSIRAClassifier,
    load_flat_trainable_parameters,
    logits_for_samples,
    per_sample_cross_entropy,
)
from fedsira.protocol.capability_contract import screen_evidence_is_adequate
from fedsira.protocol.proposal import (
    ScreenDomainResult,
    ScreenLossObservation,
    candidate_free_screen_domain_predicate,
    raw_target_f1_screen_domain_decision_is_positive,
    run_proposal_screen_for_domain,
    screen_domain_decision_is_positive,
    screen_fold_index,
    unmatched_control_screen_domain_decision_is_positive,
)
from fedsira.runtime import (
    current_application_context,
    derive_uint32,
)


@dataclass(frozen=True)
class BoundaryMetricSet:
    macro_auroc: MetricResult
    macro_auprc: MetricResult
    clean_oracle_degradation_is_material: CleanOracleDegradationMaterial | None
    false_same_capability_rate: MetricResult
    false_same_capability_reason: FalseSameCapabilityReason | None
    false_same_equivalence_check: FalseSameEquivalenceCheck


class EvaluationValidationError(ValueError):
    def __init__(self, message: FailureMessage) -> None:
        super().__init__(message)
        self.message = message


def validate_metric_class_membership(
    class_tokens: Sequence[DatasetClassToken],
    target_class_token: DatasetClassToken,
    benign_class_token: DatasetClassToken,
    supported_class_tokens: Sequence[DatasetClassToken],
) -> None:
    vocabulary = frozenset(class_tokens)
    if target_class_token not in vocabulary:
        raise EvaluationValidationError(
            f"target class {target_class_token!r} is outside the metric class vocabulary"
        )
    if benign_class_token not in vocabulary:
        raise EvaluationValidationError(
            f"benign class {benign_class_token!r} is outside the metric class vocabulary"
        )
    for supported in supported_class_tokens:
        if supported not in vocabulary:
            raise EvaluationValidationError(
                f"supported class {supported!r} is outside the metric class vocabulary"
            )


def compute_confusion_counts(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    class_token: DatasetClassToken,
) -> ConfusionCounts:
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    for true_label, predicted_label in zip(true_labels, predicted_labels, strict=True):
        true_is_class = true_label == class_token
        predicted_is_class = predicted_label == class_token
        if true_is_class and predicted_is_class:
            true_positive += 1
        elif not true_is_class and predicted_is_class:
            false_positive += 1
        elif true_is_class and not predicted_is_class:
            false_negative += 1
        else:
            true_negative += 1
    return ConfusionCounts(
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        true_negative=true_negative,
    )


def compute_confusion_counts_by_class(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    class_tokens: Sequence[DatasetClassToken],
) -> Mapping[DatasetClassToken, ConfusionCounts]:
    return OrderedDict(
        (class_token, compute_confusion_counts(true_labels, predicted_labels, class_token))
        for class_token in class_tokens
    )


def accuracy(
    confusion_counts_by_class: Mapping[DatasetClassToken, ConfusionCounts],
    sample_count: ExampleCount,
) -> MetricResult:
    if sample_count == 0:
        return MetricResult(value=None, denominator=0)
    true_positive_total = sum(counts.true_positive for counts in confusion_counts_by_class.values())
    return MetricResult(value=true_positive_total / sample_count, denominator=sample_count)


def precision_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.true_positive + counts.false_positive
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=counts.true_positive / denominator, denominator=denominator)


def false_positive_rate_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.false_positive + counts.true_negative
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=counts.false_positive / denominator, denominator=denominator)


def false_negative_rate_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.false_negative + counts.true_positive
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=counts.false_negative / denominator, denominator=denominator)


def true_negative_rate_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.true_negative + counts.false_positive
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=counts.true_negative / denominator, denominator=denominator)


def f1_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = 2 * counts.true_positive + counts.false_positive + counts.false_negative
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=2 * counts.true_positive / denominator, denominator=denominator)


def _mean_of_defined_values(
    results: Mapping[DatasetClassToken, MetricResult],
) -> MetricResult:
    defined_values = [result.value for result in results.values() if result.value is not None]
    if len(defined_values) == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=sum(defined_values) / len(defined_values), denominator=len(defined_values)
    )


def macro_f1(f1_by_class: Mapping[DatasetClassToken, MetricResult]) -> MetricResult:
    return _mean_of_defined_values(f1_by_class)


def target_f1(
    confusion_counts_by_class: Mapping[DatasetClassToken, ConfusionCounts],
    target_class_token: DatasetClassToken,
) -> MetricResult:
    return f1_for_class(confusion_counts_by_class[target_class_token])


def target_capability_gain(
    target_f1_current: MetricResult, target_f1_anchor: MetricResult
) -> MetricResult:
    if target_f1_current.value is None or target_f1_anchor.value is None:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=target_f1_current.value - target_f1_anchor.value, denominator=1)


def supported_macro_f1_harm(
    supported_macro_f1_anchor: MetricResult, supported_macro_f1_current: MetricResult
) -> MetricResult:
    if supported_macro_f1_anchor.value is None or supported_macro_f1_current.value is None:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=supported_macro_f1_anchor.value - supported_macro_f1_current.value, denominator=1
    )


def benign_false_alarm_rate(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    benign_class_token: DatasetClassToken,
) -> MetricResult:
    benign_indices = [
        index for index, true_label in enumerate(true_labels) if true_label == benign_class_token
    ]
    denominator = len(benign_indices)
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    false_alarm_count = sum(
        1 for index in benign_indices if predicted_labels[index] != benign_class_token
    )
    return MetricResult(value=false_alarm_count / denominator, denominator=denominator)


def benign_false_alarm_rate_increase(
    benign_false_alarm_rate_current: MetricResult, benign_false_alarm_rate_anchor: MetricResult
) -> MetricResult:
    if (
        benign_false_alarm_rate_current.value is None
        or benign_false_alarm_rate_anchor.value is None
    ):
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=benign_false_alarm_rate_current.value - benign_false_alarm_rate_anchor.value,
        denominator=1,
    )


def attack_success_rate_within_domain(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    triggered_mask: TriggeredSampleMaskSeries,
    triggered_source_class_token: DatasetClassToken,
    benign_class_token: DatasetClassToken,
) -> MetricResult:
    paired = zip(true_labels, triggered_mask, strict=False)
    carrier_indices = [
        index
        for index, (true_label, triggered) in enumerate(paired)
        if triggered and true_label == triggered_source_class_token
    ]
    denominator = len(carrier_indices)
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    evaded_count = sum(
        1 for index in carrier_indices if predicted_labels[index] == benign_class_token
    )
    return MetricResult(value=evaded_count / denominator, denominator=denominator)


def clean_proposal_oracle_label(
    aggregate_target_f1: MetricResult,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    defined_domain_count: DomainCount,
    expected_domain_count: DomainCount,
    generic_defined_domain_fraction_minimum: Probability,
    capability_contract_config: CapabilityContractConfig,
) -> ProposalOracleLabel:
    required_domain_count = minimum_defined_domain_count(
        expected_domain_count, generic_defined_domain_fraction_minimum
    )
    if defined_domain_count < required_domain_count:
        return ProposalOracleLabel.NA
    if (
        aggregate_target_f1.value is None
        or target_f1_gain.value is None
        or supported_macro_f1_drop.value is None
        or benign_far_increase.value is None
    ):
        return ProposalOracleLabel.NA
    if (
        aggregate_target_f1.value >= capability_contract_config.target_f1_minimum
        and target_f1_gain.value >= capability_contract_config.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value
        <= capability_contract_config.supported_macro_f1_drop_maximum
        and benign_far_increase.value
        <= capability_contract_config.benign_false_alarm_rate_increase_maximum
    ):
        return ProposalOracleLabel.ORACLE_VALID
    return ProposalOracleLabel.ORACLE_INVALID


def false_launch_rate(
    false_launch_count: AdmissionCount, adequate_defined_oracle_count: DomainCount
) -> MetricResult:
    if adequate_defined_oracle_count == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=false_launch_count / adequate_defined_oracle_count,
        denominator=adequate_defined_oracle_count,
    )


def reproduction_attempt_count(
    domains_with_training_start: frozenset[DatasetClassToken],
    evidence_inadequate_domains: frozenset[DatasetClassToken],
) -> ReproductionAttemptCount:
    return len(domains_with_training_start - evidence_inadequate_domains)


def malicious_admission_rate(
    malicious_admission_indicators: AdmissionIndicatorSeries,
) -> MetricResult:
    denominator = len(malicious_admission_indicators)
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=sum(malicious_admission_indicators) / denominator, denominator=denominator
    )


def legitimate_admission_rate(
    legitimate_admission_indicators: AdmissionIndicatorSeries,
) -> MetricResult:
    denominator = len(legitimate_admission_indicators)
    if denominator == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=sum(legitimate_admission_indicators) / denominator, denominator=denominator
    )


def verifier_abstention_rate(
    abstaining_verifier_report_count: VerifierReportCount,
    assigned_verifier_report_count: VerifierReportCount,
) -> MetricResult:
    if assigned_verifier_report_count == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=abstaining_verifier_report_count / assigned_verifier_report_count,
        denominator=assigned_verifier_report_count,
    )


def reproduction_abstention_rate(
    evidence_insufficient_opportunity_count: ReproductionOpportunityCount,
    assigned_reproduction_opportunity_count: ReproductionOpportunityCount,
) -> MetricResult:
    if assigned_reproduction_opportunity_count == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=evidence_insufficient_opportunity_count / assigned_reproduction_opportunity_count,
        denominator=assigned_reproduction_opportunity_count,
    )


def dormant_admission_rate(
    dormant_admission_count: AdmissionCount, eligible_admission_count: AdmissionCount
) -> MetricResult:
    if eligible_admission_count == 0:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=dormant_admission_count / eligible_admission_count,
        denominator=eligible_admission_count,
    )


def auroc_one_vs_rest(
    true_binary: BinaryLabelMaskSeries, scores: Sequence[MetricValue]
) -> MetricResult:
    positive_count = sum(true_binary)
    negative_count = len(true_binary) - positive_count
    if positive_count == 0 or negative_count == 0:
        return MetricResult(value=None, denominator=0)
    order = sorted(range(len(scores)), key=lambda index: scores[index])
    ranks = [0.0] * len(scores)
    position = 0
    while position < len(order):
        current_score = scores[order[position]]
        tied_positions = [position]
        while position + 1 < len(order) and scores[order[position + 1]] == current_score:
            position += 1
            tied_positions.append(position)
        average_rank = sum(tied_position + 1 for tied_position in tied_positions) / len(
            tied_positions
        )
        for tied_position in tied_positions:
            ranks[order[tied_position]] = average_rank
        position += 1
    paired_ranks = zip(ranks, true_binary, strict=False)
    positive_rank_sum = sum(rank for rank, is_positive in paired_ranks if is_positive)
    area = (positive_rank_sum - positive_count * (positive_count + 1) / 2.0) / (
        positive_count * negative_count
    )
    return MetricResult(value=area, denominator=positive_count + negative_count)


def auprc_one_vs_rest(
    true_binary: BinaryLabelMaskSeries, scores: Sequence[MetricValue]
) -> MetricResult:
    positive_count = sum(true_binary)
    if positive_count == 0:
        return MetricResult(value=None, denominator=0)
    order = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    points: list[tuple[float, float]] = [(0.0, 1.0)]
    true_positive = 0
    false_positive = 0
    position = 0
    while position < len(order):
        current_score = scores[order[position]]
        while position < len(order) and scores[order[position]] == current_score:
            if true_binary[order[position]]:
                true_positive += 1
            else:
                false_positive += 1
            position += 1
        recall = true_positive / positive_count
        precision = true_positive / (true_positive + false_positive)
        points.append((recall, precision))
    area = 0.0
    for (recall_a, precision_a), (recall_b, precision_b) in zip(points, points[1:], strict=False):
        area += (recall_b - recall_a) * (precision_a + precision_b) / 2.0
    return MetricResult(value=area, denominator=positive_count)


def macro_auroc(auroc_by_class: Mapping[DatasetClassToken, MetricResult]) -> MetricResult:
    return _mean_of_defined_values(auroc_by_class)


def macro_auprc(auprc_by_class: Mapping[DatasetClassToken, MetricResult]) -> MetricResult:
    return _mean_of_defined_values(auprc_by_class)


def clean_oracle_degradation_is_material(
    target_f1_delta: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    clean_oracle_materiality_config: CleanOracleMaterialityConfig,
) -> CleanOracleDegradationMaterial:
    if (
        target_f1_delta.value is not None
        and target_f1_delta.value <= -clean_oracle_materiality_config.target_f1_decrease
    ):
        return True
    if (
        supported_macro_f1_drop.value is not None
        and supported_macro_f1_drop.value >= clean_oracle_materiality_config.supported_macro_f1_drop
    ):
        return True
    return (
        benign_far_increase.value is not None
        and benign_far_increase.value
        >= clean_oracle_materiality_config.benign_false_alarm_rate_increase
    )


def is_false_same_capability_certification(
    a_scoped_predicate_passes: PredicateSatisfied, b_scoped_predicate_passes: PredicateSatisfied
) -> FalseSameEquivalenceCheck:
    return a_scoped_predicate_passes != b_scoped_predicate_passes


def false_same_capability_certification_rate(
    false_certification_count: FalseCertificationCount,
    broad_certified_row_count: RowCount,
    is_scoped_contract: ScopedContractActive,
) -> tuple[MetricResult, FalseSameCapabilityReason | None]:
    if is_scoped_contract:
        return (
            MetricResult(value=None, denominator=0),
            FalseSameCapabilityReason.NO_CROSS_ROOT_CAUSE_EQUIVALENCE_ASSERTION,
        )
    if broad_certified_row_count == 0:
        return MetricResult(value=None, denominator=0), None
    return (
        MetricResult(
            value=false_certification_count / broad_certified_row_count,
            denominator=broad_certified_row_count,
        ),
        None,
    )


def boundary_metric_set(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    class_tokens: Sequence[DatasetClassToken],
    target_f1_delta: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    clean_oracle_materiality_config: CleanOracleMaterialityConfig,
    false_certification_count: FalseCertificationCount = 0,
    broad_certified_row_count: RowCount = 0,
    is_scoped_contract: ScopedContractActive = False,
    a_scoped_predicate_passes: PredicateSatisfied = False,
    b_scoped_predicate_passes: PredicateSatisfied = False,
) -> BoundaryMetricSet:
    auroc_by_class = OrderedDict(
        (
            token,
            auroc_one_vs_rest(
                [label == token for label in true_labels],
                [1.0 if prediction == token else 0.0 for prediction in predicted_labels],
            ),
        )
        for token in class_tokens
    )
    auprc_by_class = OrderedDict(
        (
            token,
            auprc_one_vs_rest(
                [label == token for label in true_labels],
                [1.0 if prediction == token else 0.0 for prediction in predicted_labels],
            ),
        )
        for token in class_tokens
    )
    material_degradation = clean_oracle_degradation_is_material(
        target_f1_delta,
        supported_macro_f1_drop,
        benign_far_increase,
        clean_oracle_materiality_config,
    )
    false_same_rate, reason = false_same_capability_certification_rate(
        false_certification_count, broad_certified_row_count, is_scoped_contract
    )
    false_same_equivalence = is_false_same_capability_certification(
        a_scoped_predicate_passes, b_scoped_predicate_passes
    )
    return BoundaryMetricSet(
        macro_auroc=macro_auroc(auroc_by_class),
        macro_auprc=macro_auprc(auprc_by_class),
        clean_oracle_degradation_is_material=material_degradation,
        false_same_capability_rate=false_same_rate,
        false_same_capability_reason=reason,
        false_same_equivalence_check=false_same_equivalence,
    )


def report_metric_set(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    class_tokens: Sequence[DatasetClassToken],
    target_class_token: DatasetClassToken,
    benign_class_token: DatasetClassToken,
    supported_class_tokens: Sequence[DatasetClassToken],
    anchor_target_f1: MetricResult | None = None,
    anchor_supported_macro_f1: MetricResult | None = None,
    anchor_benign_far: MetricResult | None = None,
    triggered_mask: OptionalTriggeredSampleMaskSeries = None,
    triggered_source_class_token: DatasetClassToken | None = None,
) -> tuple[tuple[MetricName, MetricResult], ...]:
    validate_metric_class_membership(
        class_tokens, target_class_token, benign_class_token, supported_class_tokens
    )
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    standard_accuracy, standard_macro_f1, standard_weighted_f1, standard_balanced_accuracy = (
        standard_classification_metrics(true_labels, predicted_labels, class_tokens)
    )
    f1_by_class = OrderedDict(
        (token, f1_for_class(counts)) for token, counts in counts_by_class.items()
    )
    supported_f1 = OrderedDict(
        (token, f1_by_class[token]) for token in supported_class_tokens if token in f1_by_class
    )
    current_target_f1 = f1_by_class.get(target_class_token) or MetricResult(
        value=None, denominator=0
    )
    current_supported_macro = macro_f1(supported_f1)
    current_benign_far = benign_false_alarm_rate(true_labels, predicted_labels, benign_class_token)
    gain = (
        target_capability_gain(current_target_f1, anchor_target_f1)
        if anchor_target_f1 is not None
        else MetricResult(value=None, denominator=0)
    )
    supported_harm = (
        supported_macro_f1_harm(anchor_supported_macro_f1, current_supported_macro)
        if anchor_supported_macro_f1 is not None
        else MetricResult(value=None, denominator=0)
    )
    benign_far_increase = (
        MetricResult(value=current_benign_far.value - anchor_benign_far.value, denominator=1)
        if anchor_benign_far is not None
        and current_benign_far.value is not None
        and anchor_benign_far.value is not None
        else MetricResult(value=None, denominator=0)
    )
    asr = (
        attack_success_rate_within_domain(
            true_labels,
            predicted_labels,
            triggered_mask,
            triggered_source_class_token or target_class_token,
            benign_class_token,
        )
        if triggered_mask is not None
        else MetricResult(value=None, denominator=0)
    )
    class_metrics: list[tuple[MetricName, MetricResult]] = []
    for token, counts in counts_by_class.items():
        class_metrics.append((f"{token}:precision", precision_for_class(counts)))
        class_metrics.append((f"{token}:fpr", false_positive_rate_for_class(counts)))
        class_metrics.append((f"{token}:fnr", false_negative_rate_for_class(counts)))
        class_metrics.append((f"{token}:tnr", true_negative_rate_for_class(counts)))
    return (
        ("accuracy", standard_accuracy),
        ("macro-f1", standard_macro_f1),
        ("weighted-f1", standard_weighted_f1),
        ("balanced-accuracy", standard_balanced_accuracy),
        (ComparisonMetric.TARGET_F1.value, current_target_f1),
        ("target-f1-gain", gain),
        (ComparisonMetric.SUPPORTED_MACRO_F1_HARM.value, supported_harm),
        (ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE.value, benign_far_increase),
        (ComparisonMetric.ATTACK_SUCCESS_RATE.value, asr),
        ("verifier-abstention-rate", verifier_abstention_rate(0, 0)),
        ("reproduction-abstention-rate", reproduction_abstention_rate(0, 0)),
        *class_metrics,
    )


def metric_value(
    metrics: Sequence[tuple[MetricName, MetricResult]],
    name: MetricName,
) -> MetricResult:
    for metric_name, result in metrics:
        if metric_name == name:
            return result
    raise KeyError(f"no metric named {name!r}")


_accuracy_score_typed = cast(Callable[..., float], _accuracy_score)
_balanced_accuracy_score_typed = cast(Callable[..., float], _balanced_accuracy_score)
_f1_score_typed = cast(Callable[..., float], _f1_score)


def standard_classification_metrics(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    class_tokens: Sequence[DatasetClassToken],
) -> tuple[MetricResult, MetricResult, MetricResult, MetricResult]:
    if not true_labels:
        undefined = MetricResult(value=None, denominator=0)
        return undefined, undefined, undefined, undefined
    labels = tuple(class_tokens)
    counts = tuple(
        ConfusionCounts(
            true_positive=sum(
                true == token and predicted == token
                for true, predicted in zip(true_labels, predicted_labels, strict=True)
            ),
            false_positive=sum(
                true != token and predicted == token
                for true, predicted in zip(true_labels, predicted_labels, strict=True)
            ),
            false_negative=sum(
                true == token and predicted != token
                for true, predicted in zip(true_labels, predicted_labels, strict=True)
            ),
            true_negative=sum(
                true != token and predicted != token
                for true, predicted in zip(true_labels, predicted_labels, strict=True)
            ),
        )
        for token in labels
    )
    f1_denominator = sum(
        item.true_positive + item.false_positive + item.false_negative > 0 for item in counts
    )
    recall_denominator = sum(item.true_positive + item.false_negative > 0 for item in counts)
    macro = (
        None
        if f1_denominator == 0
        else _f1_score_typed(
            true_labels, predicted_labels, labels=labels, average="macro", zero_division=np.nan
        )
    )
    weighted = _f1_score_typed(
        true_labels, predicted_labels, labels=labels, average="weighted", zero_division=np.nan
    )
    balanced = (
        None
        if recall_denominator == 0
        else _balanced_accuracy_score_typed(true_labels, predicted_labels)
    )
    return (
        MetricResult(
            value=_accuracy_score_typed(true_labels, predicted_labels), denominator=len(true_labels)
        ),
        MetricResult(value=macro, denominator=f1_denominator),
        MetricResult(value=weighted, denominator=len(true_labels)),
        MetricResult(value=balanced, denominator=recall_denominator),
    )


def evaluate_domain(
    adapter: DatasetAdapter,
    anchor: RealAnchor,
    flat_parameters: torch.Tensor,
    domain: DomainId,
    role: Role,
    target_role: Role | None = None,
    root_cause_scope: RootCauseScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> DomainTargetMetrics | None:
    true_labels: list[ClassLabel] = []
    predicted_labels: list[ClassLabel] = []
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, flat_parameters)
    model.eval()
    with torch.no_grad():
        for class_id in adapter.class_tokens:
            row_role = (
                target_role
                if target_role is not None and class_id == adapter.target_class_token
                else role
            )
            rows = adapter.load_rows(domain, class_id, row_role)
            if (
                class_id == adapter.target_class_token
                and root_cause_scope is not None
                and rows is not None
            ):
                rows = scope_and_shift_rows(rows, root_cause_scope)
            if rows is not None and heterogeneity_scope is not None:
                rows = apply_heterogeneity_shift(rows, domain, heterogeneity_scope)
            tensor_rows = adapter.tensor_view(rows)
            if tensor_rows is None:
                continue
            features, _labels, _sample_ids = tensor_rows
            predictions = torch.argmax(logits_for_samples(model, features), dim=-1)
            predicted_cpu = predictions.detach().cpu()
            prediction_indices = tuple(
                int(predicted_cpu[index].item()) for index in range(predicted_cpu.numel())
            )
            true_labels.extend(class_id for _ in range(features.shape[0]))
            predicted_labels.extend(adapter.class_tokens[index] for index in prediction_indices)
    if not true_labels:
        return None
    class_tokens = tuple(adapter.class_tokens)
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    f1_by_class = OrderedDict(
        (token, f1_for_class(counts)) for token, counts in counts_by_class.items()
    )
    supported_tokens = tuple(token for token in class_tokens if token != adapter.target_class_token)
    supported_f1 = OrderedDict(
        (token, f1_by_class[token]) for token in supported_tokens if token in f1_by_class
    )
    report = report_metric_set(
        true_labels,
        predicted_labels,
        class_tokens,
        adapter.target_class_token,
        adapter.benign_class_token,
        supported_tokens,
    )
    return DomainTargetMetrics(
        target_f1=metric_value(report, ComparisonMetric.TARGET_F1.value),
        supported_macro_f1=macro_f1(supported_f1),
        benign_far=benign_false_alarm_rate(
            true_labels, predicted_labels, adapter.benign_class_token
        ),
    )


def non_source_domains(
    adapter: DatasetAdapter, source_domain: DomainId | None
) -> tuple[DomainId, ...]:
    return tuple(domain for domain in adapter.domain_ids if domain != source_domain)


def root_cause_partitioned_row_ids(
    adapter: DatasetAdapter, domains: Sequence[DomainId]
) -> tuple[frozenset[ArtifactDigest], frozenset[ArtifactDigest], frozenset[ArtifactDigest]]:
    root_cause_a_ids: set[ArtifactDigest] = set()
    root_cause_b_ids: set[ArtifactDigest] = set()
    supported_ids: set[ArtifactDigest] = set()
    for domain in domains:
        target_rows = adapter.load_rows(
            domain, adapter.target_class_token, Role.POST_REFERENCE_REPLAY
        )
        if target_rows is not None:
            for sample_id in target_rows.sample_ids:
                if root_cause_for_sample(sample_id) is RootCause.A:
                    root_cause_a_ids.add(sample_id)
                else:
                    root_cause_b_ids.add(sample_id)
        for class_id in adapter.class_tokens:
            if class_id == adapter.target_class_token:
                continue
            supported_rows = adapter.load_rows(domain, class_id, Role.POST_REFERENCE_REPLAY)
            if supported_rows is not None:
                supported_ids.update(supported_rows.sample_ids)
    return (frozenset(root_cause_a_ids), frozenset(root_cause_b_ids), frozenset(supported_ids))


@dataclass(frozen=True)
class RealReportSummary:
    target_f1: MetricResult
    worst_domain_target_f1: MetricResult
    p10_domain_target_f1: MetricResult
    domain_disparity: MetricResult
    domain_iqr: MetricResult
    coefficient_of_variation: MetricResult
    supported_macro_f1_harm: MetricResult
    benign_far_increase: MetricResult


def compute_real_report_summary(
    adapter: DatasetAdapter,
    anchor: RealAnchor,
    source_domain: DomainId | None,
    production_checkpoint: torch.Tensor,
) -> RealReportSummary | None:
    target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    for domain in non_source_domains(adapter, source_domain):
        anchor_metrics = evaluate_domain(
            adapter, anchor, anchor.flat_parameters, domain, Role.REPORT_TEST
        )
        production_metrics = evaluate_domain(
            adapter, anchor, production_checkpoint, domain, Role.REPORT_TEST
        )
        if anchor_metrics is None or production_metrics is None:
            continue
        target_f1_values.append(production_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, production_metrics.supported_macro_f1
            )
        )
        if (
            anchor_metrics.benign_far.value is not None
            and production_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(
                    value=production_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        else:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
    if not target_f1_values:
        return None
    target_f1_tuple = tuple(target_f1_values)
    return RealReportSummary(
        target_f1=equal_weight_domain_mean(target_f1_tuple, 1),
        worst_domain_target_f1=worst_domain_target_f1(target_f1_tuple),
        p10_domain_target_f1=percentile_10_domain_target_f1(target_f1_tuple),
        domain_disparity=domain_disparity(target_f1_tuple),
        domain_iqr=interquartile_range(target_f1_tuple),
        coefficient_of_variation=coefficient_of_variation(
            tuple(result.value for result in target_f1_tuple if result.value is not None)
        ),
        supported_macro_f1_harm=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
    )


def undefined_metric() -> MetricResult:
    return MetricResult(value=None, denominator=0)


_STATE_ENCODINGS: tuple[tuple[AdmissionState, MetricValue], ...] = (
    (AdmissionState.ADMITTED, 1.0),
    (AdmissionState.REJECTED, -1.0),
    (AdmissionState.EXPIRED, -2.0),
    (AdmissionState.DORMANT, 0.0),
)


def _state_encoding(state: AdmissionState) -> MetricValue:
    for encoded_state, encoding in _STATE_ENCODINGS:
        if encoded_state is state:
            return encoding
    return 0.0


def metrics_from_state(
    state: AdmissionState,
    real_report: RealReportSummary | None = None,
    attack_success_rate: MetricResult | None = None,
    *,
    legitimate_admission_eligible: LegitimateAdmissionEligible,
) -> tuple[MetricObservation, ...]:
    is_admitted = state is AdmissionState.ADMITTED
    is_dormant = state is AdmissionState.DORMANT
    undefined = undefined_metric()
    asr = attack_success_rate if attack_success_rate is not None else undefined
    legitimate_admission_value = (
        legitimate_admission_rate([is_admitted]).value
        if legitimate_admission_eligible
        else undefined.value
    )
    if real_report is None:
        target_f1 = undefined
        supported_macro_f1_harm_value = undefined
        benign_far_increase_value = undefined
        worst_domain = undefined
        p10_domain = undefined
        disparity = undefined
        iqr = undefined
        cv = undefined
        equal_weight_mean = undefined
    else:
        target_f1 = real_report.target_f1
        supported_macro_f1_harm_value = real_report.supported_macro_f1_harm
        benign_far_increase_value = real_report.benign_far_increase
        worst_domain = real_report.worst_domain_target_f1
        p10_domain = real_report.p10_domain_target_f1
        disparity = real_report.domain_disparity
        iqr = real_report.domain_iqr
        cv = real_report.coefficient_of_variation
        equal_weight_mean = real_report.target_f1
    return (
        ("terminal-state", _state_encoding(state)),
        (ComparisonMetric.LEGITIMATE_ADMISSION, legitimate_admission_value),
        (ComparisonMetric.TARGET_F1, target_f1.value),
        ("target-f1-gain", undefined.value),
        (ComparisonMetric.SUPPORTED_MACRO_F1_HARM, supported_macro_f1_harm_value.value),
        (ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE, benign_far_increase_value.value),
        (ComparisonMetric.ATTACK_SUCCESS_RATE, asr.value),
        ("accuracy", undefined.value),
        ("macro-f1", undefined.value),
        ("weighted-f1", undefined.value),
        ("balanced-accuracy", undefined.value),
        ("verifier-abstention-rate", undefined.value),
        ("reproduction-abstention-rate", undefined.value),
        (ComparisonMetric.WORST_DOMAIN_TARGET_F1, worst_domain.value),
        ("p10-domain-target-f1", p10_domain.value),
        ("domain-disparity", disparity.value),
        ("domain-iqr", iqr.value),
        ("coefficient-of-variation", cv.value),
        ("equal-weight-domain-mean-target-f1", equal_weight_mean.value),
        (ComparisonMetric.REPRODUCTION_ATTEMPTS, undefined.value),
        (ComparisonMetric.FALSE_LAUNCH, undefined.value),
        (ComparisonMetric.POST_EVIDENCE_OVERHEAD, undefined.value),
        (
            DescriptiveScientificMetric.DORMANT_ADMISSION_RATE.value,
            dormant_admission_rate(
                dormant_admission_count=1 if is_dormant else 0, eligible_admission_count=1
            ).value,
        ),
    )


def _screen_models(
    anchor: RealAnchor, source_delta: torch.Tensor
) -> tuple[FedSIRAClassifier, FedSIRAClassifier]:
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    source_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(source_model, anchor.flat_parameters + source_delta)
    return anchor_model, source_model


def compute_unmatched_screen_differential(
    adapter: DatasetAdapter, anchor: RealAnchor, source_delta: torch.Tensor, domain: DomainId
) -> MetricValue | None:
    target_rows = adapter.tensor_view(
        adapter.load_rows(domain, adapter.target_class_token, Role.CANDIDATE_SCREEN)
    )
    if target_rows is None:
        return None
    target_features, target_labels, _target_sample_ids = target_rows
    anchor_model, source_model = _screen_models(anchor, source_delta)
    target_anchor_loss = per_sample_cross_entropy(anchor_model, target_features, target_labels)
    target_source_loss = per_sample_cross_entropy(source_model, target_features, target_labels)
    return float(torch.mean(target_anchor_loss - target_source_loss))


def compute_screen_differential(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_delta: torch.Tensor,
    domain: DomainId,
) -> MetricValue | None:
    target_rows = adapter.tensor_view(
        adapter.load_rows(domain, adapter.target_class_token, Role.CANDIDATE_SCREEN)
    )
    if target_rows is None:
        return None
    target_features, target_labels, target_sample_ids = target_rows
    control_features_parts: list[torch.Tensor] = []
    control_labels_parts: list[torch.Tensor] = []
    control_sample_ids: list[ArtifactDigest] = []
    for class_id in adapter.class_tokens:
        if class_id == adapter.target_class_token:
            continue
        replay_rows = adapter.tensor_view(
            adapter.load_rows(domain, class_id, Role.POST_REFERENCE_REPLAY)
        )
        if replay_rows is None:
            continue
        features, labels, sample_ids = replay_rows
        control_features_parts.append(features)
        control_labels_parts.append(labels)
        control_sample_ids.extend(sample_ids)
    if not control_features_parts:
        return None
    anchor_model, source_model = _screen_models(anchor, source_delta)
    target_anchor_loss = per_sample_cross_entropy(anchor_model, target_features, target_labels)
    target_source_loss = per_sample_cross_entropy(source_model, target_features, target_labels)
    control_features = torch.cat(control_features_parts, dim=0)
    control_labels = torch.cat(control_labels_parts, dim=0)
    control_anchor_loss = per_sample_cross_entropy(anchor_model, control_features, control_labels)
    control_source_loss = per_sample_cross_entropy(source_model, control_features, control_labels)
    config = current_application_context().scientific_config
    screen_fold_seed = derive_uint32("SCREEN_FOLD_SEED", master_seed)
    fold_count = config.protocol.proposal_screen.fold_count
    fold_assignment: OrderedDict[ArtifactDigest, FoldIndex] = OrderedDict()
    target_observations: list[ScreenLossObservation] = []
    for index, sample_id in enumerate(target_sample_ids):
        fold_assignment[sample_id] = screen_fold_index(sample_id, screen_fold_seed, fold_count)
        target_observations.append(
            ScreenLossObservation(
                sample_id=sample_id,
                anchor_loss=float(target_anchor_loss[index]),
                source_loss=float(target_source_loss[index]),
            )
        )
    control_observations: list[ScreenLossObservation] = []
    for index, sample_id in enumerate(control_sample_ids):
        fold_assignment[sample_id] = screen_fold_index(sample_id, screen_fold_seed, fold_count)
        control_observations.append(
            ScreenLossObservation(
                sample_id=sample_id,
                anchor_loss=float(control_anchor_loss[index]),
                source_loss=float(control_source_loss[index]),
            )
        )
    return run_proposal_screen_for_domain(
        fold_assignment, target_observations, control_observations, fold_count
    )


def evaluate_screen_domain(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_delta: torch.Tensor | None,
    domain: DomainId,
    opening_mode: AdmissionOpeningMode,
    screen_predicate_variant: AblationVariant | None,
) -> ScreenDomainResult:
    config = current_application_context().scientific_config
    target_rows = adapter.load_rows(domain, adapter.target_class_token, Role.CANDIDATE_SCREEN)
    target_count = 0 if target_rows is None else target_rows.row_count
    if not screen_evidence_is_adequate(target_count, config.capability_contract.evidence_minima):
        return ScreenDomainResult(
            domain=domain, is_evidence_adequate=False, meets_opening_predicate=False
        )
    if opening_mode is AdmissionOpeningMode.CANDIDATE_FREE:
        anchor_screen = evaluate_domain(
            adapter,
            anchor,
            anchor.flat_parameters,
            domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        predicate = candidate_free_screen_domain_predicate(
            anchor_screen.target_f1
            if anchor_screen is not None
            else MetricResult(value=None, denominator=0),
            config.capability_contract,
        )
        return ScreenDomainResult(
            domain=domain, is_evidence_adequate=True, meets_opening_predicate=predicate
        )
    if source_delta is None:
        return ScreenDomainResult(
            domain=domain, is_evidence_adequate=True, meets_opening_predicate=False
        )
    candidate_flat = anchor.flat_parameters + source_delta
    anchor_screen = evaluate_domain(
        adapter,
        anchor,
        anchor.flat_parameters,
        domain,
        role=Role.POST_REFERENCE_REPLAY,
        target_role=Role.CANDIDATE_SCREEN,
    )
    source_screen = evaluate_domain(
        adapter,
        anchor,
        candidate_flat,
        domain,
        role=Role.POST_REFERENCE_REPLAY,
        target_role=Role.CANDIDATE_SCREEN,
    )
    if anchor_screen is None or source_screen is None:
        return ScreenDomainResult(
            domain=domain, is_evidence_adequate=True, meets_opening_predicate=False
        )
    target_f1_gain = target_capability_gain(source_screen.target_f1, anchor_screen.target_f1)
    supported_macro_f1_drop = supported_macro_f1_harm(
        anchor_screen.supported_macro_f1, source_screen.supported_macro_f1
    )
    benign_far_increase = (
        MetricResult(
            value=source_screen.benign_far.value - anchor_screen.benign_far.value,
            denominator=1,
        )
        if source_screen.benign_far.value is not None and anchor_screen.benign_far.value is not None
        else MetricResult(value=None, denominator=0)
    )
    if screen_predicate_variant is AblationVariant.RAW_TARGET_F1_SCREEN_ONLY:
        predicate = raw_target_f1_screen_domain_decision_is_positive(
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.capability_contract,
        )
    elif screen_predicate_variant is AblationVariant.NO_MATCHED_CONTROL:
        unmatched_differential = compute_unmatched_screen_differential(
            adapter, anchor, source_delta, domain
        )
        predicate = unmatched_control_screen_domain_decision_is_positive(
            unmatched_differential,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.protocol.proposal_screen,
            config.capability_contract,
        )
    else:
        differential_a = compute_screen_differential(
            adapter, master_seed, anchor, source_delta, domain
        )
        predicate = screen_domain_decision_is_positive(
            differential_a,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
            config.protocol.proposal_screen,
            config.capability_contract,
        )
    return ScreenDomainResult(
        domain=domain, is_evidence_adequate=True, meets_opening_predicate=predicate
    )


def compute_source_backdoor_asr(
    adapter: DatasetAdapter,
    anchor: RealAnchor,
    production_flat_parameters: torch.Tensor,
    source_domain: DomainId,
    trigger_feature_indices: tuple[FeatureIndex, ...],
    trigger_value: TriggerFeatureValue,
) -> MetricResult:
    rows = adapter.tensor_view(
        adapter.load_rows(source_domain, adapter.attack_carrier_class_token(), Role.REPORT_TEST)
    )
    if rows is None:
        return MetricResult(value=None, denominator=0)
    features, _labels, _sample_ids = rows
    triggered_features = features.clone()
    for feature_index in trigger_feature_indices:
        triggered_features[:, feature_index] = trigger_value
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, production_flat_parameters)
    model.eval()
    with torch.no_grad():
        predictions = torch.argmax(logits_for_samples(model, triggered_features), dim=1)
    benign_index = adapter.class_tokens.index(adapter.benign_class_token)
    asr = float((predictions == benign_index).float().mean())
    return MetricResult(value=asr, denominator=triggered_features.shape[0])


def triggered_to_benign_rate(
    adapter: DatasetAdapter,
    anchor: RealAnchor,
    flat_parameters: torch.Tensor,
    domain: DomainId,
    role: Role,
    trigger_feature_names: tuple[FeatureName, ...],
    trigger_value: TriggerFeatureValue,
) -> MetricResult:
    feature_names = adapter.feature_names()
    rows = adapter.load_rows(domain, adapter.attack_carrier_class_token(), role)
    if feature_names is None or rows is None:
        return MetricResult(value=None, denominator=0)
    trigger_indices = [feature_names.index(name) for name in trigger_feature_names]
    features = torch.tensor(rows.features, dtype=torch.float32)
    triggered_features = apply_attacker_induced_common_context(
        features, trigger_indices, trigger_value
    )
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, flat_parameters)
    model.eval()
    with torch.no_grad():
        predictions = torch.argmax(logits_for_samples(model, triggered_features), dim=-1)
    benign_index = adapter.class_tokens.index(adapter.benign_class_token)
    rate = float((predictions == benign_index).float().mean())
    return MetricResult(value=rate, denominator=len(rows.sample_ids))
