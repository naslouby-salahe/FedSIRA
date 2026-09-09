from fedsira.config.models import ResourceHorizonConfig
from fedsira.domain.enums import AdmissionState, DormantOrigin, TernaryOutcome
from fedsira.domain.types import (
    AdmissionStateIsTerminal,
    EvidenceAdequate,
    EvidenceCycleIndex,
    NewlyAdequateEvidenceExists,
    UnderlyingVoteIsPositive,
)

TERMINAL_ADMISSION_STATES = frozenset(
    {AdmissionState.ADMITTED, AdmissionState.REJECTED, AdmissionState.EXPIRED}
)


def is_terminal_state(state: AdmissionState) -> AdmissionStateIsTerminal:
    return state in TERMINAL_ADMISSION_STATES


def apply_logical_cycle_expiry(
    state: AdmissionState,
    logical_cycle: EvidenceCycleIndex,
    resource_horizon_config: ResourceHorizonConfig,
) -> AdmissionState:
    if is_terminal_state(state):
        return state
    if logical_cycle >= resource_horizon_config.maximum_logical_evidence_cycles:
        return AdmissionState.EXPIRED
    return state


_DORMANT_RESUME_STATES: tuple[tuple[DormantOrigin, AdmissionState], ...] = (
    (DormantOrigin.CANDIDATE_SCREEN, AdmissionState.CANDIDATE_SCREEN),
    (DormantOrigin.REPRODUCTION_PENDING, AdmissionState.REPRODUCTION_PENDING),
    (DormantOrigin.SYNTHESIS_PENDING, AdmissionState.SYNTHESIS_PENDING),
)


def _dormant_resume_state(dormant_origin: DormantOrigin) -> AdmissionState:
    for origin, resume_state in _DORMANT_RESUME_STATES:
        if origin is dormant_origin:
            return resume_state
    raise ValueError(f"unknown dormant origin: {dormant_origin.value}")


def resume_dormant_admission(
    dormant_origin: DormantOrigin, newly_adequate_evidence_exists: NewlyAdequateEvidenceExists
) -> AdmissionState:
    if not newly_adequate_evidence_exists:
        return AdmissionState.DORMANT
    return _dormant_resume_state(dormant_origin)


def resolve_ternary_outcome(
    is_evidence_adequate: EvidenceAdequate, underlying_vote_is_positive: UnderlyingVoteIsPositive
) -> TernaryOutcome:
    if not is_evidence_adequate:
        return TernaryOutcome.ABSTAIN
    if underlying_vote_is_positive:
        return TernaryOutcome.POSITIVE
    return TernaryOutcome.NEGATIVE
