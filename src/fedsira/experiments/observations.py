from fedsira.config import ResourceHorizonConfig
from fedsira.domain.enums import AdmissionState, CapabilityContractScope
from fedsira.domain.types import (
    EligibleEvidenceHolderCount,
    EvidenceCycleIndex,
    MetricName,
    MetricObservation,
    MetricValue,
)
from fedsira.experiments.definitions import DescriptiveScientificMetric
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


def mean_of_defined(values: tuple[MetricValue | None, ...]) -> MetricValue | None:
    defined = tuple(value for value in values if value is not None)
    if not defined:
        return None
    return sum(defined) / len(defined)
