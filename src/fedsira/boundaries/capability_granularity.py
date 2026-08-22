import hashlib

import torch

from fedsira.domain.enums import CapabilityContractScope, RootCause
from fedsira.domain.records import CanonicalToken, NonNegativeInt
from fedsira.runtime.determinism import canonical_bytes

ROOT_CAUSE_SEPARATOR = "CAPABILITY_ROOT_CAUSE"


def root_cause_for_sample(sample_id: CanonicalToken) -> RootCause:
    digest = hashlib.sha256(canonical_bytes(ROOT_CAUSE_SEPARATOR, sample_id)).digest()
    parity: NonNegativeInt = int.from_bytes(digest[0:8], byteorder="big", signed=False) % 2
    return RootCause.A if parity == 0 else RootCause.B


def apply_root_cause_feature_shift(
    standardized_features: torch.Tensor,
    root_cause: RootCause,
    root_cause_a_feature_index: int,
    root_cause_b_feature_index: int,
    shift_value: float,
) -> torch.Tensor:
    shifted = standardized_features.clone()
    feature_index = (
        root_cause_a_feature_index if root_cause is RootCause.A else root_cause_b_feature_index
    )
    shifted[..., feature_index] = shifted[..., feature_index] + shift_value
    return shifted


def target_row_ids_for_contract(
    scope: CapabilityContractScope,
    root_cause_a_row_ids: frozenset[CanonicalToken],
    root_cause_b_row_ids: frozenset[CanonicalToken],
) -> frozenset[CanonicalToken]:
    if scope is CapabilityContractScope.BROAD_TARGET_ONLY:
        return root_cause_a_row_ids | root_cause_b_row_ids
    if scope is CapabilityContractScope.ROOT_CAUSE_A_SCOPED:
        return root_cause_a_row_ids
    return root_cause_b_row_ids


def validate_excluded_root_cause_not_supported(
    scope: CapabilityContractScope,
    supported_row_ids: frozenset[CanonicalToken],
    root_cause_a_row_ids: frozenset[CanonicalToken],
    root_cause_b_row_ids: frozenset[CanonicalToken],
) -> None:
    if scope is CapabilityContractScope.ROOT_CAUSE_A_SCOPED and not supported_row_ids.isdisjoint(
        root_cause_b_row_ids
    ):
        raise ValueError("the excluded root cause must never become a supported-control class")
    if scope is CapabilityContractScope.ROOT_CAUSE_B_SCOPED and not supported_row_ids.isdisjoint(
        root_cause_a_row_ids
    ):
        raise ValueError("the excluded root cause must never become a supported-control class")
