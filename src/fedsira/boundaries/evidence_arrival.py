from collections.abc import Sequence
from enum import StrEnum

from fedsira.datasets.nbaiot.schema import NBaiotDomain, deterministic_domain_order
from fedsira.domain.records import NamespaceSeed, NonNegativeInt, PositiveInt
from fedsira.protocol.theory import first_cycle_with_minimum_eligible_evidence_holders

REPRODUCER_ORDER_SEPARATOR = "REPRODUCER_ORDER"

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
    eligible_domains: Sequence[NBaiotDomain], reproducer_order_namespace_seed: NamespaceSeed
) -> tuple[NBaiotDomain, ...]:
    return deterministic_domain_order(
        eligible_domains, REPRODUCER_ORDER_SEPARATOR, reproducer_order_namespace_seed
    )


def holder_count_at_cycle(
    schedule: EvidenceArrivalSchedule, cycle: NonNegativeInt, eligible_domain_count: NonNegativeInt
) -> NonNegativeInt:
    if schedule is EvidenceArrivalSchedule.PERMANENT_SINGLETON:
        return 0
    if schedule is EvidenceArrivalSchedule.ONE_HONEST_HOLDER:
        return 0 if cycle < 2 else min(1, eligible_domain_count)
    if schedule is EvidenceArrivalSchedule.IMMEDIATE_QUORUM:
        return eligible_domain_count
    count = 0
    for breakpoint_cycle, breakpoint_count in _GRADUAL_TO_QUORUM_BREAKPOINTS:
        if cycle >= breakpoint_cycle:
            count = breakpoint_count
    return min(count, eligible_domain_count)


def holders_at_cycle(
    schedule: EvidenceArrivalSchedule,
    cycle: NonNegativeInt,
    target_capable_reproducer_order: Sequence[NBaiotDomain],
) -> tuple[NBaiotDomain, ...]:
    count = holder_count_at_cycle(schedule, cycle, len(target_capable_reproducer_order))
    return tuple(target_capable_reproducer_order[:count])


def first_holder_cycle_for_domain(
    schedule: EvidenceArrivalSchedule,
    domain: NBaiotDomain,
    target_capable_reproducer_order: Sequence[NBaiotDomain],
    candidate_cycles: Sequence[NonNegativeInt],
) -> NonNegativeInt | None:
    for cycle in sorted(candidate_cycles):
        if domain in holders_at_cycle(schedule, cycle, target_capable_reproducer_order):
            return cycle
    return None


def _holder_counts_by_cycle(
    schedule: EvidenceArrivalSchedule,
    target_capable_reproducer_order: Sequence[NBaiotDomain],
    candidate_cycles: Sequence[NonNegativeInt],
) -> list[NonNegativeInt]:
    return [
        holder_count_at_cycle(schedule, cycle, len(target_capable_reproducer_order))
        for cycle in candidate_cycles
    ]


def cycle_when_requirement_met(
    schedule: EvidenceArrivalSchedule,
    target_capable_reproducer_order: Sequence[NBaiotDomain],
    candidate_cycles: Sequence[NonNegativeInt],
    requirement_count: PositiveInt,
) -> NonNegativeInt | None:
    counts = _holder_counts_by_cycle(schedule, target_capable_reproducer_order, candidate_cycles)
    index = first_cycle_with_minimum_eligible_evidence_holders(counts, requirement_count)
    if index is None:
        return None
    return candidate_cycles[index]


def compute_t_evidence(
    schedule: EvidenceArrivalSchedule,
    target_capable_reproducer_order: Sequence[NBaiotDomain],
    candidate_cycles: Sequence[NonNegativeInt],
    reproduction_row_requirement: PositiveInt,
    final_gate_domain_requirement: PositiveInt,
) -> NonNegativeInt | None:
    t_reproduction_evidence = cycle_when_requirement_met(
        schedule, target_capable_reproducer_order, candidate_cycles, reproduction_row_requirement
    )
    t_final_gate = cycle_when_requirement_met(
        schedule, target_capable_reproducer_order, candidate_cycles, final_gate_domain_requirement
    )
    if t_reproduction_evidence is None or t_final_gate is None:
        return None
    return max(t_reproduction_evidence, t_final_gate)
