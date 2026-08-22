import pytest
import torch

from fedsira.boundaries.capability_granularity import (
    apply_root_cause_feature_shift,
    root_cause_for_sample,
    target_row_ids_for_contract,
    validate_excluded_root_cause_not_supported,
)
from fedsira.domain.enums import CapabilityContractScope, RootCause


def test_root_cause_for_sample_is_deterministic() -> None:
    first = root_cause_for_sample("sample-1")
    second = root_cause_for_sample("sample-1")
    assert first == second
    assert first in (RootCause.A, RootCause.B)


def test_root_cause_for_sample_produces_both_values_across_many_samples() -> None:
    outcomes = {root_cause_for_sample(f"sample-{i}") for i in range(200)}
    assert outcomes == {RootCause.A, RootCause.B}


def test_apply_root_cause_feature_shift_uses_the_correct_feature_per_root_cause() -> None:
    features = torch.zeros(1, 4)
    shifted_a = apply_root_cause_feature_shift(features, RootCause.A, 0, 3, 3.0)
    assert torch.equal(shifted_a, torch.tensor([[3.0, 0.0, 0.0, 0.0]]))
    shifted_b = apply_root_cause_feature_shift(features, RootCause.B, 0, 3, 3.0)
    assert torch.equal(shifted_b, torch.tensor([[0.0, 0.0, 0.0, 3.0]]))
    assert torch.equal(features, torch.zeros(1, 4))


def test_target_row_ids_for_contract_broad_includes_both_root_causes() -> None:
    a_rows = frozenset({"a1", "a2"})
    b_rows = frozenset({"b1"})
    result = target_row_ids_for_contract(CapabilityContractScope.BROAD_TARGET_ONLY, a_rows, b_rows)
    assert result == a_rows | b_rows


def test_target_row_ids_for_contract_scoped_excludes_the_other_root_cause() -> None:
    a_rows = frozenset({"a1", "a2"})
    b_rows = frozenset({"b1"})
    assert (
        target_row_ids_for_contract(CapabilityContractScope.ROOT_CAUSE_A_SCOPED, a_rows, b_rows)
        == a_rows
    )
    assert (
        target_row_ids_for_contract(CapabilityContractScope.ROOT_CAUSE_B_SCOPED, a_rows, b_rows)
        == b_rows
    )


def test_validate_excluded_root_cause_not_supported_rejects_leakage() -> None:
    a_rows = frozenset({"a1"})
    b_rows = frozenset({"b1"})
    validate_excluded_root_cause_not_supported(
        CapabilityContractScope.ROOT_CAUSE_A_SCOPED, frozenset({"other"}), a_rows, b_rows
    )
    with pytest.raises(ValueError, match="excluded root cause"):
        validate_excluded_root_cause_not_supported(
            CapabilityContractScope.ROOT_CAUSE_A_SCOPED, frozenset({"b1"}), a_rows, b_rows
        )
