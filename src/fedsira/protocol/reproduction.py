from collections.abc import Sequence
from dataclasses import dataclass

from fedsira.datasets.nbaiot.schema import NBaiotDomain
from fedsira.domain.enums import ClaimState
from fedsira.domain.records import CanonicalToken


@dataclass(frozen=True)
class ReproductionAttempt:
    domain: NBaiotDomain
    was_trained: bool
    is_certified: bool


def consumed_domains(attempts: Sequence[ReproductionAttempt]) -> frozenset[NBaiotDomain]:
    return frozenset(attempt.domain for attempt in attempts if attempt.was_trained)


def next_reproducer_domain(
    reproducer_order: Sequence[NBaiotDomain],
    consumed: frozenset[NBaiotDomain],
    adequate_domains: frozenset[NBaiotDomain],
) -> NBaiotDomain | None:
    for domain in reproducer_order:
        if domain not in consumed and domain in adequate_domains:
            return domain
    return None


def handle_inadequate_domain() -> ClaimState:
    return ClaimState.REPRODUCTION_PENDING


def handle_adequate_domain_trained(
    external_verification_active: bool, resolved_row_requirement_reached: bool
) -> ClaimState:
    if external_verification_active:
        return ClaimState.VERIFICATION_PENDING
    if resolved_row_requirement_reached:
        return ClaimState.SYNTHESIS_PENDING
    return ClaimState.REPRODUCTION_PENDING


def handle_no_adequate_unconsumed_domain(resolved_row_requirement_reached: bool) -> ClaimState:
    if resolved_row_requirement_reached:
        return ClaimState.SYNTHESIS_PENDING
    return ClaimState.DORMANT


def validate_reproduction_start_checkpoint(
    start_checkpoint_id: CanonicalToken, source_checkpoint_ids: frozenset[CanonicalToken]
) -> None:
    if start_checkpoint_id in source_checkpoint_ids:
        raise ValueError(
            "honest reproduction must not start from the source or a source-derived checkpoint"
        )
