from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ClaimState
from fedsira.protocol.synthesis import krum_input_excludes_source, synthesis_pending_transition

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
FINAL_GATE_CONFIG = CONFIG.protocol.final_gate


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
