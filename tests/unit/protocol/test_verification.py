from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import ClaimState
from fedsira.protocol.verification import (
    panel_votes_are_one_per_domain,
    verification_pending_transition,
    verifier_assignment_timestamp_is_valid,
    verifier_is_eligible,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
VERIFICATION_CONFIG = CONFIG.protocol.verification
DOMAIN_A, DOMAIN_B, DOMAIN_C = NBAIOT_DOMAIN_ORDER[:3]


def test_verifier_is_eligible_excludes_reproducer_and_source() -> None:
    assert not verifier_is_eligible(DOMAIN_A, DOMAIN_B, reproducer_domain=DOMAIN_A)
    assert not verifier_is_eligible(DOMAIN_A, source_domain=DOMAIN_A, reproducer_domain=DOMAIN_B)
    assert verifier_is_eligible(DOMAIN_C, DOMAIN_B, reproducer_domain=DOMAIN_A)


def test_verifier_assignment_timestamp_must_be_strictly_later() -> None:
    assert verifier_assignment_timestamp_is_valid(2.0, 1.0)
    assert not verifier_assignment_timestamp_is_valid(1.0, 1.0)
    assert not verifier_assignment_timestamp_is_valid(0.5, 1.0)


def test_panel_votes_are_one_per_domain() -> None:
    assert panel_votes_are_one_per_domain([DOMAIN_A, DOMAIN_B, DOMAIN_C])
    assert not panel_votes_are_one_per_domain([DOMAIN_A, DOMAIN_A, DOMAIN_C])


def test_verification_pending_transition_insufficient_panel_is_uncertified() -> None:
    state = verification_pending_transition(2, 2, True, VERIFICATION_CONFIG)
    assert state is ClaimState.REPRODUCTION_PENDING


def test_verification_pending_transition_panel_fails_threshold() -> None:
    state = verification_pending_transition(3, 1, True, VERIFICATION_CONFIG)
    assert state is ClaimState.REPRODUCTION_PENDING


def test_verification_pending_transition_passes_but_row_requirement_not_reached() -> None:
    state = verification_pending_transition(3, 2, False, VERIFICATION_CONFIG)
    assert state is ClaimState.REPRODUCTION_PENDING


def test_verification_pending_transition_passes_and_row_requirement_reached() -> None:
    state = verification_pending_transition(3, 2, True, VERIFICATION_CONFIG)
    assert state is ClaimState.SYNTHESIS_PENDING
