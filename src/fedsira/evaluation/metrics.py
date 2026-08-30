from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fedsira.config.schema import CapabilityClaimConfig, CleanOracleMaterialityConfig
from fedsira.domain.records import DatasetClassToken, NonNegativeInt, PositiveInt, Probability
from fedsira.evaluation.aggregation import minimum_defined_domain_count
from fedsira.evaluation.records import (
    ConfusionCounts,
    FalseSameCapabilityReason,
    MetricResult,
    ProposalOracleLabel,
)
from fedsira.evaluation.validation import validate_metric_class_membership


@dataclass(frozen=True)
class BoundaryMetricSet:
    macro_auroc: MetricResult
    macro_auprc: MetricResult
    clean_oracle_degradation_is_material: bool | None
    false_same_capability_rate: MetricResult
    false_same_capability_reason: FalseSameCapabilityReason | None
    false_same_equivalence_check: bool


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
    return ConfusionCounts(true_positive, false_positive, false_negative, true_negative)


def compute_confusion_counts_by_class(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    class_tokens: Sequence[DatasetClassToken],
) -> dict[DatasetClassToken, ConfusionCounts]:
    return {
        class_token: compute_confusion_counts(true_labels, predicted_labels, class_token)
        for class_token in class_tokens
    }


def accuracy(
    confusion_counts_by_class: Mapping[DatasetClassToken, ConfusionCounts],
    sample_count: NonNegativeInt,
) -> MetricResult:
    if sample_count == 0:
        return MetricResult(None, 0)
    true_positive_total = sum(counts.true_positive for counts in confusion_counts_by_class.values())
    return MetricResult(true_positive_total / sample_count, sample_count)


def precision_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.true_positive + counts.false_positive
    if denominator == 0:
        return MetricResult(None, 0)
    return MetricResult(counts.true_positive / denominator, denominator)


def recall_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.true_positive + counts.false_negative
    if denominator == 0:
        return MetricResult(None, 0)
    return MetricResult(counts.true_positive / denominator, denominator)


def false_positive_rate_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.false_positive + counts.true_negative
    if denominator == 0:
        return MetricResult(None, 0)
    return MetricResult(counts.false_positive / denominator, denominator)


def false_negative_rate_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.false_negative + counts.true_positive
    if denominator == 0:
        return MetricResult(None, 0)
    return MetricResult(counts.false_negative / denominator, denominator)


def true_negative_rate_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = counts.true_negative + counts.false_positive
    if denominator == 0:
        return MetricResult(None, 0)
    return MetricResult(counts.true_negative / denominator, denominator)


def f1_for_class(counts: ConfusionCounts) -> MetricResult:
    denominator = 2 * counts.true_positive + counts.false_positive + counts.false_negative
    if denominator == 0:
        return MetricResult(None, 0)
    return MetricResult(2 * counts.true_positive / denominator, denominator)


def _mean_of_defined_values(
    results: Mapping[DatasetClassToken, MetricResult],
) -> MetricResult:
    defined_values = [result.value for result in results.values() if result.value is not None]
    if len(defined_values) == 0:
        return MetricResult(None, 0)
    return MetricResult(sum(defined_values) / len(defined_values), len(defined_values))


def balanced_accuracy(recall_by_class: Mapping[DatasetClassToken, MetricResult]) -> MetricResult:
    return _mean_of_defined_values(recall_by_class)


def macro_f1(f1_by_class: Mapping[DatasetClassToken, MetricResult]) -> MetricResult:
    return _mean_of_defined_values(f1_by_class)


def weighted_f1(
    f1_by_class: Mapping[DatasetClassToken, MetricResult],
    support_by_class: Mapping[DatasetClassToken, NonNegativeInt],
) -> MetricResult:
    weighted_sum = 0.0
    total_support = 0
    for class_token, f1_result in f1_by_class.items():
        if f1_result.value is None:
            continue
        support = support_by_class[class_token]
        weighted_sum += support * f1_result.value
        total_support += support
    if total_support == 0:
        return MetricResult(None, 0)
    return MetricResult(weighted_sum / total_support, total_support)


def target_f1(
    confusion_counts_by_class: Mapping[DatasetClassToken, ConfusionCounts],
    target_class_token: DatasetClassToken,
) -> MetricResult:
    return f1_for_class(confusion_counts_by_class[target_class_token])


def target_capability_gain(
    target_f1_current: MetricResult, target_f1_anchor: MetricResult
) -> MetricResult:
    if target_f1_current.value is None or target_f1_anchor.value is None:
        return MetricResult(None, 0)
    return MetricResult(target_f1_current.value - target_f1_anchor.value, 1)


def supported_macro_f1_harm(
    supported_macro_f1_anchor: MetricResult, supported_macro_f1_current: MetricResult
) -> MetricResult:
    if supported_macro_f1_anchor.value is None or supported_macro_f1_current.value is None:
        return MetricResult(None, 0)
    return MetricResult(supported_macro_f1_anchor.value - supported_macro_f1_current.value, 1)


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
        return MetricResult(None, 0)
    false_alarm_count = sum(
        1 for index in benign_indices if predicted_labels[index] != benign_class_token
    )
    return MetricResult(false_alarm_count / denominator, denominator)


def benign_false_alarm_rate_increase(
    benign_false_alarm_rate_current: MetricResult, benign_false_alarm_rate_anchor: MetricResult
) -> MetricResult:
    if (
        benign_false_alarm_rate_current.value is None
        or benign_false_alarm_rate_anchor.value is None
    ):
        return MetricResult(None, 0)
    return MetricResult(
        benign_false_alarm_rate_current.value - benign_false_alarm_rate_anchor.value, 1
    )


def attack_success_rate_within_domain(
    true_labels: Sequence[DatasetClassToken],
    predicted_labels: Sequence[DatasetClassToken],
    triggered_mask: Sequence[bool],
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
        return MetricResult(None, 0)
    evaded_count = sum(
        1 for index in carrier_indices if predicted_labels[index] == benign_class_token
    )
    return MetricResult(evaded_count / denominator, denominator)


def clean_proposal_oracle_label(
    aggregate_target_f1: MetricResult,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    defined_domain_count: NonNegativeInt,
    expected_domain_count: PositiveInt,
    generic_defined_domain_fraction_minimum: Probability,
    capability_claim_config: CapabilityClaimConfig,
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
        aggregate_target_f1.value >= capability_claim_config.target_f1_minimum
        and target_f1_gain.value >= capability_claim_config.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value <= capability_claim_config.supported_macro_f1_drop_maximum
        and benign_far_increase.value
        <= capability_claim_config.benign_false_alarm_rate_increase_maximum
    ):
        return ProposalOracleLabel.ORACLE_VALID
    return ProposalOracleLabel.ORACLE_INVALID


def false_launch_rate(
    false_launch_count: NonNegativeInt, adequate_defined_oracle_count: NonNegativeInt
) -> MetricResult:
    if adequate_defined_oracle_count == 0:
        return MetricResult(None, 0)
    return MetricResult(
        false_launch_count / adequate_defined_oracle_count, adequate_defined_oracle_count
    )


def reproduction_attempt_count(
    domains_with_training_start: frozenset[DatasetClassToken],
    evidence_inadequate_domains: frozenset[DatasetClassToken],
) -> NonNegativeInt:
    return len(domains_with_training_start - evidence_inadequate_domains)


def malicious_admission_rate(malicious_admission_indicators: Sequence[bool]) -> MetricResult:
    denominator = len(malicious_admission_indicators)
    if denominator == 0:
        return MetricResult(None, 0)
    return MetricResult(sum(malicious_admission_indicators) / denominator, denominator)


def legitimate_admission_rate(legitimate_admission_indicators: Sequence[bool]) -> MetricResult:
    denominator = len(legitimate_admission_indicators)
    if denominator == 0:
        return MetricResult(None, 0)
    return MetricResult(sum(legitimate_admission_indicators) / denominator, denominator)


def verifier_abstention_rate(
    abstaining_verifier_report_count: NonNegativeInt, assigned_verifier_report_count: NonNegativeInt
) -> MetricResult:
    if assigned_verifier_report_count == 0:
        return MetricResult(None, 0)
    return MetricResult(
        abstaining_verifier_report_count / assigned_verifier_report_count,
        assigned_verifier_report_count,
    )


def reproduction_abstention_rate(
    evidence_insufficient_opportunity_count: NonNegativeInt,
    assigned_reproduction_opportunity_count: NonNegativeInt,
) -> MetricResult:
    if assigned_reproduction_opportunity_count == 0:
        return MetricResult(None, 0)
    return MetricResult(
        evidence_insufficient_opportunity_count / assigned_reproduction_opportunity_count,
        assigned_reproduction_opportunity_count,
    )


def dormant_claim_rate(
    dormant_claim_count: NonNegativeInt, eligible_claim_count: NonNegativeInt
) -> MetricResult:
    if eligible_claim_count == 0:
        return MetricResult(None, 0)
    return MetricResult(dormant_claim_count / eligible_claim_count, eligible_claim_count)


def auroc_one_vs_rest(true_binary: Sequence[bool], scores: Sequence[float]) -> MetricResult:
    positive_count = sum(true_binary)
    negative_count = len(true_binary) - positive_count
    if positive_count == 0 or negative_count == 0:
        return MetricResult(None, 0)
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
    return MetricResult(area, positive_count + negative_count)


def auprc_one_vs_rest(true_binary: Sequence[bool], scores: Sequence[float]) -> MetricResult:
    positive_count = sum(true_binary)
    if positive_count == 0:
        return MetricResult(None, 0)
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
    return MetricResult(area, positive_count)


def macro_auroc(auroc_by_class: Mapping[DatasetClassToken, MetricResult]) -> MetricResult:
    return _mean_of_defined_values(auroc_by_class)


def macro_auprc(auprc_by_class: Mapping[DatasetClassToken, MetricResult]) -> MetricResult:
    return _mean_of_defined_values(auprc_by_class)


def clean_oracle_degradation_is_material(
    target_f1_delta: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    clean_oracle_materiality_config: CleanOracleMaterialityConfig,
) -> bool:
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
    a_scoped_predicate_passes: bool, b_scoped_predicate_passes: bool
) -> bool:
    return a_scoped_predicate_passes != b_scoped_predicate_passes


def false_same_capability_certification_rate(
    false_certification_count: NonNegativeInt,
    broad_certified_row_count: NonNegativeInt,
    is_scoped_contract: bool,
) -> tuple[MetricResult, FalseSameCapabilityReason | None]:
    if is_scoped_contract:
        return (
            MetricResult(None, 0),
            FalseSameCapabilityReason.NO_CROSS_ROOT_CAUSE_EQUIVALENCE_ASSERTION,
        )
    if broad_certified_row_count == 0:
        return MetricResult(None, 0), None
    return (
        MetricResult(
            false_certification_count / broad_certified_row_count, broad_certified_row_count
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
    false_certification_count: NonNegativeInt = 0,
    broad_certified_row_count: NonNegativeInt = 0,
    is_scoped_contract: bool = False,
    a_scoped_predicate_passes: bool = False,
    b_scoped_predicate_passes: bool = False,
) -> BoundaryMetricSet:
    auroc_by_class = {
        token: auroc_one_vs_rest(
            [label == token for label in true_labels],
            [1.0 if prediction == token else 0.0 for prediction in predicted_labels],
        )
        for token in class_tokens
    }
    auprc_by_class = {
        token: auprc_one_vs_rest(
            [label == token for label in true_labels],
            [1.0 if prediction == token else 0.0 for prediction in predicted_labels],
        )
        for token in class_tokens
    }
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
    triggered_mask: Sequence[bool] | None = None,
    triggered_source_class_token: DatasetClassToken | None = None,
) -> dict[DatasetClassToken, MetricResult]:
    validate_metric_class_membership(
        class_tokens, target_class_token, benign_class_token, supported_class_tokens
    )
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    f1_by_class = {token: f1_for_class(counts) for token, counts in counts_by_class.items()}
    recall_by_class = {token: recall_for_class(counts) for token, counts in counts_by_class.items()}
    supported_f1 = {
        token: f1_by_class[token] for token in supported_class_tokens if token in f1_by_class
    }
    current_target_f1 = f1_by_class.get(target_class_token) or MetricResult(None, 0)
    current_supported_macro = macro_f1(supported_f1)
    current_benign_far = benign_false_alarm_rate(true_labels, predicted_labels, benign_class_token)
    gain = (
        target_capability_gain(current_target_f1, anchor_target_f1)
        if anchor_target_f1 is not None
        else MetricResult(None, 0)
    )
    supported_harm = (
        supported_macro_f1_harm(anchor_supported_macro_f1, current_supported_macro)
        if anchor_supported_macro_f1 is not None
        else MetricResult(None, 0)
    )
    benign_far_increase = (
        MetricResult(current_benign_far.value - anchor_benign_far.value, 1)
        if anchor_benign_far is not None
        and current_benign_far.value is not None
        and anchor_benign_far.value is not None
        else MetricResult(None, 0)
    )
    support_by_class = {
        token: sum(1 for label in true_labels if label == token) for token in class_tokens
    }
    asr = (
        attack_success_rate_within_domain(
            true_labels,
            predicted_labels,
            triggered_mask,
            triggered_source_class_token or target_class_token,
            benign_class_token,
        )
        if triggered_mask is not None
        else MetricResult(None, 0)
    )
    class_metrics: dict[DatasetClassToken, MetricResult] = {}
    for token, counts in counts_by_class.items():
        class_metrics[f"{token}:precision"] = precision_for_class(counts)
        class_metrics[f"{token}:fpr"] = false_positive_rate_for_class(counts)
        class_metrics[f"{token}:fnr"] = false_negative_rate_for_class(counts)
        class_metrics[f"{token}:tnr"] = true_negative_rate_for_class(counts)
    return {
        "accuracy": accuracy(counts_by_class, len(true_labels)),
        "macro-f1": macro_f1(f1_by_class),
        "weighted-f1": weighted_f1(f1_by_class, support_by_class),
        "balanced-accuracy": balanced_accuracy(recall_by_class),
        "target-f1": current_target_f1,
        "target-f1-gain": gain,
        "supported-macro-f1-harm": supported_harm,
        "benign-far-increase": benign_far_increase,
        "asr": asr,
        "verifier-abstention-rate": verifier_abstention_rate(0, 0),
        "reproduction-abstention-rate": reproduction_abstention_rate(0, 0),
        **class_metrics,
    }
