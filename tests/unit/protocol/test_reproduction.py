import pytest
import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, NBaiotDomain
from fedsira.domain.enums import ClaimState
from fedsira.protocol.reproduction import (
    ReproductionAttempt,
    compute_reproduction_commitment_hash,
    consumed_domains,
    handle_adequate_domain_trained,
    handle_inadequate_domain,
    handle_no_adequate_unconsumed_domain,
    next_reproducer_domain,
    select_compromised_reproducers,
    validate_commitment_exists_before_verifier_assignment,
    validate_reproduction_start_checkpoint,
    validate_reproduction_starts_from_anchor,
)

DOMAIN_A, DOMAIN_B, DOMAIN_C = NBAIOT_DOMAIN_ORDER[:3]
CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
POST_REFERENCE_CONFIG = CONFIG.model.post_reference


def test_reproduction_stability_weight_is_1_0() -> None:
    assert POST_REFERENCE_CONFIG.stability_weight == 1.0


def test_reproduction_delta_l2_weight_is_1e_5() -> None:
    assert POST_REFERENCE_CONFIG.delta_l2_weight == 1e-5


def test_consumed_domains_only_counts_trained_attempts() -> None:
    attempts = [
        ReproductionAttempt(
            domain=DOMAIN_A,
            was_trained=True,
            is_certified=True,
        ),
        ReproductionAttempt(
            domain=DOMAIN_B,
            was_trained=False,
            is_certified=False,
        ),
    ]
    assert consumed_domains(attempts) == frozenset({DOMAIN_A})


def test_consumed_domain_retained_even_if_certification_later_fails() -> None:
    attempts = [
        ReproductionAttempt(
            domain=DOMAIN_A,
            was_trained=True,
            is_certified=False,
        )
    ]
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


def test_validate_reproduction_starts_from_anchor() -> None:
    anchor = torch.tensor([1.0, 2.0, 3.0])
    validate_reproduction_starts_from_anchor(anchor.clone(), anchor)
    with pytest.raises(ValueError, match="anchor"):
        validate_reproduction_starts_from_anchor(torch.tensor([0.0, 2.0, 3.0]), anchor)


def test_compute_reproduction_commitment_hash_is_deterministic() -> None:
    parameters = torch.tensor([1.0, 2.0, 3.0])
    first = compute_reproduction_commitment_hash(DOMAIN_A, "c" * 64, 42, parameters)
    second = compute_reproduction_commitment_hash(DOMAIN_A, "c" * 64, 42, parameters)
    assert first == second
    assert len(first) == 64


def test_compute_reproduction_commitment_hash_changes_with_parameters() -> None:
    baseline = compute_reproduction_commitment_hash(
        DOMAIN_A, "c" * 64, 42, torch.tensor([1.0, 2.0, 3.0])
    )
    changed = compute_reproduction_commitment_hash(
        DOMAIN_A, "c" * 64, 42, torch.tensor([1.0, 2.0, 3.1])
    )
    assert baseline != changed


def test_compute_reproduction_commitment_hash_changes_with_domain() -> None:
    parameters = torch.tensor([1.0, 2.0, 3.0])
    baseline = compute_reproduction_commitment_hash(DOMAIN_A, "c" * 64, 42, parameters)
    changed = compute_reproduction_commitment_hash(DOMAIN_B, "c" * 64, 42, parameters)
    assert baseline != changed


def test_validate_commitment_exists_before_verifier_assignment() -> None:
    validate_commitment_exists_before_verifier_assignment("d" * 64)
    with pytest.raises(ValueError, match="commitment"):
        validate_commitment_exists_before_verifier_assignment(None)


def test_select_compromised_reproducers_takes_first_feasible_in_order() -> None:
    order = (DOMAIN_A, DOMAIN_B, DOMAIN_C)
    feasible = frozenset({DOMAIN_B, DOMAIN_C})
    assert select_compromised_reproducers(order, feasible, 1) == (DOMAIN_B,)
    assert select_compromised_reproducers(order, feasible, 2) == (DOMAIN_B, DOMAIN_C)


def test_select_compromised_reproducers_returns_none_when_infeasible() -> None:
    order = (DOMAIN_A, DOMAIN_B, DOMAIN_C)
    assert select_compromised_reproducers(order, frozenset({DOMAIN_A}), 2) is None
