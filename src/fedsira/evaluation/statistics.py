import itertools
import math
from collections.abc import Callable, Sequence
from typing import TypeAlias, cast

import numpy
from statsmodels.stats.multitest import (
    multipletests as _multipletests,
)

from fedsira.config import BootstrapConfig
from fedsira.domain.enums import EvaluationInsufficiencyReason
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    ArtifactDigest,
    ComparisonMargin,
    ComparisonName,
    ConfidenceIntervalBound,
    DecileBinIndex,
    DomainCount,
    MasterSeed,
    MatchedControlCount,
    MetricValue,
    MinimumDefinedDomainCount,
    PairedDifference,
    Probability,
    PValue,
    SampleId,
    ScreenLoss,
    Sign,
    SignFlipSampleCount,
)
from fedsira.runtime import current_application_context

SignFlipSign: TypeAlias = Sign
SignFlipAssignment: TypeAlias = tuple[SignFlipSign, ...]
NamedPValue: TypeAlias = tuple[ComparisonName, PValue]
_multipletests_typed = cast(
    Callable[..., tuple[tuple[bool, ...], tuple[float, ...], float, float]],
    _multipletests,
)


def enumerate_sign_flip_assignments(
    sample_count: SignFlipSampleCount,
) -> tuple[SignFlipAssignment, ...]:
    return tuple(itertools.product((1, -1), repeat=sample_count))


def _signed_mean(
    signs: SignFlipAssignment,
    differences: tuple[PairedDifference, ...],
) -> PairedDifference:
    paired = zip(signs, differences, strict=True)
    return sum(sign * difference for sign, difference in paired) / len(differences)


def exact_sign_flip_two_sided_p_value(
    paired_differences: tuple[PairedDifference, ...],
) -> PValue:
    sample_count = len(paired_differences)
    observed_absolute_mean = abs(sum(paired_differences) / sample_count)
    assignments = enumerate_sign_flip_assignments(sample_count)
    extreme_count = sum(
        1
        for signs in assignments
        if abs(_signed_mean(signs, paired_differences)) >= observed_absolute_mean
    )
    return extreme_count / len(assignments)


def exact_sign_flip_non_inferiority_p_value(
    paired_differences: tuple[PairedDifference, ...],
    margin: ComparisonMargin,
) -> PValue:
    shifted_differences = tuple(difference + margin for difference in paired_differences)
    sample_count = len(shifted_differences)
    observed_mean = sum(shifted_differences) / sample_count
    assignments = enumerate_sign_flip_assignments(sample_count)
    extreme_count = sum(
        1 for signs in assignments if _signed_mean(signs, shifted_differences) >= observed_mean
    )
    return extreme_count / len(assignments)


def holm_adjusted_p_values(
    named_raw_p_values: tuple[NamedPValue, ...],
) -> tuple[NamedPValue, ...]:
    ordered = sorted(named_raw_p_values, key=lambda item: (item[1], item[0]))
    if not ordered:
        return ()
    _rejected, adjusted_p_values, _sidak, _bonferroni = _multipletests_typed(
        tuple(raw_p_value for _name, raw_p_value in ordered),
        method="holm",
    )
    return tuple(
        (name, float(adjusted))
        for (name, _), adjusted in zip(ordered, adjusted_p_values, strict=True)
    )


def minimum_defined_domain_count(
    expected_domain_count: DomainCount,
    generic_defined_domain_fraction_minimum: Probability,
) -> MinimumDefinedDomainCount:
    return math.ceil(expected_domain_count * generic_defined_domain_fraction_minimum)


def quantile_type7(
    sorted_values: tuple[MetricValue, ...],
    probability: Probability,
) -> MetricValue:
    if not sorted_values:
        raise ValueError("quantile requires at least one value")
    return float(numpy.quantile(sorted_values, probability, method="linear"))


def decile_boundaries(
    boundary_values: tuple[MetricValue, ...],
) -> tuple[MetricValue, ...]:
    sorted_values = tuple(sorted(boundary_values))
    return tuple(quantile_type7(sorted_values, decile / 10.0) for decile in range(1, 10))


def decile_bin(
    value: MetricValue,
    boundaries: tuple[MetricValue, ...],
) -> DecileBinIndex:
    bin_index: DecileBinIndex = 0
    for boundary in boundaries:
        if value <= boundary:
            break
        bin_index += 1
    return bin_index


def _candidate_pool(
    candidates: tuple[tuple[SampleId, MetricValue], ...],
    boundaries: tuple[MetricValue, ...],
    target_loss: MetricValue,
) -> tuple[tuple[SampleId, MetricValue], ...]:
    target_bin = decile_bin(target_loss, boundaries)
    return tuple(
        candidate for candidate in candidates if decile_bin(candidate[1], boundaries) == target_bin
    )


def match_nearest_within_decile(
    targets: tuple[tuple[SampleId, MetricValue], ...],
    candidates: tuple[tuple[SampleId, MetricValue], ...],
    boundary_values: tuple[MetricValue, ...],
    matched_controls_per_target: MatchedControlCount,
) -> tuple[tuple[SampleId, SampleId], ...] | None:
    if not boundary_values:
        return None
    boundaries = decile_boundaries(boundary_values)
    remaining = tuple(sorted(candidates, key=lambda item: item[0]))
    matches: list[tuple[SampleId, SampleId]] = []
    for target_id, target_loss in sorted(targets, key=lambda item: item[0]):
        pool = _candidate_pool(remaining, boundaries, target_loss)
        if len(pool) < matched_controls_per_target:
            return None
        nearest = sorted(pool, key=lambda item: (abs(item[1] - target_loss), item[0]))[
            :matched_controls_per_target
        ]
        matched_ids = frozenset(candidate[0] for candidate in nearest)
        remaining = tuple(candidate for candidate in remaining if candidate[0] not in matched_ids)
        matches.extend(
            (target_id, control_id)
            for _loss, control_id in ((candidate[1], candidate[0]) for candidate in nearest)
        )
    return tuple(matches)


def equal_weight_domain_mean(
    domain_results: tuple[MetricResult, ...],
    minimum_defined_domains: DomainCount,
) -> MetricResult:
    defined_values = tuple(result.value for result in domain_results if result.value is not None)
    if len(defined_values) < minimum_defined_domains:
        return MetricResult(value=None, denominator=len(defined_values))
    return MetricResult(
        value=sum(defined_values) / len(defined_values),
        denominator=len(defined_values),
    )


def worst_domain_target_f1(domain_target_f1: tuple[MetricResult, ...]) -> MetricResult:
    defined_values = tuple(result.value for result in domain_target_f1 if result.value is not None)
    if not defined_values:
        return MetricResult(value=None, denominator=0)
    return MetricResult(value=min(defined_values), denominator=len(defined_values))


def percentile_10_domain_target_f1(
    domain_target_f1: tuple[MetricResult, ...],
) -> MetricResult:
    defined_values = tuple(
        sorted(result.value for result in domain_target_f1 if result.value is not None)
    )
    if not defined_values:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=quantile_type7(defined_values, 0.10),
        denominator=len(defined_values),
    )


def domain_disparity(domain_target_f1: tuple[MetricResult, ...]) -> MetricResult:
    defined_values = tuple(result.value for result in domain_target_f1 if result.value is not None)
    if not defined_values:
        return MetricResult(value=None, denominator=0)
    return MetricResult(
        value=max(defined_values) - min(defined_values),
        denominator=len(defined_values),
    )


def interquartile_range(domain_target_f1: tuple[MetricResult, ...]) -> MetricResult:
    defined_values = tuple(
        sorted(result.value for result in domain_target_f1 if result.value is not None)
    )
    if not defined_values:
        return MetricResult(value=None, denominator=0)
    upper_quartile = quantile_type7(defined_values, 0.75)
    lower_quartile = quantile_type7(defined_values, 0.25)
    return MetricResult(
        value=upper_quartile - lower_quartile,
        denominator=len(defined_values),
    )


def coefficient_of_variation(values: tuple[MetricValue, ...]) -> MetricResult:
    minimum_dispersion_sample_count = 2
    if len(values) < minimum_dispersion_sample_count:
        return MetricResult(value=None, denominator=len(values))
    mean = sum(values) / len(values)
    if mean == 0:
        return MetricResult(value=None, denominator=len(values))
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    standard_deviation = math.sqrt(variance)
    return MetricResult(value=standard_deviation / mean, denominator=len(values))


def bootstrap_percentile_confidence_interval(
    seed_level_values: tuple[MetricValue, ...],
    bootstrap_config: BootstrapConfig,
    analysis_seed: MasterSeed,
) -> tuple[ConfidenceIntervalBound, ConfidenceIntervalBound] | None:
    if not seed_level_values:
        return None
    generator = numpy.random.default_rng(analysis_seed)
    values = numpy.asarray(seed_level_values, dtype=numpy.float64)
    sample_size = len(values)
    indices = generator.integers(
        0,
        sample_size,
        size=(bootstrap_config.resamples, sample_size),
    )
    resampled_means = values[indices].mean(axis=1)
    sorted_means = tuple(float(value) for value in numpy.sort(resampled_means))
    lower_probability = (1.0 - bootstrap_config.confidence_level) / 2.0
    upper_probability = 1.0 - lower_probability
    return (
        quantile_type7(sorted_means, lower_probability),
        quantile_type7(sorted_means, upper_probability),
    )


def match_diagnostic_benign_report_test_rows(
    target_report_losses: Sequence[tuple[ArtifactDigest, ScreenLoss]],
    benign_report_test_losses: Sequence[tuple[ArtifactDigest, ScreenLoss]],
) -> tuple[tuple[ArtifactDigest, ArtifactDigest], ...] | None:
    boundary_values = tuple(loss for _, loss in benign_report_test_losses)
    return match_nearest_within_decile(
        tuple(target_report_losses),
        tuple(benign_report_test_losses),
        boundary_values,
        current_application_context().scientific_config.protocol.proposal_screen.matched_controls_per_target,
    )


def diagnostic_marker_metric_or_insufficient(
    matched_pairs: tuple[tuple[ArtifactDigest, ArtifactDigest], ...] | None,
    marker_value: MetricValue,
) -> tuple[MetricResult, EvaluationInsufficiencyReason | None]:
    if matched_pairs is None:
        return (
            MetricResult(value=None, denominator=0),
            EvaluationInsufficiencyReason.INSUFFICIENT_MATCHED_BENIGN_REPORT_TEST_CONTROLS,
        )
    return MetricResult(value=marker_value, denominator=len(matched_pairs)), None
