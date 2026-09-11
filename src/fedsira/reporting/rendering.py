from __future__ import annotations

import csv
from collections.abc import Callable
from io import StringIO

from fedsira.domain.types import (
    FormattedStatisticText,
    FrozenDomainModel,
    MetricValue,
    TableCsvText,
    TableName,
    TextValue,
)
from fedsira.experiments.execution import CellExecutionOutcome


class RenderedTable(FrozenDomainModel):
    name: TableName
    csv_text: TableCsvText


def csv_text(
    header: tuple[TextValue, ...],
    rows: tuple[tuple[TextValue, ...], ...],
) -> TableCsvText:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().rstrip("\n")


def render_cell_metrics(
    outcomes: tuple[CellExecutionOutcome, ...],
    table_name: TableName,
    format_value: Callable[[MetricValue | None], FormattedStatisticText],
) -> RenderedTable:
    rows: list[tuple[TextValue, ...]] = []
    for outcome in outcomes:
        for metric_name, metric_value in outcome.metrics:
            rows.append(
                (
                    outcome.cell.experiment,
                    outcome.cell.method,
                    outcome.cell.condition,
                    f"{outcome.cell.master_seed}",
                    "" if outcome.cell.repetition is None else f"{outcome.cell.repetition}",
                    outcome.terminal_state.value,
                    metric_name,
                    format_value(metric_value),
                )
            )
    return RenderedTable(
        name=table_name,
        csv_text=csv_text(
            (
                "experiment",
                "method",
                "condition",
                "master_seed",
                "repetition",
                "terminal_state",
                "metric",
                "value",
            ),
            tuple(rows),
        ),
    )
