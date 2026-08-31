from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Self

from pydantic import model_validator

from fedsira.config.models import ScalingConfig
from fedsira.domain.types import (
    FeatureAccumulator,
    FeatureMoment,
    FeatureName,
    FiniteFloat,
    FrozenDomainModel,
    RowCount,
    SquaredFeatureAccumulator,
)

FeatureVector = tuple[FiniteFloat, ...]
FeatureMatrix = tuple[FeatureVector, ...]


class FeatureStatistic(FrozenDomainModel):
    count: RowCount
    total: FeatureAccumulator
    total_squared: SquaredFeatureAccumulator


class FeatureMoments(FrozenDomainModel):
    feature_names: tuple[FeatureName, ...]
    means: tuple[FeatureMoment, ...]
    standard_deviations: tuple[FeatureMoment, ...]
    training_row_count: RowCount

    @model_validator(mode="after")
    def _validate_consistency(self) -> Self:
        if not (len(self.feature_names) == len(self.means) == len(self.standard_deviations)):
            raise ValueError("feature moments must have matching lengths")
        if any(standard_deviation <= 0.0 for standard_deviation in self.standard_deviations):
            raise ValueError("feature standard deviations must be positive")
        return self


def accumulate_feature_statistics(
    feature_names: tuple[FeatureName, ...],
    feature_rows: Iterable[FeatureVector],
    existing: tuple[FeatureStatistic, ...] | None = None,
) -> tuple[FeatureStatistic, ...]:
    if existing is not None and len(existing) != len(feature_names):
        raise ValueError("existing statistics must match feature count")
    counts = (
        [statistic.count for statistic in existing]
        if existing is not None
        else [0] * len(feature_names)
    )
    sums = (
        [statistic.total for statistic in existing]
        if existing is not None
        else [0.0] * len(feature_names)
    )
    sum_of_squares = (
        [statistic.total_squared for statistic in existing]
        if existing is not None
        else [0.0] * len(feature_names)
    )
    for row in feature_rows:
        if len(row) != len(feature_names):
            raise ValueError("feature row width does not match feature schema")
        for column_index, numeric_value in enumerate(row):
            counts[column_index] += 1
            sums[column_index] += numeric_value
            sum_of_squares[column_index] += numeric_value * numeric_value
    return tuple(
        FeatureStatistic(
            count=counts[index],
            total=sums[index],
            total_squared=sum_of_squares[index],
        )
        for index in range(len(feature_names))
    )


def fit_feature_moments(
    feature_names: tuple[FeatureName, ...],
    statistics: tuple[FeatureStatistic, ...],
    scaling_config: ScalingConfig,
) -> FeatureMoments:
    if len(feature_names) != len(statistics):
        raise ValueError("feature name count must match statistics count")
    means: list[FiniteFloat] = []
    standard_deviations: list[FiniteFloat] = []
    row_count: RowCount = 0
    for feature_index, feature_name in enumerate(feature_names):
        statistic = statistics[feature_index]
        if statistic.count <= 0:
            raise ValueError(f"feature {feature_name} has no supported anchor-train rows")
        row_count = statistic.count
        mean = statistic.total / statistic.count
        variance = max(statistic.total_squared / statistic.count - mean * mean, 0.0)
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
    row: FeatureVector,
    moments: FeatureMoments,
    scaling_config: ScalingConfig,
) -> FeatureVector:
    if len(row) != len(moments.feature_names):
        raise ValueError("feature row width does not match fitted moments")
    standardized: list[FiniteFloat] = []
    for column_index, numeric_value in enumerate(row):
        mean = moments.means[column_index]
        standard_deviation = moments.standard_deviations[column_index]
        standardized_value = (numeric_value - mean) / standard_deviation
        standardized_value = min(
            max(standardized_value, scaling_config.clip_min), scaling_config.clip_max
        )
        standardized.append(standardized_value)
    return tuple(standardized)
