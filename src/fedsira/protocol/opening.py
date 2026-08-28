import hashlib
from collections.abc import Mapping, Sequence

from fedsira.config.schema import CapabilityClaimConfig, ClaimOpeningConfig, ProposalScreenConfig
from fedsira.domain.enums import ClaimOpeningMode, ClaimState, SeedNamespace
from fedsira.domain.records import (
    BooleanFlag,
    CanonicalToken,
    DerivedSeed,
    DomainId,
    EvidenceAdequate,
    FoldCount,
    FoldIndex,
    FrozenDomainModel,
    NamespaceSeed,
    OpeningPredicateSatisfied,
    ProductionWeight,
    ScreenDifferential,
    ScreenDomainCount,
    ScreenLoss,
    SourceCommitted,
)
from fedsira.evaluation.aggregation import match_nearest_within_decile
from fedsira.evaluation.records import MetricResult
from fedsira.runtime.determinism import canonical_bytes, deterministic_order

SCREEN_DOMAIN_ORDER_SEPARATOR = SeedNamespace.SCREEN_DOMAIN_ORDER.value
SCREEN_FOLD_SEPARATOR = SeedNamespace.SCREEN_FOLD.value
SOURCE_SELECTION_SEPARATOR = SeedNamespace.SOURCE_SELECTION.value


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


class ScreenLossObservation(FrozenDomainModel):
    sample_id: CanonicalToken
    anchor_loss: ScreenLoss
    source_loss: ScreenLoss


def source_selection_order(
    eligible_domains: Sequence[DomainId],
    source_selection_namespace_seed: NamespaceSeed,
) -> tuple[DomainId, ...]:
    return deterministic_order(
        eligible_domains,
        SOURCE_SELECTION_SEPARATOR,
        source_selection_namespace_seed,
    )


def select_source_domain(
    source_order: Sequence[DomainId],
    domains_with_target_stream: frozenset[DomainId],
    requires_attack_carrier: BooleanFlag,
    domains_with_attack_carrier: frozenset[DomainId],
) -> DomainId | None:
    for domain in source_order:
        if domain not in domains_with_target_stream:
            continue
        if requires_attack_carrier and domain not in domains_with_attack_carrier:
            continue
        return domain
    return None


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


def screen_fold_index(
    sample_id: CanonicalToken,
    screen_fold_seed: DerivedSeed,
    fold_count: FoldCount,
) -> FoldIndex:
    digest = hashlib.sha256(
        canonical_bytes(SCREEN_FOLD_SEPARATOR, screen_fold_seed, sample_id)
    ).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % fold_count


def match_held_out_fold(
    held_out_targets: Sequence[ScreenLossObservation],
    held_out_controls: Sequence[ScreenLossObservation],
    other_fold_controls: Sequence[ScreenLossObservation],
) -> tuple[tuple[ScreenLossObservation, ScreenLossObservation], ...] | None:
    targets_by_id = {observation.sample_id: observation for observation in held_out_targets}
    controls_by_id = {observation.sample_id: observation for observation in held_out_controls}
    matched_ids = match_nearest_within_decile(
        [(observation.sample_id, observation.anchor_loss) for observation in held_out_targets],
        [(observation.sample_id, observation.anchor_loss) for observation in held_out_controls],
        [observation.anchor_loss for observation in other_fold_controls],
    )
    if matched_ids is None:
        return None
    return tuple(
        (targets_by_id[target_id], controls_by_id[control_id])
        for target_id, control_id in matched_ids
    )


def proposal_screen_differential(
    matched_pairs: Sequence[tuple[ScreenLossObservation, ScreenLossObservation]],
) -> ScreenDifferential | None:
    if len(matched_pairs) == 0:
        return None
    target_deltas = [target.anchor_loss - target.source_loss for target, _ in matched_pairs]
    control_deltas = [control.anchor_loss - control.source_loss for _, control in matched_pairs]
    differential_target = sum(target_deltas) / len(target_deltas)
    differential_control = sum(control_deltas) / len(control_deltas)
    return differential_target - differential_control


def run_proposal_screen_for_domain(
    fold_assignment_by_sample_id: Mapping[CanonicalToken, FoldIndex],
    target_observations: Sequence[ScreenLossObservation],
    control_observations: Sequence[ScreenLossObservation],
    fold_count: FoldCount,
) -> ScreenDifferential | None:
    all_matches: list[tuple[ScreenLossObservation, ScreenLossObservation]] = []
    for held_out_fold in range(fold_count):
        held_out_targets = [
            observation
            for observation in target_observations
            if fold_assignment_by_sample_id[observation.sample_id] == held_out_fold
        ]
        held_out_controls = [
            observation
            for observation in control_observations
            if fold_assignment_by_sample_id[observation.sample_id] == held_out_fold
        ]
        other_fold_controls = [
            observation
            for observation in control_observations
            if fold_assignment_by_sample_id[observation.sample_id] != held_out_fold
        ]
        fold_matches = match_held_out_fold(held_out_targets, held_out_controls, other_fold_controls)
        if fold_matches is None:
            return None
        all_matches.extend(fold_matches)
    return proposal_screen_differential(all_matches)


def screen_domain_decision_is_positive(
    differential_a: ScreenDifferential | None,
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
    unmatched_differential: ScreenDifferential | None,
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
