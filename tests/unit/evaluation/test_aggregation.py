import numpy

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.evaluation.aggregation import (
    bootstrap_percentile_confidence_interval,
    coefficient_of_variation,
    decile_bin,
    decile_boundaries,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    match_nearest_within_decile,
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


def test_quantile_type7_matches_numpy_linear_method_for_arbitrary_probabilities() -> None:
    values = [3.0, 7.0, 1.0, 9.0, 4.0, 2.0, 8.0, 6.0, 5.0]
    sorted_values = sorted(values)
    for probability in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
        expected = float(numpy.quantile(values, probability, method="linear"))
        actual = quantile_type7(sorted_values, probability)
        assert abs(actual - expected) < 1e-12


def test_coefficient_of_variation_uses_ddof_1_hand_fixture() -> None:
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    mean = sum(values) / len(values)
    variance_ddof_1 = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    expected = (variance_ddof_1**0.5) / mean
    result = coefficient_of_variation(values)
    assert result.value is not None
    assert abs(result.value - expected) < 1e-9
    numpy_sample_sd = float(numpy.std(values, ddof=1))
    assert abs(result.value - numpy_sample_sd / mean) < 1e-9


def test_equal_weight_domain_mean_treats_each_domain_as_one_inference_unit() -> None:
    small_domain = MetricResult(0.5, 3)
    large_domain = MetricResult(0.9, 3000)
    result = equal_weight_domain_mean([small_domain, large_domain], 2)
    assert result.value == 0.7
    assert result.denominator == 2


def test_bootstrap_confidence_interval_na_on_empty_input() -> None:
    bootstrap_config = CONFIG.metrics_and_statistics.bootstrap
    analysis_seed = CONFIG.seeds_and_determinism.analysis_seed
    assert bootstrap_percentile_confidence_interval([], bootstrap_config, analysis_seed) is None


def test_decile_boundaries_and_bin_are_consistent() -> None:
    values = [float(v) for v in range(1, 11)]
    boundaries = decile_boundaries(values)
    assert len(boundaries) == 9
    assert decile_bin(0.5, boundaries) == 0
    assert decile_bin(10.0, boundaries) == 9


def test_match_nearest_within_decile_matches_by_closest_value() -> None:
    boundary_values = [float(v) for v in range(1, 11)]
    targets = [("t1", 1.0)]
    candidates = [("c1", 0.9)] + [(f"c{i}", float(i)) for i in range(2, 11)]
    matched = match_nearest_within_decile(targets, candidates, boundary_values)
    assert matched == (("t1", "c1"),)


def test_match_nearest_within_decile_returns_none_without_replacement_when_bin_is_empty() -> None:
    targets = [("t1", 100.0)]
    candidates = [("c1", 1.0)]
    assert (
        match_nearest_within_decile(targets, candidates, [float(v) for v in range(1, 11)]) is None
    )


def test_match_nearest_within_decile_returns_none_for_empty_boundary_values() -> None:
    assert match_nearest_within_decile([], [], []) is None
    assert match_nearest_within_decile([("t1", 1.0)], [("c1", 1.0)], []) is None
