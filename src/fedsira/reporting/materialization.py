from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas

from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.types import (
    BooleanValue,
    ComparisonName,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricName,
    MetricValue,
    RepositoryPath,
    ScenarioName,
    ScientificCellCount,
    TextValue,
)
from fedsira.evaluation.comparisons import ComparisonFamily, ComparisonFamilyResult, ComparisonState
from fedsira.experiments.definitions import (
    AGGREGATE_METRICS_PARQUET_NAME,
    CELL_METRICS_PARQUET_NAME,
    SEED_METRICS_PARQUET_NAME,
)
from fedsira.experiments.execution import CellExecutionOutcome, ExperimentExecutionResult

COMPARISONS_PARQUET_NAME = "comparisons.parquet"
TIMINGS_PARQUET_NAME = "timings.parquet"
RESOURCES_PARQUET_NAME = "resources.parquet"

_TIMING_METRICS: frozenset[MetricName] = frozenset(
    (
        "assignment-seconds",
        "reproduce-seconds",
        "verify-seconds",
        "synthesize-seconds",
        "post-evidence-wall-clock-seconds",
    )
)
_RESOURCE_METRICS: frozenset[MetricName] = frozenset(
    (
        "peak-gpu-memory-bytes",
        "peak-host-rss-bytes",
        "communication-bytes",
        "model-transmissions",
    )
)


class MetricEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    terminal_state: ExperimentLifecycleState
    metric: MetricName
    value: MetricValue | None

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        MethodName,
        ScenarioName,
        MasterSeed,
        TextValue,
        MetricName,
        MetricValue | None,
    ]:
        return (
            self.experiment,
            self.method,
            self.condition,
            self.master_seed,
            self.terminal_state.value,
            self.metric,
            self.value,
        )


class AggregateMetricEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    metric: MetricName
    observation_count: ScientificCellCount
    mean_value: MetricValue

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        MethodName,
        ScenarioName,
        MetricName,
        ScientificCellCount,
        MetricValue,
    ]:
        return (
            self.experiment,
            self.method,
            self.condition,
            self.metric,
            self.observation_count,
            self.mean_value,
        )


class ComparisonEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    family: ComparisonFamily
    comparison: ComparisonName
    method: MethodName
    scenario: ScenarioName
    metric: MetricName
    complete_seed_count: ScientificCellCount
    mean_paired_difference: MetricValue | None
    adjusted_p_value: MetricValue | None
    state: ComparisonState

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        TextValue,
        TextValue,
        MethodName,
        ScenarioName,
        MetricName,
        ScientificCellCount,
        MetricValue | None,
        MetricValue | None,
        TextValue,
    ]:
        return (
            self.experiment,
            self.family.value,
            self.comparison,
            self.method,
            self.scenario,
            self.metric,
            self.complete_seed_count,
            self.mean_paired_difference,
            self.adjusted_p_value,
            self.state.value,
        )


class ExperimentEvidenceMaterialization(FrozenDomainModel):
    paths: tuple[RepositoryPath, ...]


def parquet_contains_rows(path: Path) -> BooleanValue:
    return path.is_file() and not pandas.read_parquet(path).empty


def _metric_rows(
    experiment: ExperimentName,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[MetricEvidenceRow, ...]:
    return tuple(
        MetricEvidenceRow(
            experiment=experiment,
            method=outcome.cell.method,
            condition=outcome.cell.condition,
            master_seed=outcome.cell.master_seed,
            terminal_state=outcome.terminal_state,
            metric=metric,
            value=value,
        )
        for outcome in outcomes
        for metric, value in outcome.metrics
    )


def _aggregate_rows(
    rows: tuple[MetricEvidenceRow, ...],
) -> tuple[AggregateMetricEvidenceRow, ...]:
    values_by_identity: defaultdict[
        tuple[ExperimentName, MethodName, ScenarioName, MetricName], list[MetricValue]
    ] = defaultdict(list)
    for row in rows:
        if row.value is not None:
            values_by_identity[(row.experiment, row.method, row.condition, row.metric)].append(
                row.value
            )
    return tuple(
        AggregateMetricEvidenceRow(
            experiment=experiment,
            method=method,
            condition=condition,
            metric=metric,
            observation_count=len(values),
            mean_value=sum(values) / len(values),
        )
        for (experiment, method, condition, metric), values in sorted(values_by_identity.items())
        if values
    )


def _comparison_rows(
    experiment: ExperimentName,
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> tuple[ComparisonEvidenceRow, ...]:
    return tuple(
        ComparisonEvidenceRow(
            experiment=experiment,
            family=family.family,
            comparison=comparison.definition.comparison_name,
            method=comparison.definition.method,
            scenario=comparison.definition.scientific_scenario,
            metric=comparison.definition.metric.value,
            complete_seed_count=comparison.complete_seed_count,
            mean_paired_difference=comparison.mean_paired_difference,
            adjusted_p_value=comparison.adjusted_p_value,
            state=comparison.comparison_state,
        )
        for family in comparison_results
        for comparison in family.comparisons
    )


def _write_metric_parquet(destination: Path, rows: tuple[MetricEvidenceRow, ...]) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            "experiment",
            "method",
            "condition",
            "master_seed",
            "terminal_state",
            "metric",
            "value",
        ),
    )
    frame.to_parquet(destination, index=False)
    return destination


def _write_aggregate_metric_parquet(
    destination: Path,
    rows: tuple[AggregateMetricEvidenceRow, ...],
) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=("experiment", "method", "condition", "metric", "observation_count", "mean_value"),
    )
    frame.to_parquet(destination, index=False)
    return destination


def _write_comparison_parquet(destination: Path, rows: tuple[ComparisonEvidenceRow, ...]) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            "experiment",
            "family",
            "comparison",
            "method",
            "scenario",
            "metric",
            "complete_seed_count",
            "mean_paired_difference",
            "adjusted_p_value",
            "state",
        ),
    )
    frame.to_parquet(destination, index=False)
    return destination


def materialize_experiment_evidence(
    result: ExperimentExecutionResult,
    metrics_root: Path,
    telemetry_root: Path,
) -> ExperimentEvidenceMaterialization:
    metrics_root.mkdir(parents=True, exist_ok=True)
    telemetry_root.mkdir(parents=True, exist_ok=True)
    rows = _metric_rows(result.experiment, result.outcomes)
    paths: list[Path] = [
        _write_metric_parquet(metrics_root / CELL_METRICS_PARQUET_NAME, rows),
        _write_metric_parquet(metrics_root / SEED_METRICS_PARQUET_NAME, rows),
        _write_aggregate_metric_parquet(
            metrics_root / AGGREGATE_METRICS_PARQUET_NAME,
            _aggregate_rows(rows),
        ),
    ]
    comparison_rows = _comparison_rows(result.experiment, result.comparison_results)
    if comparison_rows:
        paths.append(
            _write_comparison_parquet(
                metrics_root / COMPARISONS_PARQUET_NAME,
                comparison_rows,
            )
        )
    for filename, metric_names in (
        (TIMINGS_PARQUET_NAME, _TIMING_METRICS),
        (RESOURCES_PARQUET_NAME, _RESOURCE_METRICS),
    ):
        telemetry_rows = tuple(row for row in rows if row.metric in metric_names)
        if telemetry_rows:
            paths.append(_write_metric_parquet(telemetry_root / filename, telemetry_rows))
    return ExperimentEvidenceMaterialization(paths=tuple(str(path) for path in paths))
