from fedsira.config.schema import ResourceHorizonConfig
from fedsira.domain.enums import ClaimState, DormantOrigin, TernaryOutcome
from fedsira.domain.records import NonNegativeInt

TERMINAL_CLAIM_STATES = frozenset(
    {ClaimState.ADMITTED, ClaimState.REJECTED_CLAIM, ClaimState.EXPIRED}
)


def is_terminal_state(state: ClaimState) -> bool:
    return state in TERMINAL_CLAIM_STATES


def apply_logical_cycle_expiry(
    state: ClaimState,
    logical_cycle: NonNegativeInt,
    resource_horizon_config: ResourceHorizonConfig,
) -> ClaimState:
    if is_terminal_state(state):
        return state
    if logical_cycle >= resource_horizon_config.maximum_logical_evidence_cycles:
        return ClaimState.EXPIRED
    return state


_DORMANT_RESUME_STATE: dict[DormantOrigin, ClaimState] = {
    DormantOrigin.CANDIDATE_SCREEN: ClaimState.CANDIDATE_SCREEN,
    DormantOrigin.REPRODUCTION_PENDING: ClaimState.REPRODUCTION_PENDING,
    DormantOrigin.SYNTHESIS_PENDING: ClaimState.SYNTHESIS_PENDING,
}


def resume_dormant_claim(
    dormant_origin: DormantOrigin, newly_adequate_evidence_exists: bool
) -> ClaimState:
    if not newly_adequate_evidence_exists:
        return ClaimState.DORMANT
    return _DORMANT_RESUME_STATE[dormant_origin]


def resolve_ternary_outcome(
    is_evidence_adequate: bool, underlying_vote_is_positive: bool
) -> TernaryOutcome:
    if not is_evidence_adequate:
        return TernaryOutcome.ABSTAIN
    if underlying_vote_is_positive:
        return TernaryOutcome.POSITIVE
    return TernaryOutcome.NEGATIVE
