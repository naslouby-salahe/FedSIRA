import math

import pytest

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.scaling import (
    FeatureMoments,
    accumulate_feature_statistics,
    fit_feature_moments,
    standardize_row,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
SCALING = CONFIG.datasets.primary.scaling

FEATURES = ("f0", "f1")
MOMENTS = FeatureMoments(
    feature_names=FEATURES,
    means=(0.0, 10.0),
    standard_deviations=(1.0, 2.0),
    training_row_count=3,
)


def test_accumulate_feature_statistics_empty() -> None:
    statistics = accumulate_feature_statistics(FEATURES, [])
    assert statistics == ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def test_accumulate_feature_statistics_sums() -> None:
    rows = [(1.0, 2.0), (3.0, 4.0)]
    statistics = accumulate_feature_statistics(FEATURES, rows)
    assert statistics == (
        (2.0, 4.0, 10.0),
        (2.0, 6.0, 20.0),
    )


def test_accumulate_feature_statistics_extends_existing() -> None:
    existing = ((1.0, 1.0, 1.0), (1.0, 2.0, 4.0))
    statistics = accumulate_feature_statistics(FEATURES, [(1.0, 2.0)], existing)
    assert statistics == (
        (2.0, 2.0, 2.0),
        (2.0, 4.0, 8.0),
    )


def test_fit_feature_moments_computes_mean_and_std() -> None:
    statistics = ((3.0, 3.0, 5.0), (3.0, 30.0, 310.0))
    moments = fit_feature_moments(FEATURES, statistics, SCALING)
    assert moments.means == (1.0, 10.0)
    expected_std = (math.sqrt(2 / 3), math.sqrt(10 / 3))
    assert [round(value, 12) for value in moments.standard_deviations] == [
        round(value, 12) for value in expected_std
    ]
    assert moments.training_row_count == 3


def test_fit_feature_moments_rejects_count_mismatch() -> None:
    with pytest.raises(ValueError):
        fit_feature_moments(("f0",), ((1.0, 1.0, 1.0), (1.0, 2.0, 4.0)), SCALING)


def test_fit_feature_moments_rejects_zero_count() -> None:
    with pytest.raises(ValueError):
        fit_feature_moments(FEATURES, ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)), SCALING)


def test_fit_feature_moments_zero_variance_uses_floor() -> None:
    statistics = ((2.0, 4.0, 8.0), (2.0, 6.0, 18.0))
    moments = fit_feature_moments(FEATURES, statistics, SCALING)
    assert moments.standard_deviations[1] == SCALING.zero_standard_deviation_scale


def test_standardize_row_normalizes_and_clips() -> None:
    row = (2.0, 6.0)
    standardized = standardize_row(row, MOMENTS, SCALING)
    assert standardized[0] == 2.0
    assert standardized[1] == -2.0


def test_standardize_row_clips_high_values() -> None:
    row = (100.0, 1000.0)
    standardized = standardize_row(row, MOMENTS, SCALING)
    assert standardized[0] <= SCALING.clip_max
    assert standardized[1] >= SCALING.clip_min


def test_feature_moments_reject_inconsistent_lengths() -> None:
    with pytest.raises(ValueError, match="matching lengths"):
        FeatureMoments(
            feature_names=("f0",),
            means=(0.0,),
            standard_deviations=(1.0, 2.0),
            training_row_count=2,
        )


def test_feature_moments_reject_nonpositive_scale() -> None:
    with pytest.raises(ValueError, match="positive"):
        FeatureMoments(
            feature_names=("f0",),
            means=(0.0,),
            standard_deviations=(0.0,),
            training_row_count=2,
        )
