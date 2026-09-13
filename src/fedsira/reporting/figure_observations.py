from __future__ import annotations

from fedsira.domain.enums import AdmissionState
from fedsira.domain.types import (
    EvidenceCycleIndex,
    FrozenDomainModel,
    MethodName,
    MetricName,
    MetricValue,
    Probability,
    ScenarioName,
    ScientificCellCount,
)
#TODO:  move this whole file to figures.py instead of having it separate

class EvidenceStateFraction(FrozenDomainModel):
    condition: ScenarioName
    cycle: EvidenceCycleIndex
    state: AdmissionState
    fraction: Probability


class EfficiencyMetricObservation(FrozenDomainModel):
    method: MethodName
    metric: MetricName
    median: MetricValue
    first_quartile: MetricValue
    third_quartile: MetricValue
    seed_count: ScientificCellCount


def state_fraction(
    observations: tuple[EvidenceStateFraction, ...],
    condition: ScenarioName,
    cycle: EvidenceCycleIndex,
    state: AdmissionState,
) -> Probability:
    for observation in observations:
        if (
            observation.condition == condition
            and observation.cycle == cycle
            and observation.state is state
        ):
            return observation.fraction
    return 0.0


def efficiency_observation(
    observations: tuple[EfficiencyMetricObservation, ...],
    method: MethodName,
    metric: MetricName,
) -> EfficiencyMetricObservation:
    for observation in observations:
        if observation.method == method and observation.metric == metric:
            return observation
    raise ValueError(f"missing efficiency telemetry for {method} / {metric}")
