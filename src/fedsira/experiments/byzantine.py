from fedsira.domain.enums import ByzantineVerifierBehavior, ReproducerCondition, VerifierCondition
from fedsira.domain.types import (
    ByzantineDomainCount,
    CompromisedReproducerCount,
    ConditionName,
)
from fedsira.runtime import current_application_context

BYZANTINE_BEHAVIOUR_CONDITIONS: tuple[tuple[ByzantineVerifierBehavior, ConditionName], ...] = (
    (ByzantineVerifierBehavior.FALSE_POSITIVE, VerifierCondition.ONE_FALSE_POSITIVE),
    (ByzantineVerifierBehavior.FALSE_POSITIVE, VerifierCondition.TWO_FALSE_POSITIVES),
    (ByzantineVerifierBehavior.FALSE_NEGATIVE, VerifierCondition.ONE_FALSE_NEGATIVE),
    (ByzantineVerifierBehavior.FALSE_NEGATIVE, VerifierCondition.TWO_FALSE_NEGATIVES),
)


def validate_byzantine_vocabulary() -> None:
    byzantine = current_application_context().scientific_config.attacks_and_boundaries
    declared_reproducer_counts = tuple(sorted(byzantine.byzantine_reproduction.compromised_counts))
    observed_reproducer_counts = tuple(
        sorted({compromised_reproducer_count(condition) for condition in ReproducerCondition})
    )
    if observed_reproducer_counts != declared_reproducer_counts:
        raise ValueError(
            "declared compromised-reproducer counts "
            f"{declared_reproducer_counts} do not match the reproducer conditions "
            f"{observed_reproducer_counts}"
        )
    declared_verifier_counts = tuple(sorted(byzantine.byzantine_verifier.compromise_counts))
    observed_verifier_counts = tuple(
        sorted({compromised_verifier_count(condition) for condition in VerifierCondition})
    )
    if observed_verifier_counts != declared_verifier_counts:
        raise ValueError(
            "declared compromised-verifier counts "
            f"{declared_verifier_counts} do not match the verifier conditions "
            f"{observed_verifier_counts}"
        )
    declared_behaviours = tuple(sorted(byzantine.byzantine_verifier.behaviors))
    observed_behaviours = tuple(
        sorted({behaviour for behaviour, _condition in BYZANTINE_BEHAVIOUR_CONDITIONS})
    )
    if observed_behaviours != declared_behaviours:
        raise ValueError(
            "declared byzantine verifier behaviours "
            f"{declared_behaviours} do not match the verifier conditions "
            f"{observed_behaviours}"
        )


def compromised_reproducer_count(condition: ConditionName) -> CompromisedReproducerCount:
    if condition in (
        ReproducerCondition.ONE_SOURCE_COPY,
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
        ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
    ):
        return 1
    if condition in (
        ReproducerCondition.TWO_SOURCE_COPIES,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
        ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
    ):
        return 2
    return 0


def compromised_verifier_count(condition: ConditionName) -> ByzantineDomainCount:
    if condition in (
        VerifierCondition.ONE_FALSE_POSITIVE,
        VerifierCondition.ONE_FALSE_NEGATIVE,
    ):
        return 1
    if condition in (
        VerifierCondition.TWO_FALSE_POSITIVES,
        VerifierCondition.TWO_FALSE_NEGATIVES,
    ):
        return 2
    return 0
