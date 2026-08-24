from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import ClaimOpeningMode, ClaimState
from fedsira.evaluation.records import MetricResult
from fedsira.protocol.opening import (
    ScreenDomainResult,
    candidate_free_screen_domain_predicate,
    candidate_screen_transition,
    raw_target_f1_screen_domain_decision_is_positive,
    screen_domain_decision_is_positive,
    screen_domain_order,
    start_claim,
    unmatched_control_screen_domain_decision_is_positive,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
CLAIM_OPENING_CONFIG = CONFIG.protocol.claim_opening
PROPOSAL_SCREEN_CONFIG = CONFIG.protocol.proposal_screen
CAPABILITY_CLAIM_CONFIG = CONFIG.capability_claim


def _results(adequate_flags: list[bool], predicate_flags: list[bool]) -> list[ScreenDomainResult]:
    paired = zip(adequate_flags, predicate_flags, strict=True)
    return [
        ScreenDomainResult(NBAIOT_DOMAIN_ORDER[index], adequate, predicate)
        for index, (adequate, predicate) in enumerate(paired)
    ]


def test_start_claim_proposal_assisted_commits_source_with_zero_weight() -> None:
    entry = start_claim(ClaimOpeningMode.PROPOSAL_ASSISTED)
    assert entry.state is ClaimState.CANDIDATE_SCREEN
    assert entry.source_committed is True
    assert entry.direct_production_weight == 0.0


def test_start_claim_candidate_free_does_not_commit_source() -> None:
    entry = start_claim(ClaimOpeningMode.CANDIDATE_FREE)
    assert entry.source_committed is False


def test_candidate_screen_fewer_than_required_adequate_domains_is_dormant() -> None:
    results = _results([True, False, False], [True, False, False])
    state = candidate_screen_transition(
        ClaimOpeningMode.PROPOSAL_ASSISTED, results, CLAIM_OPENING_CONFIG
    )
    assert state is ClaimState.DORMANT


def test_candidate_screen_proposal_mode_enough_positive_opens_claim() -> None:
    results = _results([True, True, True], [True, True, False])
    state = candidate_screen_transition(
        ClaimOpeningMode.PROPOSAL_ASSISTED, results, CLAIM_OPENING_CONFIG
    )
    assert state is ClaimState.CLAIM_OPEN


def test_candidate_screen_proposal_mode_too_few_positive_is_rejected() -> None:
    results = _results([True, True, True], [True, False, False])
    state = candidate_screen_transition(
        ClaimOpeningMode.PROPOSAL_ASSISTED, results, CLAIM_OPENING_CONFIG
    )
    assert state is ClaimState.REJECTED_CLAIM


def test_candidate_screen_candidate_free_mode_enough_hard_domains_opens_claim() -> None:
    results = _results([True, True, True], [True, True, False])
    state = candidate_screen_transition(
        ClaimOpeningMode.CANDIDATE_FREE, results, CLAIM_OPENING_CONFIG
    )
    assert state is ClaimState.CLAIM_OPEN


def test_candidate_screen_candidate_free_mode_too_few_hard_domains_is_rejected() -> None:
    results = _results([True, True, True], [True, False, False])
    state = candidate_screen_transition(
        ClaimOpeningMode.CANDIDATE_FREE, results, CLAIM_OPENING_CONFIG
    )
    assert state is ClaimState.REJECTED_CLAIM


def test_screen_domain_order_is_deterministic_and_takes_the_configured_prefix() -> None:
    eligible = NBAIOT_DOMAIN_ORDER[:8]
    first = screen_domain_order(eligible, 42, CLAIM_OPENING_CONFIG.screen_domains)
    second = screen_domain_order(eligible, 42, CLAIM_OPENING_CONFIG.screen_domains)
    assert first == second
    assert len(first) == CLAIM_OPENING_CONFIG.screen_domains
    assert set(first).issubset(set(eligible))


def test_screen_domain_decision_is_positive_requires_all_four_predicates() -> None:
    passing = screen_domain_decision_is_positive(
        PROPOSAL_SCREEN_CONFIG.differential_minimum_nats_per_example,
        MetricResult(CAPABILITY_CLAIM_CONFIG.target_f1_gain_over_anchor_minimum, 10),
        MetricResult(CAPABILITY_CLAIM_CONFIG.supported_macro_f1_drop_maximum, 10),
        MetricResult(CAPABILITY_CLAIM_CONFIG.benign_false_alarm_rate_increase_maximum, 10),
        PROPOSAL_SCREEN_CONFIG,
        CAPABILITY_CLAIM_CONFIG,
    )
    assert passing


def test_screen_domain_decision_is_positive_fails_when_differential_too_small() -> None:
    result = screen_domain_decision_is_positive(
        PROPOSAL_SCREEN_CONFIG.differential_minimum_nats_per_example - 0.001,
        MetricResult(1.0, 10),
        MetricResult(0.0, 10),
        MetricResult(0.0, 10),
        PROPOSAL_SCREEN_CONFIG,
        CAPABILITY_CLAIM_CONFIG,
    )
    assert not result


def test_screen_domain_decision_is_positive_na_differential_is_not_positive() -> None:
    result = screen_domain_decision_is_positive(
        None,
        MetricResult(1.0, 10),
        MetricResult(0.0, 10),
        MetricResult(0.0, 10),
        PROPOSAL_SCREEN_CONFIG,
        CAPABILITY_CLAIM_CONFIG,
    )
    assert not result


def test_raw_target_f1_screen_domain_decision_ignores_the_differential() -> None:
    passing = raw_target_f1_screen_domain_decision_is_positive(
        MetricResult(CAPABILITY_CLAIM_CONFIG.target_f1_gain_over_anchor_minimum, 10),
        MetricResult(CAPABILITY_CLAIM_CONFIG.supported_macro_f1_drop_maximum, 10),
        MetricResult(CAPABILITY_CLAIM_CONFIG.benign_false_alarm_rate_increase_maximum, 10),
        CAPABILITY_CLAIM_CONFIG,
    )
    assert passing


def test_raw_target_f1_screen_domain_decision_fails_when_target_gain_too_small() -> None:
    result = raw_target_f1_screen_domain_decision_is_positive(
        MetricResult(CAPABILITY_CLAIM_CONFIG.target_f1_gain_over_anchor_minimum - 0.001, 10),
        MetricResult(0.0, 10),
        MetricResult(0.0, 10),
        CAPABILITY_CLAIM_CONFIG,
    )
    assert not result


def test_unmatched_control_screen_domain_decision_is_positive_requires_all_predicates() -> None:
    passing = unmatched_control_screen_domain_decision_is_positive(
        PROPOSAL_SCREEN_CONFIG.differential_minimum_nats_per_example,
        MetricResult(CAPABILITY_CLAIM_CONFIG.target_f1_gain_over_anchor_minimum, 10),
        MetricResult(CAPABILITY_CLAIM_CONFIG.supported_macro_f1_drop_maximum, 10),
        MetricResult(CAPABILITY_CLAIM_CONFIG.benign_false_alarm_rate_increase_maximum, 10),
        PROPOSAL_SCREEN_CONFIG,
        CAPABILITY_CLAIM_CONFIG,
    )
    assert passing


def test_unmatched_control_screen_domain_decision_na_differential_is_not_positive() -> None:
    result = unmatched_control_screen_domain_decision_is_positive(
        None,
        MetricResult(1.0, 10),
        MetricResult(0.0, 10),
        MetricResult(0.0, 10),
        PROPOSAL_SCREEN_CONFIG,
        CAPABILITY_CLAIM_CONFIG,
    )
    assert not result


def test_candidate_free_screen_domain_predicate_boundary() -> None:
    maximum = CAPABILITY_CLAIM_CONFIG.candidate_free_anchor_target_f1_maximum
    assert candidate_free_screen_domain_predicate(
        MetricResult(maximum - 0.01, 10), CAPABILITY_CLAIM_CONFIG
    )
    assert not candidate_free_screen_domain_predicate(
        MetricResult(maximum, 10), CAPABILITY_CLAIM_CONFIG
    )
    assert not candidate_free_screen_domain_predicate(
        MetricResult(None, 0), CAPABILITY_CLAIM_CONFIG
    )
