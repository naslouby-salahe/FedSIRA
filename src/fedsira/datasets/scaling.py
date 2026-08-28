from __future__ import annotations

import math
from collections.abc import Iterable, Iterator
from typing import Protocol, Self

from pydantic import model_validator

from fedsira.config.schema import ScalingConfig
from fedsira.domain.records import FeatureName, FiniteFloat, FrozenDomainModel, NonNegativeInt


class NumericRow(Protocol):
    def __iter__(self) -> Iterator[float]: ...


FeatureStatisticRow = tuple[float, float, float]


class FeatureMoments(FrozenDomainModel):
    feature_names: tuple[FeatureName, ...]
    means: tuple[FiniteFloat, ...]
    standard_deviations: tuple[FiniteFloat, ...]
    training_row_count: NonNegativeInt

    @model_validator(mode="after")
    def _validate_consistency(self) -> Self:
        if not (len(self.feature_names) == len(self.means) == len(self.standard_deviations)):
            raise ValueError("feature moments must have matching lengths")
        if any(standard_deviation <= 0.0 for standard_deviation in self.standard_deviations):
            raise ValueError("feature standard deviations must be positive")
        return self


def accumulate_feature_statistics(
    feature_names: tuple[FeatureName, ...],
    feature_matrix: Iterable[NumericRow],
    existing: tuple[FeatureStatisticRow, ...] | None = None,
) -> tuple[FeatureStatisticRow, ...]:
    counts: list[float] = []
    sums: list[float] = []
    sum_of_squares: list[float] = []
    if existing is not None:
        for count, total, total_squared in existing:
            counts.append(count)
            sums.append(total)
            sum_of_squares.append(total_squared)
    else:
        counts = [0.0] * len(feature_names)
        sums = [0.0] * len(feature_names)
        sum_of_squares = [0.0] * len(feature_names)
    for row in feature_matrix:
        for column_index, value in enumerate(row):
            numeric_value = float(value)
            counts[column_index] += 1.0
            sums[column_index] += numeric_value
            sum_of_squares[column_index] += numeric_value * numeric_value
    return tuple(
        (counts[index], sums[index], sum_of_squares[index]) for index in range(len(feature_names))
    )


def fit_feature_moments(
    feature_names: tuple[FeatureName, ...],
    statistics: tuple[FeatureStatisticRow, ...],
    scaling_config: ScalingConfig,
) -> FeatureMoments:
    if len(feature_names) != len(statistics):
        raise ValueError("feature name count must match statistics count")
    means: list[FiniteFloat] = []
    standard_deviations: list[FiniteFloat] = []
    row_count = 0
    for feature_index, feature_name in enumerate(feature_names):
        count, total, total_squared = statistics[feature_index]
        if count <= 0:
            raise ValueError(f"feature {feature_name} has no supported anchor-train rows")
        row_count = int(count)
        mean = total / count
        variance = max(total_squared / count - mean * mean, 0.0)
        standard_deviation = math.sqrt(variance)
        if standard_deviation == 0.0:
            standard_deviation = scaling_config.zero_standard_deviation_scale
        means.append(mean)
        standard_deviations.append(standard_deviation)
    return FeatureMoments(
        feature_names=feature_names,
        means=tuple(means),
        standard_deviations=tuple(standard_deviations),
        training_row_count=row_count,
    )


def standardize_row(
    row: NumericRow,
    moments: FeatureMoments,
    scaling_config: ScalingConfig,
) -> tuple[FiniteFloat, ...]:
    standardized: list[FiniteFloat] = []
    for column_index, value in enumerate(row):
        mean = moments.means[column_index]
        standard_deviation = moments.standard_deviations[column_index]
        standardized_value = (float(value) - mean) / standard_deviation
        standardized_value = min(
            max(standardized_value, scaling_config.clip_min), scaling_config.clip_max
        )
        standardized.append(standardized_value)
    return tuple(standardized)
