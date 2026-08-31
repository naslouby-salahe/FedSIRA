from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.protocol.proposal import select_source_domain, source_selection_order

DOMAIN_A, DOMAIN_B, DOMAIN_C = NBAIOT_DOMAIN_ORDER[:3]


def test_source_selection_order_is_deterministic_and_a_permutation() -> None:
    first = source_selection_order(NBAIOT_DOMAIN_ORDER, 42)
    second = source_selection_order(NBAIOT_DOMAIN_ORDER, 42)
    assert first == second
    assert set(first) == set(NBAIOT_DOMAIN_ORDER)


def test_source_selection_order_is_reproducible_for_the_same_seed() -> None:
    assert source_selection_order(NBAIOT_DOMAIN_ORDER, 7) == source_selection_order(
        NBAIOT_DOMAIN_ORDER, 7
    )


def test_select_source_domain_picks_first_with_target_stream() -> None:
    order = (DOMAIN_A, DOMAIN_B, DOMAIN_C)
    selected = select_source_domain(
        order,
        frozenset({DOMAIN_B, DOMAIN_C}),
        requires_attack_carrier=False,
        domains_with_attack_carrier=frozenset(),
    )
    assert selected is DOMAIN_B


def test_select_source_domain_requires_gafgyt_udp_carrier_when_needed() -> None:
    order = (DOMAIN_A, DOMAIN_B, DOMAIN_C)
    selected = select_source_domain(
        order,
        frozenset({DOMAIN_A, DOMAIN_B}),
        requires_attack_carrier=True,
        domains_with_attack_carrier=frozenset({DOMAIN_B}),
    )
    assert selected is DOMAIN_B


def test_select_source_domain_returns_none_when_no_domain_qualifies() -> None:
    order = (DOMAIN_A,)
    assert (
        select_source_domain(
            order,
            frozenset(),
            requires_attack_carrier=False,
            domains_with_attack_carrier=frozenset(),
        )
        is None
    )
