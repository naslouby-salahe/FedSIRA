from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas

from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.domain.types import (
    BooleanValue,
    ComparisonName,
    EvidenceCycleIndex,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricName,
    MetricValue,
    RepetitionIndex,
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
    STATE_TRAJECTORY_PARQUET_NAME,
    DescriptiveScientificMetric,
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
        DescriptiveScientificMetric.WALL_CLOCK_SECONDS.value,
    )
)
_RESOURCE_METRICS: frozenset[MetricName] = frozenset(
    (
        DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES.value,
        DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES.value,
        DescriptiveScientificMetric.COMMUNICATION_BYTES.value,
        DescriptiveScientificMetric.MODEL_TRANSMISSIONS.value,
    )
)


class MetricEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    repetition: RepetitionIndex | None
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
        RepetitionIndex | None,
        TextValue,
        MetricName,
        MetricValue | None,
    ]:
        return (
            self.experiment,
            self.method,
            self.condition,
            self.master_seed,
            self.repetition,
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


class StateTrajectoryEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    repetition: RepetitionIndex | None
    logical_evidence_cycle: EvidenceCycleIndex
    admission_state: TextValue

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        MethodName,
        ScenarioName,
        MasterSeed,
        RepetitionIndex | None,
        EvidenceCycleIndex,
        TextValue,
    ]:
        return (
            self.experiment,
            self.method,
            self.condition,
            self.master_seed,
            self.repetition,
            self.logical_evidence_cycle,
            self.admission_state,
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
            repetition=outcome.cell.repetition,
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


def _state_trajectory_rows(
    experiment: ExperimentName,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[StateTrajectoryEvidenceRow, ...]:
    return tuple(
        StateTrajectoryEvidenceRow(
            experiment=experiment,
            method=outcome.cell.method,
            condition=outcome.cell.condition,
            master_seed=outcome.cell.master_seed,
            repetition=outcome.cell.repetition,
            logical_evidence_cycle=observation.cycle,
            admission_state=observation.state.value,
        )
        for outcome in outcomes
        for observation in outcome.state_trajectory
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
            "repetition",
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


def _write_state_trajectory_parquet(
    destination: Path,
    rows: tuple[StateTrajectoryEvidenceRow, ...],
) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            "experiment",
            "method",
            "condition",
            "master_seed",
            "repetition",
            "logical_evidence_cycle",
            "admission_state",
        ),
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
    trajectory_rows = _state_trajectory_rows(result.experiment, result.outcomes)
    if trajectory_rows:
        paths.append(
            _write_state_trajectory_parquet(
                metrics_root / STATE_TRAJECTORY_PARQUET_NAME,
                trajectory_rows,
            )
        )
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
