from fedsira.domain.enums import ByzantineVerifierBehavior, TernaryOutcome


def resolve_byzantine_verifier_vote(behavior: ByzantineVerifierBehavior) -> TernaryOutcome:
    if behavior is ByzantineVerifierBehavior.FALSE_POSITIVE:
        return TernaryOutcome.POSITIVE
    return TernaryOutcome.NEGATIVE
