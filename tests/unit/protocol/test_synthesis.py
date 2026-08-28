import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.enums import ClaimState
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    krum_input_excludes_source,
    krum_neighbor_count,
    krum_score,
    select_krum_update,
    synthesis_pending_transition,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
FINAL_GATE_CONFIG = CONFIG.protocol.final_gate
SYNTHESIS_CONFIG = CONFIG.protocol.synthesis


def test_synthesis_pending_dormant_when_too_few_adequate_final_gate_domains() -> None:
    state = synthesis_pending_transition(
        FINAL_GATE_CONFIG.minimum_adequate_non_source_domains - 1, True, FINAL_GATE_CONFIG
    )
    assert state is ClaimState.DORMANT


def test_synthesis_pending_admitted_when_predicates_pass() -> None:
    state = synthesis_pending_transition(
        FINAL_GATE_CONFIG.minimum_adequate_non_source_domains, True, FINAL_GATE_CONFIG
    )
    assert state is ClaimState.ADMITTED


def test_synthesis_pending_rejected_when_predicates_fail() -> None:
    state = synthesis_pending_transition(
        FINAL_GATE_CONFIG.minimum_adequate_non_source_domains, False, FINAL_GATE_CONFIG
    )
    assert state is ClaimState.REJECTED_CLAIM


def test_krum_input_excludes_source() -> None:
    assert krum_input_excludes_source(["row-a", "row-b"], None)
    assert krum_input_excludes_source(["row-a", "row-b"], "row-c")
    assert not krum_input_excludes_source(["row-a", "row-b"], "row-a")


def _row(index: int, value: float) -> CertifiedReproductionRow:
    return CertifiedReproductionRow(
        reproducer_domain=NBAIOT_DOMAIN_ORDER[index],
        update_vector=torch.tensor([value], dtype=torch.float64),
    )


def test_krum_neighbor_count_for_n5_f1_is_2() -> None:
    assert krum_neighbor_count(SYNTHESIS_CONFIG.committee_size, 1) == 2


def test_krum_score_matches_hand_computation() -> None:
    committee = [_row(0, 0.0), _row(1, 0.1), _row(2, 0.2), _row(3, 10.0), _row(4, -10.0)]
    score_a = krum_score(committee[0], committee, neighbor_count=2)
    assert abs(score_a - 0.05) < 1e-9


def test_select_krum_update_picks_minimum_score() -> None:
    committee = [_row(0, 0.0), _row(1, 0.1), _row(2, 0.2), _row(3, 10.0), _row(4, -10.0)]
    selected = select_krum_update(committee, maximum_byzantine_rows=1)
    assert selected.reproducer_domain == NBAIOT_DOMAIN_ORDER[1]
    assert abs(float(selected.update_vector.item()) - 0.1) < 1e-9


def test_select_krum_update_breaks_ties_by_ascending_domain_hash_token() -> None:
    committee = [_row(0, 0.0), _row(1, 0.0), _row(2, 5.0), _row(3, 10.0), _row(4, 15.0)]
    selected = select_krum_update(committee, maximum_byzantine_rows=1)
    assert selected.reproducer_domain == NBAIOT_DOMAIN_ORDER[0]


def test_select_krum_update_rejects_inadmissible_committee_size() -> None:
    committee = [_row(0, 0.0), _row(1, 0.0), _row(2, 5.0)]
    try:
        select_krum_update(committee, maximum_byzantine_rows=1)
    except ValueError:
        return
    raise AssertionError("expected ValueError for an inadmissible Krum committee size")
