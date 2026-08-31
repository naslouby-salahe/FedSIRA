from fedsira.config.schema import ResourceHorizonConfig
from fedsira.domain.enums import ClaimState, DormantOrigin, TernaryOutcome
from fedsira.domain.records import (
    BooleanValue,
    EvidenceAdequate,
    EvidenceCycleIndex,
    NewlyAdequateEvidenceExists,
    UnderlyingVoteIsPositive,
)

TERMINAL_CLAIM_STATES = frozenset(
    {ClaimState.ADMITTED, ClaimState.REJECTED_CLAIM, ClaimState.EXPIRED}
)


def is_terminal_state(state: ClaimState) -> BooleanValue:
    return state in TERMINAL_CLAIM_STATES


def apply_logical_cycle_expiry(
    state: ClaimState,
    logical_cycle: EvidenceCycleIndex,
    resource_horizon_config: ResourceHorizonConfig,
) -> ClaimState:
    if is_terminal_state(state):
        return state
    if logical_cycle >= resource_horizon_config.maximum_logical_evidence_cycles:
        return ClaimState.EXPIRED
    return state


_DORMANT_RESUME_STATES: tuple[tuple[DormantOrigin, ClaimState], ...] = (
    (DormantOrigin.CANDIDATE_SCREEN, ClaimState.CANDIDATE_SCREEN),
    (DormantOrigin.REPRODUCTION_PENDING, ClaimState.REPRODUCTION_PENDING),
    (DormantOrigin.SYNTHESIS_PENDING, ClaimState.SYNTHESIS_PENDING),
)


def _dormant_resume_state(dormant_origin: DormantOrigin) -> ClaimState:
    for origin, resume_state in _DORMANT_RESUME_STATES:
        if origin is dormant_origin:
            return resume_state
    raise ValueError(f"unknown dormant origin: {dormant_origin.value}")


def resume_dormant_claim(
    dormant_origin: DormantOrigin, newly_adequate_evidence_exists: NewlyAdequateEvidenceExists
) -> ClaimState:
    if not newly_adequate_evidence_exists:
        return ClaimState.DORMANT
    return _dormant_resume_state(dormant_origin)


def resolve_ternary_outcome(
    is_evidence_adequate: EvidenceAdequate, underlying_vote_is_positive: UnderlyingVoteIsPositive
) -> TernaryOutcome:
    if not is_evidence_adequate:
        return TernaryOutcome.ABSTAIN
    if underlying_vote_is_positive:
        return TernaryOutcome.POSITIVE
    return TernaryOutcome.NEGATIVE
