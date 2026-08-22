from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import ClaimOpeningMode, ClaimState
from fedsira.protocol.opening import ScreenDomainResult, candidate_screen_transition, start_claim

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
CLAIM_OPENING_CONFIG = CONFIG.protocol.claim_opening


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
