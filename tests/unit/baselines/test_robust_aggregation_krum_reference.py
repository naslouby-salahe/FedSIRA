from fedsira.baselines.robust_aggregation import (
    client_sampling_round_order,
    client_sampling_round_seed,
    krum_reference_post_reference_rounds,
    krum_reference_round_participants,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
BASELINES_CONFIG = CONFIG.baselines
SYNTHESIS_CONFIG = CONFIG.protocol.synthesis


def test_krum_reference_post_reference_rounds_uses_governed_config() -> None:
    assert (
        krum_reference_post_reference_rounds(BASELINES_CONFIG)
        == BASELINES_CONFIG.krum_robust_aggregation_post_reference_rounds
    )


def test_client_sampling_round_order_is_deterministic_and_recomputed_per_round() -> None:
    first = client_sampling_round_order(NBAIOT_DOMAIN_ORDER, 42, 0)
    second = client_sampling_round_order(NBAIOT_DOMAIN_ORDER, 42, 0)
    third_round = client_sampling_round_order(NBAIOT_DOMAIN_ORDER, 42, 1)
    assert first == second
    assert set(first) == set(NBAIOT_DOMAIN_ORDER)
    assert client_sampling_round_seed(42, 0) != client_sampling_round_seed(42, 1)
    assert first != third_round


def test_krum_reference_round_participants_clean_condition_takes_first_five() -> None:
    order = client_sampling_round_order(NBAIOT_DOMAIN_ORDER, 42, 0)
    participants = krum_reference_round_participants(order, None, SYNTHESIS_CONFIG.committee_size)
    assert participants == order[: SYNTHESIS_CONFIG.committee_size]


def test_krum_reference_round_participants_forces_compromised_domain_inclusion() -> None:
    order = client_sampling_round_order(NBAIOT_DOMAIN_ORDER, 42, 0)
    compromised = order[-1]
    participants = krum_reference_round_participants(
        order, compromised, SYNTHESIS_CONFIG.committee_size
    )
    assert participants is not None
    assert compromised in participants
    assert len(participants) == SYNTHESIS_CONFIG.committee_size


def test_krum_reference_round_participants_none_when_insufficient_eligible_domains() -> None:
    assert krum_reference_round_participants(NBAIOT_DOMAIN_ORDER[:3], None, 5) is None
