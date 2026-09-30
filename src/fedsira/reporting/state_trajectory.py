from __future__ import annotations

import math
from collections.abc import Iterable
from numbers import Integral, Real
from pathlib import Path
from typing import Protocol, TypeAlias, cast

import pandas

from fedsira.domain.enums import (
    AdmissionState,
    EvidenceArrivalSchedule,
    ExperimentName,
    ReportColumnName,
)
from fedsira.domain.types import (
    EvidenceCycleIndex,
    FrozenDomainModel,
    Probability,
    ScenarioName,
    ScientificCellCount,
    ScientificCellSemanticKey,
    ScientificCellSemanticKeyTuple,
)
from fedsira.experiments.engine import CellExecutionOutcome
from fedsira.runtime import current_application_context


class ParquetStringArray(Protocol):
    def tolist(self) -> ScientificCellSemanticKeyTuple: ...


ParquetTrajectoryValue: TypeAlias = str | int | float | None | list[str] | ParquetStringArray

EVIDENCE_TRAJECTORY_STATE_VOCABULARY: tuple[AdmissionState, ...] = (
    AdmissionState.DORMANT,
    AdmissionState.VERIFICATION_PENDING,
    AdmissionState.ADMITTED,
    AdmissionState.REJECTED,
    AdmissionState.EXPIRED,
)


class EvidenceStateFraction(FrozenDomainModel):
    experiment: ExperimentName | None = None
    condition: ScenarioName
    cycle: EvidenceCycleIndex
    state: AdmissionState
    fraction: Probability
    instance_count: ScientificCellCount
    instance_total: ScientificCellCount
    source_cell_semantic_keys: ScientificCellSemanticKeyTuple = ()


class StateTrajectoryFractionEvidenceRow(FrozenDomainModel):
    experiment: ExperimentName
    condition: ScenarioName
    cycle: EvidenceCycleIndex
    state: AdmissionState
    instance_count: ScientificCellCount
    instance_total: ScientificCellCount
    fraction: Probability
    source_cell_semantic_keys: ScientificCellSemanticKeyTuple

    def values(
        self,
    ) -> tuple[
        ExperimentName,
        ScenarioName,
        EvidenceCycleIndex,
        AdmissionState,
        ScientificCellCount,
        ScientificCellCount,
        Probability,
        ScientificCellSemanticKeyTuple,
    ]:
        return (
            self.experiment,
            self.condition,
            self.cycle,
            self.state,
            self.instance_count,
            self.instance_total,
            self.fraction,
            self.source_cell_semantic_keys,
        )


def state_trajectory_fraction_rows(
    experiment: ExperimentName,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[StateTrajectoryFractionEvidenceRow, ...]:
    if experiment is not ExperimentName.EVIDENCE_SCARCITY_AND_DORMANCY:
        return ()
    completed = tuple(outcome for outcome in outcomes if outcome.completed)
    if not completed:
        return ()

    resource_horizon = current_application_context().scientific_config.protocol.resource_horizon
    horizon = resource_horizon.maximum_logical_evidence_cycles
    expected_cycles = frozenset(range(horizon + 1))
    for outcome in completed:
        observed_cycles = frozenset(item.cycle for item in outcome.state_trajectory)
        if observed_cycles != expected_cycles or len(observed_cycles) != len(
            outcome.state_trajectory
        ):
            raise ValueError(
                f"{experiment}: state trajectory for {outcome.cell.semantic_key} must contain "
                "exactly one observation at every configured logical evidence cycle"
            )

    state_vocabulary = EVIDENCE_TRAJECTORY_STATE_VOCABULARY
    rows: list[StateTrajectoryFractionEvidenceRow] = []
    conditions = sorted({outcome.cell.condition for outcome in completed})
    for condition in conditions:
        condition_outcomes = tuple(
            outcome for outcome in completed if outcome.cell.condition == condition
        )
        source_keys = tuple(sorted(outcome.cell.semantic_key for outcome in condition_outcomes))
        denominator = len(condition_outcomes)
        for cycle in sorted(expected_cycles):
            cycle_states = tuple(
                next(item.state for item in outcome.state_trajectory if item.cycle == cycle)
                for outcome in condition_outcomes
            )
            unexpected_states = frozenset(cycle_states) - frozenset(state_vocabulary)
            if unexpected_states:
                raise ValueError(
                    f"{experiment}: unsupported evidence-trajectory states: "
                    f"{sorted(state.value for state in unexpected_states)}"
                )
            for state in state_vocabulary:
                count = sum(item is state for item in cycle_states)
                rows.append(
                    StateTrajectoryFractionEvidenceRow(
                        experiment=experiment,
                        condition=condition,
                        cycle=cycle,
                        state=state,
                        instance_count=count,
                        instance_total=denominator,
                        fraction=count / denominator,
                        source_cell_semantic_keys=source_keys,
                    )
                )
    return tuple(rows)


def write_state_trajectory_fraction_parquet(
    destination: Path,
    rows: tuple[StateTrajectoryFractionEvidenceRow, ...],
) -> Path:
    frame = pandas.DataFrame(
        tuple(row.values() for row in rows),
        columns=(
            ReportColumnName.EXPERIMENT,
            ReportColumnName.CONDITION,
            ReportColumnName.LOGICAL_EVIDENCE_CYCLE,
            ReportColumnName.ADMISSION_STATE,
            ReportColumnName.OBSERVATION_COUNT,
            ReportColumnName.SEED_COUNT,
            ReportColumnName.FRACTION_OF_SEED_INSTANCES,
            ReportColumnName.SOURCE_CELL_SEMANTIC_KEYS,
        ),
    )
    frame.to_parquet(destination, index=False)
    return destination


def read_state_trajectory_fractions(
    path: Path,
    experiment: ExperimentName,
) -> tuple[EvidenceStateFraction, ...]:
    if not path.is_file():
        return ()
    frame = pandas.read_parquet(path)
    columns = (
        ReportColumnName.EXPERIMENT,
        ReportColumnName.CONDITION,
        ReportColumnName.LOGICAL_EVIDENCE_CYCLE,
        ReportColumnName.ADMISSION_STATE,
        ReportColumnName.OBSERVATION_COUNT,
        ReportColumnName.SEED_COUNT,
        ReportColumnName.FRACTION_OF_SEED_INSTANCES,
        ReportColumnName.SOURCE_CELL_SEMANTIC_KEYS,
    )
    if not set(columns).issubset(frame.columns) or frame.empty:
        raise ValueError(f"{experiment}: persisted state-trajectory fractions are incomplete")

    raw_rows = cast(
        Iterable[tuple[ParquetTrajectoryValue, ...]],
        frame.loc[:, list(columns)].itertuples(index=False, name=None),
    )
    result: list[StateTrajectoryFractionEvidenceRow] = []
    for raw in raw_rows:
        (
            raw_experiment,
            raw_condition,
            raw_cycle,
            raw_state,
            raw_count,
            raw_total,
            raw_fraction,
            raw_source_keys,
        ) = raw
        if raw_experiment != experiment:
            continue
        if not isinstance(raw_condition, str) or not isinstance(raw_state, str):
            raise ValueError(f"{experiment}: state-trajectory category is malformed")
        try:
            condition = EvidenceArrivalSchedule(raw_condition)
            state = AdmissionState(raw_state)
        except ValueError as error:
            raise ValueError(f"{experiment}: unknown state-trajectory category") from error
        if not all(isinstance(value, Integral) for value in (raw_cycle, raw_count, raw_total)):
            raise ValueError(f"{experiment}: state-trajectory counts are malformed")
        if not isinstance(raw_fraction, Real):
            raise ValueError(f"{experiment}: state-trajectory fraction is malformed")
        source_keys = _source_keys(raw_source_keys, experiment)
        fraction = float(raw_fraction)
        count = int(cast(int, raw_count))
        total = int(cast(int, raw_total))
        if (
            not source_keys
            or len(set(source_keys)) != len(source_keys)
            or total != len(source_keys)
            or count < 0
            or count > total
            or not math.isfinite(fraction)
            or not 0.0 <= fraction <= 1.0
            or fraction != count / total
        ):
            raise ValueError(f"{experiment}: state-trajectory fraction or lineage is invalid")
        result.append(
            StateTrajectoryFractionEvidenceRow(
                experiment=experiment,
                condition=condition,
                cycle=int(cast(int, raw_cycle)),
                state=state,
                instance_count=count,
                instance_total=total,
                fraction=fraction,
                source_cell_semantic_keys=source_keys,
            )
        )

    resource_horizon = current_application_context().scientific_config.protocol.resource_horizon
    horizon = resource_horizon.maximum_logical_evidence_cycles
    expected_conditions = frozenset(EvidenceArrivalSchedule)
    expected_keys = {
        (condition, cycle, state)
        for condition in expected_conditions
        for cycle in range(horizon + 1)
        for state in EVIDENCE_TRAJECTORY_STATE_VOCABULARY
    }
    observed_keys = tuple((row.condition, row.cycle, row.state) for row in result)
    if len(observed_keys) != len(set(observed_keys)) or set(observed_keys) != expected_keys:
        raise ValueError(
            f"{experiment}: persisted state-trajectory grid is incomplete or duplicated"
        )
    for condition in expected_conditions:
        condition_rows = tuple(row for row in result if row.condition == condition)
        expected_sources = condition_rows[0].source_cell_semantic_keys
        expected_total = condition_rows[0].instance_total
        if any(
            row.source_cell_semantic_keys != expected_sources
            or row.instance_total != expected_total
            for row in condition_rows
        ):
            raise ValueError(f"{experiment}: state-trajectory source lineage varies by cell")
        for cycle in range(horizon + 1):
            cycle_rows = tuple(row for row in condition_rows if row.cycle == cycle)
            if sum(row.instance_count for row in cycle_rows) != expected_total:
                raise ValueError(f"{experiment}: state-trajectory fractions do not partition seeds")

    return tuple(
        EvidenceStateFraction(
            experiment=experiment,
            condition=row.condition,
            cycle=row.cycle,
            state=row.state,
            fraction=row.fraction,
            instance_count=row.instance_count,
            instance_total=row.instance_total,
            source_cell_semantic_keys=row.source_cell_semantic_keys,
        )
        for row in result
    )


def _source_keys(
    value: ParquetTrajectoryValue,
    experiment: ExperimentName,
) -> tuple[ScientificCellSemanticKey, ...]:
    if isinstance(value, list) and all(type(item) is str for item in value):
        return tuple(value)
    if value is not None and not isinstance(value, str | int | float):
        values = tuple(cast(ParquetStringArray, value).tolist())
        if all(type(item) is str for item in values):
            return values
    raise ValueError(f"{experiment}: state-trajectory source-cell lineage is malformed")
