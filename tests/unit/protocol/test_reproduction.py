import pytest

from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, NBaiotDomain
from fedsira.domain.enums import ClaimState
from fedsira.protocol.reproduction import (
    ReproductionAttempt,
    consumed_domains,
    handle_adequate_domain_trained,
    handle_inadequate_domain,
    handle_no_adequate_unconsumed_domain,
    next_reproducer_domain,
    validate_reproduction_start_checkpoint,
)

DOMAIN_A, DOMAIN_B, DOMAIN_C = NBAIOT_DOMAIN_ORDER[:3]


def test_consumed_domains_only_counts_trained_attempts() -> None:
    attempts = [
        ReproductionAttempt(DOMAIN_A, was_trained=True, is_certified=True),
        ReproductionAttempt(DOMAIN_B, was_trained=False, is_certified=False),
    ]
    assert consumed_domains(attempts) == frozenset({DOMAIN_A})


def test_consumed_domain_retained_even_if_certification_later_fails() -> None:
    attempts = [ReproductionAttempt(DOMAIN_A, was_trained=True, is_certified=False)]
    assert DOMAIN_A in consumed_domains(attempts)


def test_next_reproducer_domain_skips_consumed_and_inadequate_domains() -> None:
    order = (DOMAIN_A, DOMAIN_B, DOMAIN_C)
    consumed = frozenset({DOMAIN_A})
    adequate = frozenset({DOMAIN_B, DOMAIN_C})
    assert next_reproducer_domain(order, consumed, adequate) == DOMAIN_B


def test_next_reproducer_domain_never_reorders_by_adequacy() -> None:
    order = (DOMAIN_A, DOMAIN_B, DOMAIN_C)
    consumed: frozenset[NBaiotDomain] = frozenset()
    adequate = frozenset({DOMAIN_C})
    assert next_reproducer_domain(order, consumed, adequate) == DOMAIN_C


def test_next_reproducer_domain_returns_none_when_exhausted() -> None:
    order = (DOMAIN_A,)
    assert next_reproducer_domain(order, frozenset({DOMAIN_A}), frozenset({DOMAIN_A})) is None


def test_handle_inadequate_domain_does_not_consume() -> None:
    assert handle_inadequate_domain() is ClaimState.REPRODUCTION_PENDING


def test_handle_adequate_domain_trained_goes_to_verification_when_active() -> None:
    state = handle_adequate_domain_trained(
        external_verification_active=True, resolved_row_requirement_reached=False
    )
    assert state is ClaimState.VERIFICATION_PENDING


def test_handle_adequate_domain_trained_goes_to_synthesis_without_verification() -> None:
    state = handle_adequate_domain_trained(
        external_verification_active=False, resolved_row_requirement_reached=True
    )
    assert state is ClaimState.SYNTHESIS_PENDING


def test_handle_adequate_domain_trained_continues_scanning() -> None:
    state = handle_adequate_domain_trained(
        external_verification_active=False, resolved_row_requirement_reached=False
    )
    assert state is ClaimState.REPRODUCTION_PENDING


def test_handle_no_adequate_unconsumed_domain_dormant_when_row_requirement_unmet() -> None:
    assert handle_no_adequate_unconsumed_domain(False) is ClaimState.DORMANT


def test_handle_no_adequate_unconsumed_domain_synthesizes_when_row_requirement_met() -> None:
    assert handle_no_adequate_unconsumed_domain(True) is ClaimState.SYNTHESIS_PENDING


def test_validate_reproduction_start_checkpoint_rejects_source_derived_checkpoint() -> None:
    with pytest.raises(ValueError, match="source"):
        validate_reproduction_start_checkpoint(
            "source-checkpoint", frozenset({"source-checkpoint"})
        )
    validate_reproduction_start_checkpoint("anchor-checkpoint", frozenset({"source-checkpoint"}))
