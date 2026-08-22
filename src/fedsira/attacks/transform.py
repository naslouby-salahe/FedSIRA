import math
from collections.abc import Sequence

from fedsira.domain.records import CanonicalToken, NamespaceSeed, NonNegativeInt, Probability
from fedsira.runtime.determinism import deterministic_order

ATTACK_GENERATION_SEPARATOR = "ATTACK_GENERATION"


def fraction_to_transform_count(
    fraction: Probability, eligible_population_size: NonNegativeInt
) -> NonNegativeInt:
    return math.floor(fraction * eligible_population_size)


def attack_generation_order(
    eligible_row_ids: Sequence[CanonicalToken], attack_generation_namespace_seed: NamespaceSeed
) -> tuple[CanonicalToken, ...]:
    return deterministic_order(
        eligible_row_ids, ATTACK_GENERATION_SEPARATOR, attack_generation_namespace_seed
    )


def select_transform_rows(
    eligible_row_ids: Sequence[CanonicalToken],
    fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[CanonicalToken, ...] | None:
    count = fraction_to_transform_count(fraction, len(eligible_row_ids))
    if fraction > 0.0 and count == 0:
        return None
    ordered = attack_generation_order(eligible_row_ids, attack_generation_namespace_seed)
    return ordered[:count]


def balanced_50_50_selection(
    group_a_row_ids: Sequence[CanonicalToken],
    group_b_row_ids: Sequence[CanonicalToken],
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[tuple[CanonicalToken, ...], tuple[CanonicalToken, ...]]:
    selected_count = min(len(group_a_row_ids), len(group_b_row_ids))
    ordered_a = attack_generation_order(group_a_row_ids, attack_generation_namespace_seed)
    ordered_b = attack_generation_order(group_b_row_ids, attack_generation_namespace_seed)
    return ordered_a[:selected_count], ordered_b[:selected_count]


def a_dominant_80_20_selection(
    group_a_row_ids: Sequence[CanonicalToken],
    group_b_row_ids: Sequence[CanonicalToken],
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[tuple[CanonicalToken, ...], tuple[CanonicalToken, ...]]:
    b_matched_count = min(len(group_a_row_ids) // 4, len(group_b_row_ids))
    ordered_a = attack_generation_order(group_a_row_ids, attack_generation_namespace_seed)
    ordered_b = attack_generation_order(group_b_row_ids, attack_generation_namespace_seed)
    return ordered_a[: 4 * b_matched_count], ordered_b[:b_matched_count]
