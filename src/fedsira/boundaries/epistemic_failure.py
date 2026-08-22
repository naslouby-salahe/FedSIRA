from collections.abc import Mapping, Sequence

import torch

from fedsira.attacks.source_backdoor import apply_trigger_transform
from fedsira.attacks.transform import select_transform_rows
from fedsira.datasets.nbaiot.schema import NBaiotClass
from fedsira.domain.enums import EvaluationInsufficiencyReason
from fedsira.domain.records import CanonicalToken, NamespaceSeed, Probability
from fedsira.evaluation.aggregation import match_nearest_within_decile
from fedsira.evaluation.records import MetricResult


def select_shared_label_error_rows(
    eligible_benign_row_ids: Sequence[CanonicalToken],
    strength: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[CanonicalToken, ...] | None:
    return select_transform_rows(
        eligible_benign_row_ids, strength, attack_generation_namespace_seed
    )


def relabel_shared_label_error_rows(
    labels_by_row_id: Mapping[CanonicalToken, NBaiotClass],
    selected_row_ids: Sequence[CanonicalToken],
) -> dict[CanonicalToken, NBaiotClass]:
    relabeled = dict(labels_by_row_id)
    for row_id in selected_row_ids:
        relabeled[row_id] = NBaiotClass.GAFGYT_COMBO
    return relabeled


def select_spurious_feature_rows(
    eligible_target_row_ids: Sequence[CanonicalToken],
    strength: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[CanonicalToken, ...] | None:
    return select_transform_rows(
        eligible_target_row_ids, strength, attack_generation_namespace_seed
    )


def apply_shared_spurious_feature(
    standardized_features: torch.Tensor, spurious_feature_index: int, trigger_value: float
) -> torch.Tensor:
    return apply_trigger_transform(standardized_features, [spurious_feature_index], trigger_value)


def apply_attacker_induced_common_context(
    standardized_features: torch.Tensor,
    trigger_feature_indices: Sequence[int],
    trigger_value: float,
) -> torch.Tensor:
    return apply_trigger_transform(standardized_features, trigger_feature_indices, trigger_value)


def match_diagnostic_benign_report_test_rows(
    target_report_losses: Sequence[tuple[CanonicalToken, float]],
    benign_report_test_losses: Sequence[tuple[CanonicalToken, float]],
) -> tuple[tuple[CanonicalToken, CanonicalToken], ...] | None:
    boundary_values = [loss for _, loss in benign_report_test_losses]
    return match_nearest_within_decile(
        target_report_losses, benign_report_test_losses, boundary_values
    )


def diagnostic_marker_metric_or_insufficient(
    matched_pairs: tuple[tuple[CanonicalToken, CanonicalToken], ...] | None,
    marker_value: float,
) -> tuple[MetricResult, EvaluationInsufficiencyReason | None]:
    if matched_pairs is None:
        return (
            MetricResult(None, 0),
            EvaluationInsufficiencyReason.INSUFFICIENT_MATCHED_BENIGN_REPORT_TEST_CONTROLS,
        )
    return MetricResult(marker_value, len(matched_pairs)), None
