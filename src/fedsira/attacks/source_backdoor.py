from collections.abc import Mapping, Sequence

import torch

from fedsira.attacks.transform import select_transform_rows
from fedsira.datasets.nbaiot.schema import NBaiotClass
from fedsira.domain.records import CanonicalToken, NamespaceSeed, Probability


def apply_trigger_transform(
    standardized_features: torch.Tensor,
    trigger_feature_indices: Sequence[int],
    trigger_value: float,
) -> torch.Tensor:
    triggered = standardized_features.clone()
    for feature_index in trigger_feature_indices:
        triggered[..., feature_index] = trigger_value
    return triggered


def select_source_backdoor_poison_rows(
    eligible_gafgyt_udp_row_ids: Sequence[CanonicalToken],
    poison_fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[CanonicalToken, ...] | None:
    return select_transform_rows(
        eligible_gafgyt_udp_row_ids, poison_fraction, attack_generation_namespace_seed
    )


def relabel_triggered_rows_as_benign(
    labels_by_row_id: Mapping[CanonicalToken, NBaiotClass],
    poisoned_row_ids: Sequence[CanonicalToken],
) -> dict[CanonicalToken, NBaiotClass]:
    relabeled = dict(labels_by_row_id)
    for row_id in poisoned_row_ids:
        relabeled[row_id] = NBaiotClass.BENIGN
    return relabeled
