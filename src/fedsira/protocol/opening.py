from collections.abc import Sequence
from dataclasses import dataclass

from fedsira.config.schema import ClaimOpeningConfig
from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.domain.enums import ClaimOpeningMode, ClaimState
from fedsira.domain.records import NonNegativeFloat


@dataclass(frozen=True)
class ClaimOpeningEntry:
    state: ClaimState
    source_committed: bool
    direct_production_weight: NonNegativeFloat


def start_claim(opening_mode: ClaimOpeningMode) -> ClaimOpeningEntry:
    return ClaimOpeningEntry(
        state=ClaimState.CANDIDATE_SCREEN,
        source_committed=opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED,
        direct_production_weight=0.0,
    )


@dataclass(frozen=True)
class ScreenDomainResult:
    domain: NBaiotDomain
    is_evidence_adequate: bool
    meets_opening_predicate: bool


def candidate_screen_transition(
    opening_mode: ClaimOpeningMode,
    screen_results: Sequence[ScreenDomainResult],
    claim_opening_config: ClaimOpeningConfig,
) -> ClaimState:
    adequate_results = [result for result in screen_results if result.is_evidence_adequate]
    if len(adequate_results) < claim_opening_config.required_positive_screen_domains:
        return ClaimState.DORMANT

    if opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED:
        required_count = claim_opening_config.required_positive_screen_domains
    else:
        required_count = claim_opening_config.candidate_free_required_adequate_domains

    predicate_count = sum(1 for result in adequate_results if result.meets_opening_predicate)
    if predicate_count >= required_count:
        return ClaimState.CLAIM_OPEN
    return ClaimState.REJECTED_CLAIM
