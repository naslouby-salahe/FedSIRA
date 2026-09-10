from fedsira.domain.enums import ByzantineVerifierBehavior, TernaryOutcome
from fedsira.protocol.attacks.byzantine import resolve_byzantine_verifier_vote


def test_false_positive_behavior_always_votes_positive() -> None:
    assert (
        resolve_byzantine_verifier_vote(ByzantineVerifierBehavior.FALSE_POSITIVE)
        is TernaryOutcome.POSITIVE
    )


def test_false_negative_behavior_always_votes_negative() -> None:
    assert (
        resolve_byzantine_verifier_vote(ByzantineVerifierBehavior.FALSE_NEGATIVE)
        is TernaryOutcome.NEGATIVE
    )
