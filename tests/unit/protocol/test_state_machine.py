from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import AdmissionState, DormantOrigin, TernaryOutcome
from fedsira.protocol.state_machine import (
    TERMINAL_ADMISSION_STATES,
    apply_logical_cycle_expiry,
    is_terminal_state,
    resolve_ternary_outcome,
    resume_dormant_admission,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
RESOURCE_HORIZON_CONFIG = CONFIG.protocol.resource_horizon


def test_terminal_states_are_exactly_admitted_rejected_expired() -> None:
    assert {
        AdmissionState.ADMITTED,
        AdmissionState.REJECTED,
        AdmissionState.EXPIRED,
    } == TERMINAL_ADMISSION_STATES
    for state in TERMINAL_ADMISSION_STATES:
        assert is_terminal_state(state)
    assert not is_terminal_state(AdmissionState.DORMANT)


def test_apply_logical_cycle_expiry_expires_at_the_configured_horizon() -> None:
    maximum = RESOURCE_HORIZON_CONFIG.maximum_logical_evidence_cycles
    assert (
        apply_logical_cycle_expiry(
            AdmissionState.REPRODUCTION_PENDING, maximum - 1, RESOURCE_HORIZON_CONFIG
        )
        is AdmissionState.REPRODUCTION_PENDING
    )
    assert (
        apply_logical_cycle_expiry(
            AdmissionState.REPRODUCTION_PENDING, maximum, RESOURCE_HORIZON_CONFIG
        )
        is AdmissionState.EXPIRED
    )


def test_apply_logical_cycle_expiry_never_overrides_a_terminal_state() -> None:
    maximum = RESOURCE_HORIZON_CONFIG.maximum_logical_evidence_cycles
    assert (
        apply_logical_cycle_expiry(AdmissionState.ADMITTED, maximum, RESOURCE_HORIZON_CONFIG)
        is AdmissionState.ADMITTED
    )


def test_resume_dormant_admission_returns_to_its_origin_phase() -> None:
    assert (
        resume_dormant_admission(DormantOrigin.CANDIDATE_SCREEN, True)
        is AdmissionState.CANDIDATE_SCREEN
    )
    assert (
        resume_dormant_admission(DormantOrigin.REPRODUCTION_PENDING, True)
        is AdmissionState.REPRODUCTION_PENDING
    )
    assert (
        resume_dormant_admission(DormantOrigin.SYNTHESIS_PENDING, True)
        is AdmissionState.SYNTHESIS_PENDING
    )


def test_resume_dormant_admission_stays_dormant_without_new_evidence() -> None:
    assert (
        resume_dormant_admission(DormantOrigin.REPRODUCTION_PENDING, False)
        is AdmissionState.DORMANT
    )


def test_resolve_ternary_outcome_abstains_on_inadequate_evidence() -> None:
    assert resolve_ternary_outcome(False, True) is TernaryOutcome.ABSTAIN
    assert resolve_ternary_outcome(False, False) is TernaryOutcome.ABSTAIN


def test_resolve_ternary_outcome_reports_positive_or_negative_when_adequate() -> None:
    assert resolve_ternary_outcome(True, True) is TernaryOutcome.POSITIVE
    assert resolve_ternary_outcome(True, False) is TernaryOutcome.NEGATIVE
