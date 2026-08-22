from collections.abc import Sequence

from fedsira.config.schema import FinalGateConfig
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import CanonicalToken, NonNegativeInt


def synthesis_pending_transition(
    adequate_final_gate_domain_count: NonNegativeInt,
    final_gate_predicates_pass: bool,
    final_gate_config: FinalGateConfig,
) -> ClaimState:
    if adequate_final_gate_domain_count < final_gate_config.minimum_adequate_non_source_domains:
        return ClaimState.DORMANT
    if final_gate_predicates_pass:
        return ClaimState.ADMITTED
    return ClaimState.REJECTED_CLAIM


def krum_input_excludes_source(
    candidate_row_ids: Sequence[CanonicalToken], source_row_id: CanonicalToken | None
) -> bool:
    if source_row_id is None:
        return True
    return source_row_id not in candidate_row_ids
