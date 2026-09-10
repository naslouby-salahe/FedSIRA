from __future__ import annotations

import hashlib
import math
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from enum import StrEnum

import torch

from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
    deterministic_domain_order,
    nbaiot_domain_hash_token,
)
from fedsira.domain.enums import (
    CapabilityContractScope,
    EvaluationInsufficiencyReason,
    RootCause,
    SeedNamespace,
)
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    AdequateFinalGateDomainCount,
    ArtifactDigest,
    DomainCount,
    EligibleEvidenceHolderCount,
    EvidenceArrivalCycleSequence,
    EvidenceCycleIndex,
    FeatureCount,
    FeatureIndex,
    FeatureName,
    FeatureShiftSign,
    FrozenDomainModel,
    HeterogeneityMultiplier,
    MetricValue,
    MinimumEligibleEvidenceHolderCount,
    NamespaceSeed,
    Probability,
    RequiredReproductionRowCount,
    SampleId,
    SamplingCap,
    ScreenLoss,
    SeedDerivationLabel,
    StandardizedValue,
    TriggerFeatureValue,
)
from fedsira.evaluation.summaries import match_nearest_within_decile
from fedsira.protocol.attacks.source import apply_trigger_transform, select_fractional_attack_rows
from fedsira.protocol.specification import first_cycle_with_minimum_eligible_evidence_holders
from fedsira.runtime import deterministic_order, framed_bytes

ROOT_CAUSE_SEPARATOR: SeedDerivationLabel = "CAPABILITY_ROOT_CAUSE"


def root_cause_for_sample(sample_id: SampleId) -> RootCause:
    digest = hashlib.sha256(framed_bytes(ROOT_CAUSE_SEPARATOR, sample_id)).digest()
    parity = int.from_bytes(digest[0:8], byteorder="big", signed=False) % 2
    return RootCause.A if parity == 0 else RootCause.B


def apply_root_cause_feature_shift(
    standardized_features: torch.Tensor,
    root_cause: RootCause,
    root_cause_a_feature_index: FeatureIndex,
    root_cause_b_feature_index: FeatureIndex,
    shift_value: StandardizedValue,
) -> torch.Tensor:
    shifted = standardized_features.clone()
    feature_index = (
        root_cause_a_feature_index if root_cause is RootCause.A else root_cause_b_feature_index
    )
    shifted[..., feature_index] = shifted[..., feature_index] + shift_value
    return shifted


def target_row_ids_for_contract(
    scope: CapabilityContractScope,
    root_cause_a_row_ids: frozenset[SampleId],
    root_cause_b_row_ids: frozenset[SampleId],
) -> frozenset[SampleId]:
    if scope is CapabilityContractScope.BROAD_TARGET_ONLY:
        return root_cause_a_row_ids | root_cause_b_row_ids
    if scope is CapabilityContractScope.ROOT_CAUSE_A_SCOPED:
        return root_cause_a_row_ids
    return root_cause_b_row_ids


def validate_excluded_root_cause_not_supported(
    scope: CapabilityContractScope,
    supported_row_ids: frozenset[SampleId],
    root_cause_a_row_ids: frozenset[SampleId],
    root_cause_b_row_ids: frozenset[SampleId],
) -> None:
    if scope is CapabilityContractScope.ROOT_CAUSE_A_SCOPED and not supported_row_ids.isdisjoint(
        root_cause_b_row_ids
    ):
        raise ValueError("the excluded root cause must never become a supported-control class")
    if scope is CapabilityContractScope.ROOT_CAUSE_B_SCOPED and not supported_row_ids.isdisjoint(
        root_cause_a_row_ids
    ):
        raise ValueError("the excluded root cause must never become a supported-control class")


def balanced_capability_selection(
    root_cause_a_row_ids: Sequence[SampleId],
    root_cause_b_row_ids: Sequence[SampleId],
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[tuple[SampleId, ...], tuple[SampleId, ...]]:
    selected_count = min(len(root_cause_a_row_ids), len(root_cause_b_row_ids))
    separator = SeedNamespace.ATTACK_GENERATION.value
    ordered_a = deterministic_order(
        tuple(root_cause_a_row_ids), separator, attack_generation_namespace_seed
    )
    ordered_b = deterministic_order(
        tuple(root_cause_b_row_ids), separator, attack_generation_namespace_seed
    )
    return ordered_a[:selected_count], ordered_b[:selected_count]


REPRODUCER_ORDER_SEPARATOR = SeedNamespace.REPRODUCER_ORDER.value

_GRADUAL_TO_QUORUM_BREAKPOINTS: tuple[
    tuple[EvidenceCycleIndex, EligibleEvidenceHolderCount],
    ...,
] = (
    (0, 0),
    (2, 1),
    (4, 3),
    (6, 5),
    (8, 8),
)


class EvidenceArrivalSchedule(StrEnum):
    PERMANENT_SINGLETON = "Permanent Singleton"
    ONE_HONEST_HOLDER = "One Honest Holder"
    GRADUAL_TO_QUORUM = "Gradual to Quorum"
    IMMEDIATE_QUORUM = "Immediate Quorum"


def reproducer_order(
    eligible_domains: tuple[NBaiotDomain, ...],
    reproducer_order_namespace_seed: NamespaceSeed,
) -> tuple[NBaiotDomain, ...]:
    return deterministic_domain_order(
        eligible_domains,
        REPRODUCER_ORDER_SEPARATOR,
        reproducer_order_namespace_seed,
    )


def holder_count_at_cycle(
    schedule: EvidenceArrivalSchedule,
    cycle: EvidenceCycleIndex,
    eligible_domain_count: DomainCount,
) -> EligibleEvidenceHolderCount:
    if schedule is EvidenceArrivalSchedule.PERMANENT_SINGLETON:
        return 0
    if schedule is EvidenceArrivalSchedule.ONE_HONEST_HOLDER:
        return 0 if cycle < 2 else min(1, eligible_domain_count)
    if schedule is EvidenceArrivalSchedule.IMMEDIATE_QUORUM:
        return eligible_domain_count
    count: EligibleEvidenceHolderCount = 0
    for breakpoint_cycle, breakpoint_count in _GRADUAL_TO_QUORUM_BREAKPOINTS:
        if cycle >= breakpoint_cycle:
            count = breakpoint_count
    return min(count, eligible_domain_count)


def holders_at_cycle(
    schedule: EvidenceArrivalSchedule,
    cycle: EvidenceCycleIndex,
    target_capable_reproducer_order: tuple[NBaiotDomain, ...],
) -> tuple[NBaiotDomain, ...]:
    count = holder_count_at_cycle(schedule, cycle, len(target_capable_reproducer_order))
    return target_capable_reproducer_order[:count]


def first_holder_cycle_for_domain(
    schedule: EvidenceArrivalSchedule,
    domain: NBaiotDomain,
    target_capable_reproducer_order: tuple[NBaiotDomain, ...],
    candidate_cycles: EvidenceArrivalCycleSequence,
) -> EvidenceCycleIndex | None:
    for cycle in sorted(candidate_cycles):
        if domain in holders_at_cycle(schedule, cycle, target_capable_reproducer_order):
            return cycle
    return None


def _holder_counts_by_cycle(
    schedule: EvidenceArrivalSchedule,
    target_capable_reproducer_order: tuple[NBaiotDomain, ...],
    candidate_cycles: EvidenceArrivalCycleSequence,
) -> tuple[EligibleEvidenceHolderCount, ...]:
    return tuple(
        holder_count_at_cycle(schedule, cycle, len(target_capable_reproducer_order))
        for cycle in candidate_cycles
    )


def cycle_when_requirement_met(
    schedule: EvidenceArrivalSchedule,
    target_capable_reproducer_order: tuple[NBaiotDomain, ...],
    candidate_cycles: EvidenceArrivalCycleSequence,
    requirement_count: MinimumEligibleEvidenceHolderCount,
) -> EvidenceCycleIndex | None:
    counts = _holder_counts_by_cycle(schedule, target_capable_reproducer_order, candidate_cycles)
    index = first_cycle_with_minimum_eligible_evidence_holders(counts, requirement_count)
    if index is None:
        return None
    return candidate_cycles[index]


def compute_t_evidence(
    schedule: EvidenceArrivalSchedule,
    target_capable_reproducer_order: tuple[NBaiotDomain, ...],
    candidate_cycles: EvidenceArrivalCycleSequence,
    reproduction_row_requirement: RequiredReproductionRowCount,
    final_gate_domain_requirement: AdequateFinalGateDomainCount,
) -> EvidenceCycleIndex | None:
    t_reproduction_evidence = cycle_when_requirement_met(
        schedule,
        target_capable_reproducer_order,
        candidate_cycles,
        reproduction_row_requirement,
    )
    t_final_gate = cycle_when_requirement_met(
        schedule,
        target_capable_reproducer_order,
        candidate_cycles,
        final_gate_domain_requirement,
    )
    if t_reproduction_evidence is None or t_final_gate is None:
        return None
    return max(t_reproduction_evidence, t_final_gate)


def select_shared_label_error_rows(
    eligible_benign_row_ids: Sequence[ArtifactDigest],
    strength: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    return select_fractional_attack_rows(
        eligible_benign_row_ids, strength, attack_generation_namespace_seed
    )


def relabel_shared_label_error_rows(
    labels_by_row_id: Mapping[ArtifactDigest, NBaiotClass],
    selected_row_ids: Sequence[ArtifactDigest],
) -> Mapping[ArtifactDigest, NBaiotClass]:
    relabeled: OrderedDict[ArtifactDigest, NBaiotClass] = OrderedDict(labels_by_row_id)
    for row_id in selected_row_ids:
        relabeled[row_id] = NBaiotClass.GAFGYT_COMBO
    return relabeled


def select_spurious_feature_rows(
    eligible_target_row_ids: Sequence[ArtifactDigest],
    strength: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    return select_fractional_attack_rows(
        eligible_target_row_ids, strength, attack_generation_namespace_seed
    )


def apply_shared_spurious_feature(
    standardized_features: torch.Tensor,
    spurious_feature_index: FeatureIndex,
    trigger_value: TriggerFeatureValue,
) -> torch.Tensor:
    return apply_trigger_transform(standardized_features, [spurious_feature_index], trigger_value)


def apply_attacker_induced_common_context(
    standardized_features: torch.Tensor,
    trigger_feature_indices: Sequence[FeatureIndex],
    trigger_value: TriggerFeatureValue,
) -> torch.Tensor:
    return apply_trigger_transform(standardized_features, trigger_feature_indices, trigger_value)


def match_diagnostic_benign_report_test_rows(
    target_report_losses: Sequence[tuple[ArtifactDigest, ScreenLoss]],
    benign_report_test_losses: Sequence[tuple[ArtifactDigest, ScreenLoss]],
) -> tuple[tuple[ArtifactDigest, ArtifactDigest], ...] | None:
    boundary_values = tuple(loss for _, loss in benign_report_test_losses)
    return match_nearest_within_decile(
        tuple(target_report_losses), tuple(benign_report_test_losses), boundary_values
    )


def diagnostic_marker_metric_or_insufficient(
    matched_pairs: tuple[tuple[ArtifactDigest, ArtifactDigest], ...] | None,
    marker_value: MetricValue,
) -> tuple[MetricResult, EvaluationInsufficiencyReason | None]:
    if matched_pairs is None:
        return (
            MetricResult(value=None, denominator=0),
            EvaluationInsufficiencyReason.INSUFFICIENT_MATCHED_BENIGN_REPORT_TEST_CONTROLS,
        )
    return MetricResult(value=marker_value, denominator=len(matched_pairs)), None


QUANTITY_SKEW_SEPARATOR: SeedDerivationLabel = SeedNamespace.HETEROGENEITY.value
HETEROGENEITY_FEATURE_ORDER_SEPARATOR: SeedDerivationLabel = "HETEROGENEITY_FEATURE_ORDER"
HETEROGENEITY_FEATURE_SIGN_SEPARATOR: SeedDerivationLabel = "HETEROGENEITY_FEATURE_SIGN"


class DomainQuantitySkew(FrozenDomainModel):
    domain: NBaiotDomain
    multiplier: HeterogeneityMultiplier


def quantity_skew_multiplier_by_domain(
    heterogeneity_namespace_seed: NamespaceSeed,
    multipliers: tuple[HeterogeneityMultiplier, ...],
) -> tuple[DomainQuantitySkew, ...]:
    if len(multipliers) != len(NBAIOT_DOMAIN_ORDER):
        raise ValueError("quantity-skew multiplier count must match N-BaIoT domain count")
    ordered_domains = deterministic_domain_order(
        NBAIOT_DOMAIN_ORDER,
        QUANTITY_SKEW_SEPARATOR,
        heterogeneity_namespace_seed,
    )
    return tuple(
        DomainQuantitySkew(domain=domain, multiplier=multiplier)
        for domain, multiplier in zip(ordered_domains, multipliers, strict=True)
    )


def exclude_source_from_quantity_skew(
    assignments: tuple[DomainQuantitySkew, ...],
    source_domain: NBaiotDomain,
) -> tuple[DomainQuantitySkew, ...]:
    return tuple(assignment for assignment in assignments if assignment.domain is not source_domain)


def quantity_skew_multiplier_for_domain(
    assignments: tuple[DomainQuantitySkew, ...],
    domain: NBaiotDomain,
) -> HeterogeneityMultiplier:
    for assignment in assignments:
        if assignment.domain is domain:
            return assignment.multiplier
    raise ValueError(f"no quantity-skew multiplier assigned to {domain.value}")


def apply_quantity_skew_to_cap(
    cap: SamplingCap,
    multiplier: HeterogeneityMultiplier,
) -> SamplingCap:
    return math.floor(cap * multiplier)


def select_heterogeneity_shift_features(
    all_feature_names: tuple[FeatureName, ...],
    heterogeneity_namespace_seed: NamespaceSeed,
    selected_feature_count: FeatureCount,
) -> tuple[FeatureName, ...]:
    ordered = deterministic_order(
        all_feature_names,
        HETEROGENEITY_FEATURE_ORDER_SEPARATOR,
        heterogeneity_namespace_seed,
    )
    return ordered[:selected_feature_count]


def feature_shift_sign(
    domain: NBaiotDomain,
    feature_name: FeatureName,
    heterogeneity_namespace_seed: NamespaceSeed,
) -> FeatureShiftSign:
    digest = hashlib.sha256(
        framed_bytes(
            HETEROGENEITY_FEATURE_SIGN_SEPARATOR,
            heterogeneity_namespace_seed,
            nbaiot_domain_hash_token(domain),
            feature_name,
        )
    ).digest()
    return 1 if digest[-1] & 1 else -1
