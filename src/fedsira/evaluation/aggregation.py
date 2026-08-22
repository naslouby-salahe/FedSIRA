import math
from collections.abc import Sequence

import numpy

from fedsira.config.schema import BootstrapConfig
from fedsira.domain.records import MasterSeed, PositiveInt
from fedsira.evaluation.records import MetricResult
from fedsira.runtime.determinism import derive_uint32

SINGLE_METHOD_MEAN_BOOTSTRAP_SEPARATOR = "SINGLE_METHOD_MEAN_BOOTSTRAP"


def minimum_defined_domain_count(
    expected_domain_count: PositiveInt, generic_defined_domain_fraction_minimum: float
) -> PositiveInt:
    return math.ceil(expected_domain_count * generic_defined_domain_fraction_minimum)


def quantile_type7(sorted_values: Sequence[float], probability: float) -> float:
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


def equal_weight_domain_mean(
    domain_results: Sequence[MetricResult], minimum_defined_domains: PositiveInt
) -> MetricResult:
    defined_values = [result.value for result in domain_results if result.value is not None]
    if len(defined_values) < minimum_defined_domains:
        return MetricResult(None, len(defined_values))
    return MetricResult(sum(defined_values) / len(defined_values), len(defined_values))


def worst_domain_target_f1(domain_target_f1: Sequence[MetricResult]) -> MetricResult:
    defined_values = [result.value for result in domain_target_f1 if result.value is not None]
    if len(defined_values) == 0:
        return MetricResult(None, 0)
    return MetricResult(min(defined_values), len(defined_values))


def percentile_10_domain_target_f1(domain_target_f1: Sequence[MetricResult]) -> MetricResult:
    defined_values = sorted(result.value for result in domain_target_f1 if result.value is not None)
    if len(defined_values) == 0:
        return MetricResult(None, 0)
    return MetricResult(quantile_type7(defined_values, 0.10), len(defined_values))


def domain_disparity(domain_target_f1: Sequence[MetricResult]) -> MetricResult:
    defined_values = [result.value for result in domain_target_f1 if result.value is not None]
    if len(defined_values) == 0:
        return MetricResult(None, 0)
    return MetricResult(max(defined_values) - min(defined_values), len(defined_values))


def interquartile_range(domain_target_f1: Sequence[MetricResult]) -> MetricResult:
    defined_values = sorted(result.value for result in domain_target_f1 if result.value is not None)
    if len(defined_values) == 0:
        return MetricResult(None, 0)
    upper_quartile = quantile_type7(defined_values, 0.75)
    lower_quartile = quantile_type7(defined_values, 0.25)
    return MetricResult(upper_quartile - lower_quartile, len(defined_values))


def coefficient_of_variation(values: Sequence[float]) -> MetricResult:
    if len(values) < 2:
        return MetricResult(None, len(values))
    mean = sum(values) / len(values)
    if mean == 0:
        return MetricResult(None, len(values))
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    standard_deviation = math.sqrt(variance)
    return MetricResult(standard_deviation / mean, len(values))


def bootstrap_percentile_confidence_interval(
    seed_level_values: Sequence[float],
    bootstrap_config: BootstrapConfig,
    analysis_seed: MasterSeed,
) -> tuple[float, float] | None:
    if len(seed_level_values) == 0:
        return None
    bootstrap_seed = derive_uint32(SINGLE_METHOD_MEAN_BOOTSTRAP_SEPARATOR, analysis_seed)
    generator = numpy.random.default_rng(bootstrap_seed)
    values = numpy.asarray(seed_level_values, dtype=numpy.float64)
    sample_size = len(values)
    resampled_means = numpy.empty(bootstrap_config.resamples, dtype=numpy.float64)
    for resample_index in range(bootstrap_config.resamples):
        indices = generator.integers(0, sample_size, size=sample_size)
        resampled_means[resample_index] = values[indices].mean()
    sorted_means = numpy.sort(resampled_means).tolist()
    lower_probability = (1.0 - bootstrap_config.confidence_level) / 2.0
    upper_probability = 1.0 - lower_probability
    lower_bound = quantile_type7(sorted_means, lower_probability)
    upper_bound = quantile_type7(sorted_means, upper_probability)
    return (lower_bound, upper_bound)
