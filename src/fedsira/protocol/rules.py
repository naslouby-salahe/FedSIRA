import math
from collections.abc import Sequence
from enum import StrEnum

import torch

from fedsira.config import ResourceHorizonConfig
from fedsira.domain.enums import AdmissionState, DormantOrigin, TernaryOutcome
from fedsira.domain.types import (
    AdmissionStateIsTerminal,
    AtLeastTwoByzantineProbability,
    ByzantineDomainCount,
    CommitteeSize,
    CompletionCycleIndex,
    DomainId,
    EligibleEvidenceHolderCount,
    EligiblePoolSize,
    EvidenceAdequate,
    EvidenceArrivalCycleIndex,
    EvidenceCycleIndex,
    KrumCommitteeAdmissible,
    MaximumByzantineReportCount,
    MaximumByzantineReproductionRows,
    MinimumEligibleEvidenceHolderCount,
    MinimumHonestPositiveReportCount,
    NewlyAdequateEvidenceExists,
    ObservedPositiveReportCount,
    UnderlyingVoteIsPositive,
)


def minimum_honest_positive_count(
    observed_positive_count: ObservedPositiveReportCount,
    maximum_byzantine_count: MaximumByzantineReportCount,
) -> MinimumHonestPositiveReportCount:
    return max(observed_positive_count - maximum_byzantine_count, 0)


def krum_minimum_committee_size(
    maximum_byzantine_rows: MaximumByzantineReproductionRows,
) -> CommitteeSize:
    return 2 * maximum_byzantine_rows + 3


def krum_committee_is_admissible(
    committee_size: CommitteeSize,
    maximum_byzantine_rows: MaximumByzantineReproductionRows,
) -> KrumCommitteeAdmissible:
    return committee_size >= krum_minimum_committee_size(maximum_byzantine_rows)


def first_cycle_with_minimum_eligible_evidence_holders(
    eligible_holder_counts_by_cycle: Sequence[EligibleEvidenceHolderCount],
    minimum_required: MinimumEligibleEvidenceHolderCount,
) -> EvidenceArrivalCycleIndex | None:
    for cycle_index, count in enumerate(eligible_holder_counts_by_cycle):
        if count >= minimum_required:
            return cycle_index
    return None


def validate_no_safety_completion_before_tau_k(
    completion_cycle: CompletionCycleIndex,
    tau_k: EvidenceArrivalCycleIndex | None,
) -> None:
    if tau_k is None or completion_cycle < tau_k:
        raise ValueError("safety completion precedes the required evidence-arrival cycle")


def deduplicate_reports_by_proxy(
    reports: Sequence[tuple[DomainId, TernaryOutcome]],
) -> tuple[tuple[DomainId, TernaryOutcome], ...]:
    seen_domains: set[DomainId] = set()
    deduplicated: list[tuple[DomainId, TernaryOutcome]] = []
    for domain, outcome in reports:
        if domain in seen_domains:
            continue
        seen_domains.add(domain)
        deduplicated.append((domain, outcome))
    return tuple(deduplicated)


def report_for_domain(
    deduplicated_reports: Sequence[tuple[DomainId, TernaryOutcome]],
    domain: DomainId,
) -> TernaryOutcome:
    for report_domain, outcome in deduplicated_reports:
        if report_domain == domain:
            return outcome
    raise KeyError(f"no deduplicated report for domain {domain!r}")


def validate_exactly_one_source_domain(source_domains: Sequence[DomainId]) -> None:
    if len(source_domains) != 1:
        raise ValueError(
            f"an admission instance must have exactly one source domain, got {len(source_domains)}"
        )


def diagnostic_at_least_two_byzantine_probability(
    eligible_pool_size: EligiblePoolSize,
    byzantine_domain_count: ByzantineDomainCount,
    committee_size: CommitteeSize,
) -> AtLeastTwoByzantineProbability:
    upper_bound = min(committee_size, byzantine_domain_count)
    numerator = sum(
        math.comb(byzantine_domain_count, compromised_count)
        * math.comb(
            eligible_pool_size - byzantine_domain_count,
            committee_size - compromised_count,
        )
        for compromised_count in range(2, upper_bound + 1)
    )
    denominator = math.comb(eligible_pool_size, committee_size)
    return numerator / denominator


def reproduction_update_vector(
    anchor_flat_parameters: torch.Tensor,
    reproduced_flat_parameters: torch.Tensor,
) -> torch.Tensor:
    return reproduced_flat_parameters - anchor_flat_parameters


class EvidenceArrivalSchedule(StrEnum):
    PERMANENT_SINGLETON = "Permanent Singleton"
    ONE_HONEST_HOLDER = "One Honest Holder"
    GRADUAL_TO_QUORUM = "Gradual to Quorum"
    IMMEDIATE_QUORUM = "Immediate Quorum"


TERMINAL_ADMISSION_STATES = frozenset(
    {AdmissionState.ADMITTED, AdmissionState.REJECTED, AdmissionState.EXPIRED}
)


def is_terminal_state(state: AdmissionState) -> AdmissionStateIsTerminal:
    return state in TERMINAL_ADMISSION_STATES


def apply_logical_cycle_expiry(
    state: AdmissionState,
    logical_cycle: EvidenceCycleIndex,
    resource_horizon_config: ResourceHorizonConfig,
) -> AdmissionState:
    if is_terminal_state(state):
        return state
    if logical_cycle >= resource_horizon_config.maximum_logical_evidence_cycles:
        return AdmissionState.EXPIRED
    return state


_DORMANT_RESUME_STATES: tuple[tuple[DormantOrigin, AdmissionState], ...] = (
    (DormantOrigin.CANDIDATE_SCREEN, AdmissionState.CANDIDATE_SCREEN),
    (DormantOrigin.REPRODUCTION_PENDING, AdmissionState.REPRODUCTION_PENDING),
    (DormantOrigin.SYNTHESIS_PENDING, AdmissionState.SYNTHESIS_PENDING),
)


def _dormant_resume_state(dormant_origin: DormantOrigin) -> AdmissionState:
    for origin, resume_state in _DORMANT_RESUME_STATES:
        if origin is dormant_origin:
            return resume_state
    raise ValueError(f"unknown dormant origin: {dormant_origin.value}")


def resume_dormant_admission(
    dormant_origin: DormantOrigin, newly_adequate_evidence_exists: NewlyAdequateEvidenceExists
) -> AdmissionState:
    if not newly_adequate_evidence_exists:
        return AdmissionState.DORMANT
    return _dormant_resume_state(dormant_origin)


def resolve_ternary_outcome(
    is_evidence_adequate: EvidenceAdequate, underlying_vote_is_positive: UnderlyingVoteIsPositive
) -> TernaryOutcome:
    if not is_evidence_adequate:
        return TernaryOutcome.ABSTAIN
    if underlying_vote_is_positive:
        return TernaryOutcome.POSITIVE
    return TernaryOutcome.NEGATIVE
