from __future__ import annotations

from collections.abc import Callable

import numpy

from fedsira.domain.enums import AdmissionState, ExperimentLifecycleState
from fedsira.domain.types import ExperimentName, MetricName
from fedsira.evaluation.comparisons import ComparisonFamilyResult
from fedsira.experiments.definitions import (
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    DescriptiveScientificMetric,
)
from fedsira.experiments.execution import (
    CellExecutionOutcome,
    ExecutionRecordStore,
    ExperimentExecutionResult,
)
from fedsira.experiments.planning import ExperimentPlan
from fedsira.reporting.figures import EfficiencyMetricObservation, EvidenceStateFraction
from fedsira.runtime import current_application_context


def efficiency_telemetry(
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[EfficiencyMetricObservation, ...]:
    metric_names: tuple[MetricName, ...] = (
        DescriptiveScientificMetric.WALL_CLOCK_SECONDS.value,
        DescriptiveScientificMetric.COMMUNICATION_BYTES.value,
        DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES.value,
    )
    methods = tuple(sorted(frozenset(outcome.cell.method for outcome in outcomes)))
    observations: list[EfficiencyMetricObservation] = []
    for metric_name in metric_names:
        for method in methods:
            seed_medians = tuple(
                float(numpy.median(values))
                for seed in frozenset(outcome.cell.master_seed for outcome in outcomes)
                if (
                    values := tuple(
                        value
                        for outcome in outcomes
                        if (
                            outcome.completed
                            and outcome.cell.experiment == EFFICIENCY_MEASUREMENT_NAME
                            and outcome.cell.repetition is not None
                            and outcome.cell.method == method
                            and outcome.cell.master_seed == seed
                        )
                        for recorded_metric, value in outcome.metrics
                        if recorded_metric == metric_name and value is not None
                    )
                )
            )
            if seed_medians:
                observations.append(
                    EfficiencyMetricObservation(
                        method=method,
                        metric=metric_name,
                        median=float(numpy.median(seed_medians)),
                        first_quartile=float(numpy.quantile(seed_medians, 0.25, method="linear")),
                        third_quartile=float(numpy.quantile(seed_medians, 0.75, method="linear")),
                        seed_count=len(seed_medians),
                    )
                )
    return tuple(observations)


def evidence_trajectory(
    store: ExecutionRecordStore,
) -> tuple[EvidenceStateFraction, ...]:
    records = tuple(
        record
        for record in store.read_all_outcomes(EVIDENCE_SCARCITY_AND_DORMANCY_NAME)
        if record.terminal_state is ExperimentLifecycleState.COMPLETED
    )
    if not records:
        return ()
    if any(not record.state_trajectory for record in records):
        raise ValueError("Evidence Scarcity and Dormancy record lacks its state trajectory")
    resource_horizon = current_application_context().scientific_config.protocol.resource_horizon
    horizon = resource_horizon.maximum_logical_evidence_cycles
    result: list[EvidenceStateFraction] = []
    states = (
        AdmissionState.DORMANT,
        AdmissionState.VERIFICATION_PENDING,
        AdmissionState.ADMITTED,
        AdmissionState.EXPIRED,
    )
    for schedule in sorted(frozenset(record.condition for record in records)):
        schedule_records = tuple(record for record in records if record.condition == schedule)
        for cycle in range(horizon + 1):
            for state in states:
                count = sum(
                    1
                    for record in schedule_records
                    if next(
                        (
                            observation.state
                            for observation in record.state_trajectory
                            if observation.cycle == cycle
                        ),
                        None,
                    )
                    is state
                )
                if count:
                    result.append(
                        EvidenceStateFraction(
                            condition=schedule,
                            cycle=cycle,
                            state=state,
                            fraction=count / len(schedule_records),
                        )
                    )
    return tuple(result)


def outcome_evidence_trajectory(
    outcomes: tuple[CellExecutionOutcome, ...],
) -> tuple[EvidenceStateFraction, ...]:
    completed = tuple(outcome for outcome in outcomes if outcome.completed)
    if not completed:
        raise ValueError("Evidence Scarcity and Dormancy has no completed state evidence")
    scientific_config = current_application_context().scientific_config
    horizon = scientific_config.protocol.resource_horizon.maximum_logical_evidence_cycles
    if any(not outcome.state_trajectory for outcome in completed):
        raise ValueError("Evidence Scarcity and Dormancy outcome lacks its state trajectory")
    result: list[EvidenceStateFraction] = []
    states = (
        AdmissionState.DORMANT,
        AdmissionState.VERIFICATION_PENDING,
        AdmissionState.ADMITTED,
        AdmissionState.EXPIRED,
    )
    for schedule in sorted(frozenset(outcome.cell.condition for outcome in completed)):
        schedule_outcomes = tuple(
            outcome for outcome in completed if outcome.cell.condition == schedule
        )
        for cycle in range(horizon + 1):
            for state in states:
                count = sum(
                    1
                    for outcome in schedule_outcomes
                    if next(
                        (
                            observation.state
                            for observation in outcome.state_trajectory
                            if observation.cycle == cycle
                        ),
                        None,
                    )
                    is state
                )
                if count:
                    result.append(
                        EvidenceStateFraction(
                            condition=schedule,
                            cycle=cycle,
                            state=state,
                            fraction=count / len(schedule_outcomes),
                        )
                    )
    return tuple(result)


def project_result_evidence(
    plan: ExperimentPlan,
    load_result: Callable[[ExperimentName], ExperimentExecutionResult],
) -> tuple[tuple[ComparisonFamilyResult, ...], tuple[CellExecutionOutcome, ...]]:
    results = tuple(load_result(planned.definition.name) for planned in plan.experiments)
    return (
        tuple(comparison for result in results for comparison in result.comparison_results),
        tuple(outcome for result in results for outcome in result.outcomes),
    )
