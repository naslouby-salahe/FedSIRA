from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.evaluation.aggregation import (
    bootstrap_percentile_confidence_interval,
    coefficient_of_variation,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    minimum_defined_domain_count,
    percentile_10_domain_target_f1,
    quantile_type7,
    worst_domain_target_f1,
)
from fedsira.evaluation.records import MetricResult

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def test_minimum_defined_domain_count_matches_generic_80_percent_rule() -> None:
    assert minimum_defined_domain_count(8, 0.8) == 7


def test_quantile_type7_matches_known_values() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert quantile_type7(values, 0.0) == 1.0
    assert quantile_type7(values, 1.0) == 5.0
    assert quantile_type7(values, 0.5) == 3.0


def test_equal_weight_domain_mean_requires_minimum_defined_domains() -> None:
    domain_results = [MetricResult(0.5, 10), MetricResult(None, 0), MetricResult(0.7, 10)]
    assert equal_weight_domain_mean(domain_results, 3).value is None
    result = equal_weight_domain_mean(domain_results, 2)
    assert result.value == 0.6
    assert result.denominator == 2


def test_worst_domain_target_f1_takes_minimum_defined() -> None:
    domain_results = [MetricResult(0.9, 10), MetricResult(0.4, 10), MetricResult(None, 0)]
    result = worst_domain_target_f1(domain_results)
    assert result.value == 0.4
    assert result.denominator == 2


def test_worst_domain_target_f1_na_when_nothing_defined() -> None:
    assert worst_domain_target_f1([MetricResult(None, 0)]).value is None


def test_percentile_10_domain_target_f1() -> None:
    domain_results = [MetricResult(float(value), 10) for value in range(1, 11)]
    result = percentile_10_domain_target_f1(domain_results)
    assert result.value is not None
    assert abs(result.value - 1.9) < 1e-9


def test_domain_disparity() -> None:
    domain_results = [MetricResult(0.9, 10), MetricResult(0.4, 10)]
    result = domain_disparity(domain_results)
    assert result.value is not None
    assert abs(result.value - 0.5) < 1e-9


def test_interquartile_range() -> None:
    domain_results = [MetricResult(float(value), 10) for value in range(1, 9)]
    result = interquartile_range(domain_results)
    assert result.value is not None
    assert result.value > 0.0


def test_coefficient_of_variation_na_on_zero_mean_or_single_value() -> None:
    assert coefficient_of_variation([1.0]).value is None
    assert coefficient_of_variation([-1.0, 1.0]).value is None


def test_coefficient_of_variation_numeric() -> None:
    result = coefficient_of_variation([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    assert result.value is not None
    assert result.value > 0.0


def test_bootstrap_confidence_interval_is_deterministic_and_brackets_mean() -> None:
    values = [0.70, 0.75, 0.80, 0.85, 0.90]
    bootstrap_config = CONFIG.metrics_and_statistics.bootstrap
    analysis_seed = CONFIG.seeds_and_determinism.analysis_seed
    first = bootstrap_percentile_confidence_interval(values, bootstrap_config, analysis_seed)
    second = bootstrap_percentile_confidence_interval(values, bootstrap_config, analysis_seed)
    assert first == second
    assert first is not None
    lower, upper = first
    assert lower <= sum(values) / len(values) <= upper


def test_bootstrap_confidence_interval_na_on_empty_input() -> None:
    bootstrap_config = CONFIG.metrics_and_statistics.bootstrap
    analysis_seed = CONFIG.seeds_and_determinism.analysis_seed
    assert bootstrap_percentile_confidence_interval([], bootstrap_config, analysis_seed) is None
