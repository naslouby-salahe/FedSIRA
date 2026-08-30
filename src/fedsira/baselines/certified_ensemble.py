from collections import OrderedDict
from collections.abc import Sequence

from fedsira.config.schema import BaselinesConfig
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBaiotDomain,
    deterministic_domain_order,
)
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.records import (
    BooleanValue,
    ClassIndex,
    NamespaceSeed,
    NonNegativeInt,
    PositiveInt,
    Probability,
)

DOMAIN_PARTITION_SEPARATOR = SeedNamespace.DOMAIN_PARTITION.value


def certified_ensemble_post_reference_rounds(baselines_config: BaselinesConfig) -> PositiveInt:
    return baselines_config.multiple_model_certified_ensemble_post_reference_rounds


def certified_ensemble_domain_groups(
    domain_partition_namespace_seed: NamespaceSeed, group_count: PositiveInt
) -> tuple[tuple[NBaiotDomain, ...], ...]:
    ordered = deterministic_domain_order(
        NBAIOT_DOMAIN_ORDER, DOMAIN_PARTITION_SEPARATOR, domain_partition_namespace_seed
    )
    group_size = len(ordered) // group_count
    return tuple(
        ordered[group_index * group_size : (group_index + 1) * group_size]
        for group_index in range(group_count)
    )


def validate_group_without_target_member_uses_supported_only(
    has_target_bearing_member: BooleanValue, group_target_row_count: NonNegativeInt
) -> None:
    if not has_target_bearing_member and group_target_row_count != 0:
        raise ValueError(
            "ensemble group without a target-bearing member must not receive target rows"
        )


def ensemble_predicted_label(
    predicted_labels: Sequence[ClassIndex], softmax_probabilities: Sequence[Sequence[Probability]]
) -> ClassIndex:
    counts: OrderedDict[ClassIndex, NonNegativeInt] = OrderedDict()
    for label in predicted_labels:
        counts[label] = counts.get(label, 0) + 1
    max_count = max(counts.values())
    if max_count > 1:
        return min(label for label, count in counts.items() if count == max_count)

    tied_labels = sorted(set(predicted_labels))
    mean_probability_by_label: OrderedDict[ClassIndex, Probability] = OrderedDict(
        (
            label,
            sum(probabilities[label] for probabilities in softmax_probabilities)
            / len(softmax_probabilities),
        )
        for label in tied_labels
    )
    best_mean_probability = max(mean_probability_by_label.values())
    return min(
        label
        for label, mean_probability in mean_probability_by_label.items()
        if mean_probability == best_mean_probability
    )
