from __future__ import annotations

from fedsira.domain.enums import DatasetId, ExperimentLifecycleState
from fedsira.domain.types import (
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricName,
    MetricObservation,
    MetricValue,
    ScenarioName,
)
from fedsira.experiments.execution import CellExecutionOutcome, PersistedExecutionRecord


class MetricCellKey(FrozenDomainModel):
    dataset: DatasetId
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    master_seed: MasterSeed
    method: MethodName


class MetricCellRecord(FrozenDomainModel):
    key: MetricCellKey
    metrics: tuple[MetricObservation, ...]


def merge_metric_record(
    records: tuple[MetricCellRecord, ...], incoming: MetricCellRecord
) -> tuple[MetricCellRecord, ...]:
    retained = tuple(record for record in records if record.key != incoming.key)
    return (*retained, incoming)


def metric_value(
    records: tuple[MetricCellRecord, ...], key: MetricCellKey, metric: MetricName
) -> MetricValue | None:
    for record in reversed(records):
        if record.key != key:
            continue
        for metric_name, metric_result in reversed(record.metrics):
            if metric_name == metric:
                return metric_result
    return None


def metric_index_from_outcomes(
    dataset: DatasetId, outcomes: tuple[CellExecutionOutcome, ...]
) -> tuple[MetricCellRecord, ...]:
    records: tuple[MetricCellRecord, ...] = ()
    for outcome in outcomes:
        if outcome.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        records = merge_metric_record(
            records,
            MetricCellRecord(
                key=MetricCellKey(
                    dataset=dataset,
                    experiment=outcome.cell.experiment,
                    scientific_scenario=outcome.cell.condition,
                    master_seed=outcome.cell.master_seed,
                    method=outcome.cell.method,
                ),
                metrics=outcome.metrics,
            ),
        )
    return records


def extend_index_from_records(
    records: tuple[MetricCellRecord, ...],
    dataset: DatasetId,
    persisted_records: tuple[PersistedExecutionRecord, ...],
) -> tuple[MetricCellRecord, ...]:
    merged = records
    for record in persisted_records:
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        merged = merge_metric_record(
            merged,
            MetricCellRecord(
                key=MetricCellKey(
                    dataset=dataset,
                    experiment=record.experiment,
                    scientific_scenario=record.condition,
                    master_seed=record.master_seed,
                    method=record.method,
                ),
                metrics=record.metrics,
            ),
        )
    return merged
