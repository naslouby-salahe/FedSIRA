from fedsira.attacks.verification import resolve_byzantine_verifier_vote
from fedsira.domain.enums import ByzantineVerifierBehavior, TernaryOutcome


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
