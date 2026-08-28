from collections.abc import Sequence

from fedsira.config.schema import CapabilityClaimConfig, ClaimOpeningConfig, ProposalScreenConfig
from fedsira.domain.enums import ClaimOpeningMode, ClaimState, SeedNamespace
from fedsira.domain.records import (
    BooleanFlag,
    DifferentialNatsPerExample,
    DomainId,
    EvidenceAdequate,
    FrozenDomainModel,
    NamespaceSeed,
    OpeningPredicateSatisfied,
    ProductionWeight,
    ScreenDomainCount,
    SourceCommitted,
)
from fedsira.evaluation.records import MetricResult
from fedsira.runtime.determinism import deterministic_order

SCREEN_DOMAIN_ORDER_SEPARATOR = SeedNamespace.SCREEN_DOMAIN_ORDER.value


class ClaimOpeningEntry(FrozenDomainModel):
    state: ClaimState
    source_committed: SourceCommitted
    direct_production_weight: ProductionWeight


def start_claim(opening_mode: ClaimOpeningMode) -> ClaimOpeningEntry:
    return ClaimOpeningEntry(
        state=ClaimState.CANDIDATE_SCREEN,
        source_committed=opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED,
        direct_production_weight=0.0,
    )


class ScreenDomainResult(FrozenDomainModel):
    domain: DomainId
    is_evidence_adequate: EvidenceAdequate
    meets_opening_predicate: OpeningPredicateSatisfied


def screen_domain_order(
    eligible_non_source_domains: Sequence[DomainId],
    screen_domain_order_namespace_seed: NamespaceSeed,
    screen_domain_count: ScreenDomainCount,
) -> tuple[DomainId, ...]:
    ordered = deterministic_order(
        eligible_non_source_domains,
        SCREEN_DOMAIN_ORDER_SEPARATOR,
        screen_domain_order_namespace_seed,
    )
    return ordered[:screen_domain_count]


def screen_domain_decision_is_positive(
    differential_a: DifferentialNatsPerExample | None,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    proposal_screen_config: ProposalScreenConfig,
    capability_claim_config: CapabilityClaimConfig,
) -> BooleanFlag:
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


def raw_target_f1_screen_domain_decision_is_positive(
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    capability_claim_config: CapabilityClaimConfig,
) -> BooleanFlag:
    if (
        target_f1_gain.value is None
        or supported_macro_f1_drop.value is None
        or benign_far_increase.value is None
    ):
        return False
    return (
        target_f1_gain.value >= capability_claim_config.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value <= capability_claim_config.supported_macro_f1_drop_maximum
        and benign_far_increase.value
        <= capability_claim_config.benign_false_alarm_rate_increase_maximum
    )


def unmatched_control_screen_domain_decision_is_positive(
    unmatched_differential: DifferentialNatsPerExample | None,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
    proposal_screen_config: ProposalScreenConfig,
    capability_claim_config: CapabilityClaimConfig,
) -> BooleanFlag:
    if unmatched_differential is None:
        return False
    if (
        target_f1_gain.value is None
        or supported_macro_f1_drop.value is None
        or benign_far_increase.value is None
    ):
        return False
    return (
        unmatched_differential >= proposal_screen_config.differential_minimum_nats_per_example
        and target_f1_gain.value >= capability_claim_config.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value <= capability_claim_config.supported_macro_f1_drop_maximum
        and benign_far_increase.value
        <= capability_claim_config.benign_false_alarm_rate_increase_maximum
    )


def candidate_free_screen_domain_predicate(
    anchor_target_f1: MetricResult, capability_claim_config: CapabilityClaimConfig
) -> BooleanFlag:
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
