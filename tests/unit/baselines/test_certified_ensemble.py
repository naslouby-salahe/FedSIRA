import pytest

from fedsira.baselines.certified_ensemble import (
    certified_ensemble_domain_groups,
    certified_ensemble_post_reference_rounds,
    ensemble_predicted_label,
    validate_group_without_target_member_uses_supported_only,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
BASELINES_CONFIG = CONFIG.baselines


def test_certified_ensemble_post_reference_rounds_uses_governed_config() -> None:
    assert (
        certified_ensemble_post_reference_rounds()
        == BASELINES_CONFIG.multiple_model_certified_ensemble_post_reference_rounds
    )


def test_certified_ensemble_domain_groups_are_deterministic_disjoint_and_cover_all_domains() -> (
    None
):
    groups = certified_ensemble_domain_groups(42, 3)
    first = certified_ensemble_domain_groups(42, 3)
    assert groups == first
    assert len(groups) == 3
    assert all(len(group) == 3 for group in groups)
    flattened = [domain for group in groups for domain in group]
    assert set(flattened) == set(NBAIOT_DOMAIN_ORDER)
    assert len(flattened) == len(set(flattened))


def test_validate_group_without_target_member_rejects_synthesized_target_rows() -> None:
    validate_group_without_target_member_uses_supported_only(True, 5)
    validate_group_without_target_member_uses_supported_only(False, 0)
    with pytest.raises(ValueError):
        validate_group_without_target_member_uses_supported_only(False, 1)


def test_ensemble_predicted_label_uses_majority_vote_when_unambiguous() -> None:
    assert ensemble_predicted_label([1, 1, 2], [[0.0, 1.0, 0.0]] * 3) == 1


def test_ensemble_predicted_label_breaks_full_tie_by_mean_softmax_then_lowest_class() -> None:
    predicted_labels = [0, 1, 2]
    softmax_probabilities = [
        [0.5, 0.3, 0.2],
        [0.4, 0.4, 0.2],
        [0.3, 0.3, 0.4],
    ]
    assert ensemble_predicted_label(predicted_labels, softmax_probabilities) == 0


def test_ensemble_predicted_label_full_tie_with_equal_mean_uses_lowest_class_index() -> None:
    predicted_labels = [0, 1, 2]
    softmax_probabilities = [
        [1 / 3, 1 / 3, 1 / 3],
        [1 / 3, 1 / 3, 1 / 3],
        [1 / 3, 1 / 3, 1 / 3],
    ]
    assert ensemble_predicted_label(predicted_labels, softmax_probabilities) == 0
