from enum import StrEnum

from fedsira.datasets.nbaiot.schema import NBaiotDomain, deterministic_domain_order
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import (
    AdequateFinalGateDomainCount,
    DomainCount,
    EligibleEvidenceHolderCount,
    EvidenceArrivalCycleSequence,
    EvidenceCycleIndex,
    MinimumEligibleEvidenceHolderCount,
    NamespaceSeed,
    NonNegativeInt,
    RequiredReproductionRowCount,
)
from fedsira.protocol.theory import first_cycle_with_minimum_eligible_evidence_holders

REPRODUCER_ORDER_SEPARATOR = SeedNamespace.REPRODUCER_ORDER.value

_GRADUAL_TO_QUORUM_BREAKPOINTS: tuple[tuple[NonNegativeInt, NonNegativeInt], ...] = (
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
    count: NonNegativeInt = 0
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
) -> tuple[NonNegativeInt, ...]:
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
