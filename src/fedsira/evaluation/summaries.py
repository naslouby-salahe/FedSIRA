from __future__ import annotations

from fedsira.domain.enums import ClaimId, ClaimState
from fedsira.domain.types import FrozenDomainModel, TextValue

CLAIM_DECISION_SCHEMA_VERSION: TextValue = "fedsira|claim-decisions|1"
CLAIM_INVENTORY: tuple[ClaimId, ...] = tuple(ClaimId)


class ClaimDecision(FrozenDomainModel):
    claim_id: ClaimId
    state: ClaimState
    basis: TextValue


class ClaimSummary(FrozenDomainModel):
    schema_version: TextValue = CLAIM_DECISION_SCHEMA_VERSION
    decisions: tuple[ClaimDecision, ...]


def unevaluated_claim_summary() -> ClaimSummary:
    return ClaimSummary(
        decisions=tuple(
            ClaimDecision(
                claim_id=claim_id,
                state=ClaimState.NOT_TESTED,
                basis="Claim-bearing evidence and decision artifacts are not available.",
            )
            for claim_id in CLAIM_INVENTORY
        )
    )
