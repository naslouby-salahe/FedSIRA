from __future__ import annotations

from fedsira.artifacts.paths import experiment_metric_evidence_root
from fedsira.domain.enums import DescriptiveScientificMetric
from fedsira.domain.types import (
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    ScientificCellCount,
)
from fedsira.evaluation.statistics import quantile_type7
from fedsira.experiments.definitions import (
    AGGREGATE_METRICS_PARQUET_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
)
from fedsira.experiments.engine import CellExecutionOutcome
from fedsira.reporting.aggregate import read_aggregate_metric_evidence


class EfficiencyMetricObservation(FrozenDomainModel):
    method: MethodName
    metric: MetricName
    median: MetricValue
    first_quartile: MetricValue
    third_quartile: MetricValue
    seed_count: ScientificCellCount


class SeedMetricSummary(FrozenDomainModel):
    mean: MetricValue
    median: MetricValue
    first_quartile: MetricValue
    third_quartile: MetricValue
    seed_count: ScientificCellCount


def summarize_seed_values(values: tuple[MetricValue, ...]) -> SeedMetricSummary | None:
    if not values:
        return None
    ordered = tuple(sorted(values))
    return SeedMetricSummary(
        mean=sum(values) / len(values),
        median=quantile_type7(ordered, 0.5),
        first_quartile=quantile_type7(ordered, 0.25),
        third_quartile=quantile_type7(ordered, 0.75),
        seed_count=len(values),
    )


EFFICIENCY_METRICS: tuple[MetricName, ...] = (
    DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
    DescriptiveScientificMetric.GPU_SECONDS,
    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
    DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES,
    DescriptiveScientificMetric.COMMUNICATION_BYTES,
    DescriptiveScientificMetric.MODEL_TRANSMISSIONS,
    DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES,
)


def efficiency_telemetry(
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[EfficiencyMetricObservation, ...]:
    efficiency_outcomes = tuple(
        outcome
        for outcome in outcomes
        if (
            outcome.completed
            and outcome.cell.experiment == EFFICIENCY_MEASUREMENT_NAME
            and outcome.cell.repetition is not None
        )
    )
    methods = frozenset(outcome.cell.method for outcome in efficiency_outcomes)
    artifact_path = (
        experiment_metric_evidence_root(EFFICIENCY_MEASUREMENT_NAME)
        / AGGREGATE_METRICS_PARQUET_NAME
    )
    aggregates = read_aggregate_metric_evidence(
        artifact_path,
        EFFICIENCY_MEASUREMENT_NAME,
    )
    observations: list[EfficiencyMetricObservation] = []
    for metric in EFFICIENCY_METRICS:
        for method in sorted(methods):
            rows = tuple(row for row in aggregates if row.method == method and row.metric == metric)
            if len(rows) > 1:
                raise ValueError(
                    f"{EFFICIENCY_MEASUREMENT_NAME}/{method}/{metric}: "
                    "expected one configured efficiency condition"
                )
            if rows:
                summary = rows[0]
                observations.append(
                    EfficiencyMetricObservation(
                        method=method,
                        metric=metric,
                        median=summary.median_value,
                        first_quartile=summary.first_quartile,
                        third_quartile=summary.third_quartile,
                        seed_count=summary.seed_count,
                    )
                )
    return tuple(observations)
