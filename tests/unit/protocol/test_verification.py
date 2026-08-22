from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import ClaimState, TernaryOutcome
from fedsira.protocol.verification import (
    byzantine_selection_order,
    construct_above_bound_panel,
    deterministic_verifier_panel,
    diagnostic_committee_panel,
    panel_votes_are_one_per_domain,
    reproduction_row_is_certified,
    select_compromised_verifiers,
    verification_pending_transition,
    verifier_assignment_seed_for_row,
    verifier_assignment_timestamp_is_valid,
    verifier_is_eligible,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
VERIFICATION_CONFIG = CONFIG.protocol.verification
DOMAIN_A, DOMAIN_B, DOMAIN_C, DOMAIN_D = NBAIOT_DOMAIN_ORDER[:4]


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


def test_verifier_assignment_seed_for_row_is_deterministic_and_row_specific() -> None:
    first = verifier_assignment_seed_for_row(42, "c" * 64)
    second = verifier_assignment_seed_for_row(42, "c" * 64)
    assert first == second
    assert verifier_assignment_seed_for_row(42, "d" * 64) != first


def test_deterministic_verifier_panel_is_deterministic_and_bounded() -> None:
    eligible = NBAIOT_DOMAIN_ORDER[:7]
    seed = verifier_assignment_seed_for_row(42, "c" * 64)
    first = deterministic_verifier_panel(eligible, seed, VERIFICATION_CONFIG.panel_size)
    second = deterministic_verifier_panel(eligible, seed, VERIFICATION_CONFIG.panel_size)
    assert first == second
    assert len(first) == VERIFICATION_CONFIG.panel_size
    assert set(first).issubset(set(eligible))


def test_byzantine_selection_order_is_deterministic() -> None:
    eligible = NBAIOT_DOMAIN_ORDER[:7]
    first = byzantine_selection_order(eligible, 7)
    second = byzantine_selection_order(eligible, 7)
    assert first == second
    assert set(first) == set(eligible)


def test_select_compromised_verifiers_takes_the_configured_prefix() -> None:
    order = (DOMAIN_A, DOMAIN_B, DOMAIN_C, DOMAIN_D)
    assert select_compromised_verifiers(order, 1) == frozenset({DOMAIN_A})
    assert select_compromised_verifiers(order, 0) == frozenset()


def test_construct_above_bound_panel_places_compromised_first_then_fills_honest() -> None:
    compromised = (DOMAIN_A, DOMAIN_B)
    honest_order = (DOMAIN_C, DOMAIN_D)
    panel = construct_above_bound_panel(compromised, honest_order, panel_size=3)
    assert panel == (DOMAIN_A, DOMAIN_B, DOMAIN_C)
    assert len(panel) == 3


def test_diagnostic_committee_panel_is_deterministic_and_bounded() -> None:
    eligible = NBAIOT_DOMAIN_ORDER[:7]
    first = diagnostic_committee_panel(eligible, 42, 3)
    second = diagnostic_committee_panel(eligible, 42, 3)
    assert first == second
    assert len(first) == 3
    assert set(first).issubset(set(eligible))


def test_reproduction_row_is_certified_requires_full_panel_and_threshold() -> None:
    assert reproduction_row_is_certified(
        [TernaryOutcome.POSITIVE, TernaryOutcome.POSITIVE, TernaryOutcome.NEGATIVE], 3, 2
    )
    assert not reproduction_row_is_certified(
        [TernaryOutcome.POSITIVE, TernaryOutcome.NEGATIVE, TernaryOutcome.NEGATIVE], 3, 2
    )
    assert not reproduction_row_is_certified(
        [TernaryOutcome.POSITIVE, TernaryOutcome.POSITIVE], 3, 2
    )


def test_reproduction_row_is_certified_counts_only_positive_among_non_abstaining() -> None:
    assert reproduction_row_is_certified(
        [TernaryOutcome.POSITIVE, TernaryOutcome.POSITIVE, TernaryOutcome.ABSTAIN], 3, 2
    )
