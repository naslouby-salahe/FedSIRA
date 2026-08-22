from collections.abc import Sequence
from dataclasses import dataclass

from fedsira.config.schema import CapabilityClaimConfig, ClaimOpeningConfig, ProposalScreenConfig
from fedsira.datasets.nbaiot.schema import NBaiotDomain, deterministic_domain_order
from fedsira.domain.enums import ClaimOpeningMode, ClaimState
from fedsira.domain.records import NamespaceSeed, NonNegativeFloat, PositiveInt
from fedsira.evaluation.records import MetricResult

SCREEN_DOMAIN_ORDER_SEPARATOR = "SCREEN_DOMAIN_ORDER"


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


def screen_domain_order(
    eligible_non_source_domains: Sequence[NBaiotDomain],
    screen_domain_order_namespace_seed: NamespaceSeed,
    screen_domain_count: PositiveInt,
) -> tuple[NBaiotDomain, ...]:
    ordered = deterministic_domain_order(
        eligible_non_source_domains,
        SCREEN_DOMAIN_ORDER_SEPARATOR,
        screen_domain_order_namespace_seed,
    )
    return ordered[:screen_domain_count]


def screen_domain_decision_is_positive(
    differential_a: float | None,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    proposal_screen_config: ProposalScreenConfig,
    capability_claim_config: CapabilityClaimConfig,
) -> bool:
    if differential_a is None:
        return False
    if (
        target_f1_gain.value is None
        or supported_macro_f1_drop.value is None
        or benign_far_increase.value is None
    ):
        return False
    return (
        differential_a >= proposal_screen_config.differential_minimum_nats_per_example
        and target_f1_gain.value >= capability_claim_config.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value <= capability_claim_config.supported_macro_f1_drop_maximum
        and benign_far_increase.value
        <= capability_claim_config.benign_false_alarm_rate_increase_maximum
    )


def candidate_free_screen_domain_predicate(
    anchor_target_f1: MetricResult, capability_claim_config: CapabilityClaimConfig
) -> bool:
    if anchor_target_f1.value is None:
        return False
    return anchor_target_f1.value < capability_claim_config.candidate_free_anchor_target_f1_maximum


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
