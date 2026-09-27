from fedsira.config import ResourceHorizonConfig
from fedsira.domain.enums import (
    AdmissionState,
    CapabilityContractScope,
    DescriptiveScientificMetric,
    ExperimentName,
)
from fedsira.domain.types import (
    EligibleEvidenceHolderCount,
    EvidenceCycleIndex,
    MethodName,
    MetricName,
    MetricObservation,
    MetricValue,
    ScenarioName,
)
from fedsira.evaluation.statistics import mean_of_defined_values as mean_of_defined
from fedsira.experiments.engine import CellExecutionOutcome
from fedsira.runtime import current_application_context


def measurement_cycles(
    resource_horizon: ResourceHorizonConfig,
) -> tuple[EvidenceCycleIndex, ...]:
    return tuple(
        range(
            resource_horizon.measurement_cycle_start,
            resource_horizon.measurement_cycle_end + 1,
        )
    )


def declared_contract_scopes() -> tuple[CapabilityContractScope, ...]:
    boundaries = current_application_context().scientific_config.attacks_and_boundaries
    return tuple(boundaries.capability_under_specification.contracts)


def permanent_singleton_admission(
    state: AdmissionState, holder_counts: tuple[EligibleEvidenceHolderCount, ...]
) -> MetricObservation:
    sustained = bool(holder_counts) and max(holder_counts) <= 1
    return (
        DescriptiveScientificMetric.PERMANENT_SINGLETON_ADMISSION,
        float(state is AdmissionState.ADMITTED and sustained),
    )


def observation_value(
    observations: tuple[MetricObservation, ...], metric: MetricName
) -> MetricValue | None:
    for metric_name, metric_value in reversed(observations):
        if metric_name == metric:
            return metric_value
    return None


def observations_with_replacements(
    observations: tuple[MetricObservation, ...],
    replacements: tuple[MetricObservation, ...],
) -> tuple[MetricObservation, ...]:
    replaced = tuple(
        (metric_name, observation_value(replacements, metric_name))
        if any(name == metric_name for name, _value in replacements)
        else (metric_name, metric_value)
        for metric_name, metric_value in observations
    )
    appended = tuple(
        replacement
        for replacement in replacements
        if not any(name == replacement[0] for name, _value in observations)
    )
    return (*replaced, *appended)


def outcome_metric_values(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> tuple[MetricValue, ...]:
    return tuple(
        value
        for outcome in sorted(outcomes, key=lambda item: item.cell.master_seed)
        if (
            outcome.completed
            and outcome.cell.experiment == experiment
            and outcome.cell.method == method
            and outcome.cell.condition == scenario
        )
        for metric_name, value in outcome.metrics
        if metric_name == metric and value is not None
    )


def outcome_metric_mean(
    outcomes: tuple[CellExecutionOutcome, ...],
    experiment: ExperimentName,
    method: MethodName,
    scenario: ScenarioName,
    metric: MetricName,
) -> MetricValue | None:
    return mean_of_defined(outcome_metric_values(outcomes, experiment, method, scenario, metric))
