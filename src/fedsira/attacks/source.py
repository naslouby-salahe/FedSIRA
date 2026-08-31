import math
from collections import OrderedDict
from collections.abc import Mapping, Sequence

import torch

from fedsira.datasets.nbaiot.schema import NBaiotClass
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.types import (
    ArtifactDigest,
    AttackCount,
    ExampleCount,
    FeatureIndex,
    NamespaceSeed,
    Probability,
    TriggerFeatureValue,
)
from fedsira.runtime.determinism import deterministic_order

ATTACK_GENERATION_SEPARATOR = SeedNamespace.ATTACK_GENERATION.value


def fraction_to_attack_count(
    fraction: Probability, eligible_population_size: ExampleCount
) -> AttackCount:
    return math.floor(fraction * eligible_population_size)


def attack_row_order(
    eligible_row_ids: Sequence[ArtifactDigest], attack_generation_namespace_seed: NamespaceSeed
) -> tuple[ArtifactDigest, ...]:
    return deterministic_order(
        tuple(eligible_row_ids), ATTACK_GENERATION_SEPARATOR, attack_generation_namespace_seed
    )


def select_fractional_attack_rows(
    eligible_row_ids: Sequence[ArtifactDigest],
    fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    count = fraction_to_attack_count(fraction, len(eligible_row_ids))
    if fraction > 0.0 and count == 0:
        return None
    return attack_row_order(eligible_row_ids, attack_generation_namespace_seed)[:count]


def apply_trigger_transform(
    standardized_features: torch.Tensor,
    trigger_feature_indices: Sequence[FeatureIndex],
    trigger_value: TriggerFeatureValue,
) -> torch.Tensor:
    triggered = standardized_features.clone()
    for feature_index in trigger_feature_indices:
        triggered[..., feature_index] = trigger_value
    return triggered


def select_source_backdoor_poison_rows(
    eligible_gafgyt_udp_row_ids: Sequence[ArtifactDigest],
    poison_fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    return select_fractional_attack_rows(
        eligible_gafgyt_udp_row_ids, poison_fraction, attack_generation_namespace_seed
    )


def relabel_triggered_rows_as_benign(
    labels_by_row_id: Mapping[ArtifactDigest, NBaiotClass],
    poisoned_row_ids: Sequence[ArtifactDigest],
) -> Mapping[ArtifactDigest, NBaiotClass]:
    relabeled: OrderedDict[ArtifactDigest, NBaiotClass] = OrderedDict(labels_by_row_id)
    for row_id in poisoned_row_ids:
        relabeled[row_id] = NBaiotClass.BENIGN
    return relabeled
