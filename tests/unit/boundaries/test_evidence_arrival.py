from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, NBaiotDomain
from fedsira.experiments.scenarios.evidence_arrival import (
    EvidenceArrivalSchedule,
    compute_t_evidence,
    cycle_when_requirement_met,
    first_holder_cycle_for_domain,
    holder_count_at_cycle,
    holders_at_cycle,
    reproducer_order,
)

CYCLES = tuple(range(0, 13))
EIGHT_DOMAINS = NBAIOT_DOMAIN_ORDER[:8]


def test_reproducer_order_is_deterministic_and_a_permutation() -> None:
    first = reproducer_order(EIGHT_DOMAINS, 42)
    second = reproducer_order(EIGHT_DOMAINS, 42)
    assert first == second
    assert set(first) == set(EIGHT_DOMAINS)


def test_permanent_singleton_always_zero() -> None:
    for cycle in CYCLES:
        assert holder_count_at_cycle(EvidenceArrivalSchedule.PERMANENT_SINGLETON, cycle, 8) == 0


def test_one_honest_holder_schedule() -> None:
    schedule = EvidenceArrivalSchedule.ONE_HONEST_HOLDER
    assert holder_count_at_cycle(schedule, 0, 8) == 0
    assert holder_count_at_cycle(schedule, 1, 8) == 0
    assert holder_count_at_cycle(schedule, 2, 8) == 1
    assert holder_count_at_cycle(schedule, 12, 8) == 1


def test_gradual_to_quorum_schedule_matches_exact_checkpoints() -> None:
    schedule = EvidenceArrivalSchedule.GRADUAL_TO_QUORUM
    assert holder_count_at_cycle(schedule, 0, 8) == 0
    assert holder_count_at_cycle(schedule, 2, 8) == 1
    assert holder_count_at_cycle(schedule, 4, 8) == 3
    assert holder_count_at_cycle(schedule, 6, 8) == 5
    assert holder_count_at_cycle(schedule, 8, 8) == 8
    assert holder_count_at_cycle(schedule, 3, 8) == 1
    assert holder_count_at_cycle(schedule, 12, 8) == 8


def test_immediate_quorum_exposes_all_at_cycle_zero() -> None:
    schedule = EvidenceArrivalSchedule.IMMEDIATE_QUORUM
    assert holder_count_at_cycle(schedule, 0, 8) == 8
    assert holder_count_at_cycle(schedule, 12, 8) == 8


def test_holders_at_cycle_takes_the_first_k_in_reproducer_order() -> None:
    order = reproducer_order(EIGHT_DOMAINS, 42)
    holders = holders_at_cycle(EvidenceArrivalSchedule.GRADUAL_TO_QUORUM, 4, order)
    assert holders == order[:3]


def test_holder_set_grows_monotonically() -> None:
    order = reproducer_order(EIGHT_DOMAINS, 42)
    previous: set[NBaiotDomain] = set()
    for cycle in CYCLES:
        current = set(holders_at_cycle(EvidenceArrivalSchedule.GRADUAL_TO_QUORUM, cycle, order))
        assert previous.issubset(current)
        previous = current


def test_first_holder_cycle_for_domain() -> None:
    order = reproducer_order(EIGHT_DOMAINS, 42)
    first_domain = order[0]
    cycle = first_holder_cycle_for_domain(
        EvidenceArrivalSchedule.GRADUAL_TO_QUORUM, first_domain, order, CYCLES
    )
    assert cycle == 2


def test_first_holder_cycle_for_domain_none_for_permanent_singleton() -> None:
    order = reproducer_order(EIGHT_DOMAINS, 42)
    cycle = first_holder_cycle_for_domain(
        EvidenceArrivalSchedule.PERMANENT_SINGLETON, order[0], order, CYCLES
    )
    assert cycle is None


def test_gradual_to_quorum_t_reproduction_and_t_evidence_match_roadmap_hand_fixture() -> None:
    order = reproducer_order(EIGHT_DOMAINS, 42)
    schedule = EvidenceArrivalSchedule.GRADUAL_TO_QUORUM
    t_reproduction_evidence = cycle_when_requirement_met(schedule, order, CYCLES, 5)
    assert t_reproduction_evidence == 6
    t_evidence = compute_t_evidence(schedule, order, CYCLES, 5, 6)
    assert t_evidence == 8


def test_immediate_quorum_t_reproduction_and_t_evidence_are_zero() -> None:
    order = reproducer_order(EIGHT_DOMAINS, 42)
    schedule = EvidenceArrivalSchedule.IMMEDIATE_QUORUM
    t_reproduction_evidence = cycle_when_requirement_met(schedule, order, CYCLES, 5)
    assert t_reproduction_evidence == 0
    t_evidence = compute_t_evidence(schedule, order, CYCLES, 5, 6)
    assert t_evidence == 0


def test_permanent_singleton_never_satisfies_requirement_and_reports_none() -> None:
    order = reproducer_order(EIGHT_DOMAINS, 42)
    schedule = EvidenceArrivalSchedule.PERMANENT_SINGLETON
    assert cycle_when_requirement_met(schedule, order, CYCLES, 5) is None
    assert compute_t_evidence(schedule, order, CYCLES, 5, 6) is None
