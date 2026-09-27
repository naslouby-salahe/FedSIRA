from fedsira.domain.enums import ClaimId, ClaimState
from fedsira.evaluation.summaries import CLAIM_INVENTORY, unevaluated_claim_summary


def test_unevaluated_claim_summary_emits_exact_canonical_inventory() -> None:
    summary = unevaluated_claim_summary()

    assert tuple(decision.claim_id for decision in summary.decisions) == tuple(ClaimId)
    assert len(CLAIM_INVENTORY) == 19
    assert all(decision.state is ClaimState.NOT_TESTED for decision in summary.decisions)
    assert all(
        decision.basis == "Claim-bearing evidence and decision artifacts are not available."
        for decision in summary.decisions
    )
