import hashlib
from collections.abc import Sequence

import torch

from fedsira.domain.enums import CapabilityContractScope, RootCause, SeedNamespace
from fedsira.domain.records import (
    FeatureIndex,
    NamespaceSeed,
    SampleId,
    SeedDerivationLabel,
    StandardizedValue,
)
from fedsira.runtime.determinism import deterministic_order, framed_bytes

ROOT_CAUSE_SEPARATOR: SeedDerivationLabel = "CAPABILITY_ROOT_CAUSE"


def root_cause_for_sample(sample_id: SampleId) -> RootCause:
    digest = hashlib.sha256(framed_bytes(ROOT_CAUSE_SEPARATOR, sample_id)).digest()
    parity = int.from_bytes(digest[0:8], byteorder="big", signed=False) % 2
    return RootCause.A if parity == 0 else RootCause.B


def apply_root_cause_feature_shift(
    standardized_features: torch.Tensor,
    root_cause: RootCause,
    root_cause_a_feature_index: FeatureIndex,
    root_cause_b_feature_index: FeatureIndex,
    shift_value: StandardizedValue,
) -> torch.Tensor:
    shifted = standardized_features.clone()
    feature_index = (
        root_cause_a_feature_index if root_cause is RootCause.A else root_cause_b_feature_index
    )
    shifted[..., feature_index] = shifted[..., feature_index] + shift_value
    return shifted


def target_row_ids_for_contract(
    scope: CapabilityContractScope,
    root_cause_a_row_ids: frozenset[SampleId],
    root_cause_b_row_ids: frozenset[SampleId],
) -> frozenset[SampleId]:
    if scope is CapabilityContractScope.BROAD_TARGET_ONLY:
        return root_cause_a_row_ids | root_cause_b_row_ids
    if scope is CapabilityContractScope.ROOT_CAUSE_A_SCOPED:
        return root_cause_a_row_ids
    return root_cause_b_row_ids


def validate_excluded_root_cause_not_supported(
    scope: CapabilityContractScope,
    supported_row_ids: frozenset[SampleId],
    root_cause_a_row_ids: frozenset[SampleId],
    root_cause_b_row_ids: frozenset[SampleId],
) -> None:
    if scope is CapabilityContractScope.ROOT_CAUSE_A_SCOPED and not supported_row_ids.isdisjoint(
        root_cause_b_row_ids
    ):
        raise ValueError("the excluded root cause must never become a supported-control class")
    if scope is CapabilityContractScope.ROOT_CAUSE_B_SCOPED and not supported_row_ids.isdisjoint(
        root_cause_a_row_ids
    ):
        raise ValueError("the excluded root cause must never become a supported-control class")


def balanced_capability_selection(
    root_cause_a_row_ids: Sequence[SampleId],
    root_cause_b_row_ids: Sequence[SampleId],
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[tuple[SampleId, ...], tuple[SampleId, ...]]:
    selected_count = min(len(root_cause_a_row_ids), len(root_cause_b_row_ids))
    separator = SeedNamespace.ATTACK_GENERATION.value
    ordered_a = deterministic_order(
        tuple(root_cause_a_row_ids), separator, attack_generation_namespace_seed
    )
    ordered_b = deterministic_order(
        tuple(root_cause_b_row_ids), separator, attack_generation_namespace_seed
    )
    return ordered_a[:selected_count], ordered_b[:selected_count]
