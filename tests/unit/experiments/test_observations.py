from fedsira.domain.enums import (
    AdmissionState,
    ComparisonMetric,
    DescriptiveScientificMetric,
)
from fedsira.experiments.observations import (
    declared_contract_scopes,
    measurement_cycles,
    observation_value,
    observations_with_replacements,
    permanent_singleton_admission,
)
from fedsira.runtime import current_application_context


def test_resource_measurement_cycles_follow_configured_horizon() -> None:
    horizon = current_application_context().scientific_config.protocol.resource_horizon

    assert measurement_cycles(horizon) == tuple(
        range(horizon.measurement_cycle_start, horizon.measurement_cycle_end + 1)
    )


def test_declared_contract_scopes_use_the_configured_capability_contract() -> None:
    assert declared_contract_scopes() == tuple(
        current_application_context().scientific_config.attacks_and_boundaries.capability_under_specification.contracts
    )


def test_observation_value_and_replacement_preserve_other_metrics() -> None:
    observations = (
        (ComparisonMetric.TARGET_F1, 0.8),
        (ComparisonMetric.ATTACK_SUCCESS_RATE, 0.2),
    )
    replacements = ((ComparisonMetric.TARGET_F1, 0.9),)

    assert observation_value(observations, ComparisonMetric.TARGET_F1) == 0.8
    assert observations_with_replacements(observations, replacements) == (
        (ComparisonMetric.TARGET_F1, 0.9),
        (ComparisonMetric.ATTACK_SUCCESS_RATE, 0.2),
    )


def test_permanent_singleton_admission_requires_one_or_fewer_holders() -> None:
    assert permanent_singleton_admission(AdmissionState.ADMITTED, (0, 1)) == (
        DescriptiveScientificMetric.PERMANENT_SINGLETON_ADMISSION,
        1.0,
    )
    assert permanent_singleton_admission(AdmissionState.ADMITTED, (1, 2)) == (
        DescriptiveScientificMetric.PERMANENT_SINGLETON_ADMISSION,
        0.0,
    )
