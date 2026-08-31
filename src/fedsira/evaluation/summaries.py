import math

import numpy

from fedsira.config.models import BootstrapConfig
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    ConfidenceIntervalBound,
    DecileBinIndex,
    DomainCount,
    MasterSeed,
    MetricValue,
    MinimumDefinedDomainCount,
    NonNegativeInt,
    Probability,
    SampleId,
    SeedDerivationLabel,
)
from fedsira.runtime.determinism import derive_uint32

SINGLE_METHOD_MEAN_BOOTSTRAP_SEPARATOR: SeedDerivationLabel = "SINGLE_METHOD_MEAN_BOOTSTRAP"


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
    sample_count = len(sorted_values)
    if sample_count == 1:
        return sorted_values[0]
    position = (sample_count - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    fraction = position - lower_index
    return sorted_values[lower_index] + fraction * (
        sorted_values[upper_index] - sorted_values[lower_index]
    )


def decile_boundaries(
    boundary_values: tuple[MetricValue, ...],
) -> tuple[MetricValue, ...]:
    sorted_values = tuple(sorted(boundary_values))
    return tuple(quantile_type7(sorted_values, decile / 10.0) for decile in range(1, 10))


def decile_bin(
    value: MetricValue,
    boundaries: tuple[MetricValue, ...],
) -> DecileBinIndex:
    bin_index: NonNegativeInt = 0
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
) -> tuple[tuple[SampleId, SampleId], ...] | None:
    if not boundary_values:
        return None
    boundaries = decile_boundaries(boundary_values)
    remaining = tuple(sorted(candidates, key=lambda item: item[0]))
    matches: list[tuple[SampleId, SampleId]] = []
    for target_id, target_loss in sorted(targets, key=lambda item: item[0]):
        pool = _candidate_pool(remaining, boundaries, target_loss)
        if not pool:
            return None
        best = min(pool, key=lambda item: (abs(item[1] - target_loss), item[0]))
        remaining = tuple(candidate for candidate in remaining if candidate != best)
        matches.append((target_id, best[0]))
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
    if len(values) < 2:
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
    bootstrap_seed = derive_uint32(SINGLE_METHOD_MEAN_BOOTSTRAP_SEPARATOR, analysis_seed)
    generator = numpy.random.default_rng(bootstrap_seed)
    values = numpy.asarray(seed_level_values, dtype=numpy.float64)
    sample_size = len(values)
    resampled_means = numpy.empty(bootstrap_config.resamples, dtype=numpy.float64)
    for resample_index in range(bootstrap_config.resamples):
        indices = generator.integers(0, sample_size, size=sample_size)
        resampled_means[resample_index] = values[indices].mean()
    sorted_means = tuple(float(value) for value in numpy.sort(resampled_means))
    lower_probability = (1.0 - bootstrap_config.confidence_level) / 2.0
    upper_probability = 1.0 - lower_probability
    return (
        quantile_type7(sorted_means, lower_probability),
        quantile_type7(sorted_means, upper_probability),
    )
