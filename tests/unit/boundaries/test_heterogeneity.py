from fedsira.boundaries.heterogeneity import (
    apply_quantity_skew_to_cap,
    exclude_source_from_quantity_skew,
    feature_shift_sign,
    quantity_skew_multiplier_by_domain,
    quantity_skew_multiplier_for_domain,
    select_heterogeneity_shift_features,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
HETEROGENEITY_CONFIG = CONFIG.attacks_and_boundaries.heterogeneity


def test_quantity_skew_multiplier_by_domain_is_deterministic_and_uses_all_multipliers() -> None:
    first = quantity_skew_multiplier_by_domain(42, HETEROGENEITY_CONFIG.quantity_skew_multipliers)
    second = quantity_skew_multiplier_by_domain(42, HETEROGENEITY_CONFIG.quantity_skew_multipliers)
    assert first == second
    assert {assignment.domain for assignment in first} == set(NBAIOT_DOMAIN_ORDER)
    assert {assignment.multiplier for assignment in first} == set(
        HETEROGENEITY_CONFIG.quantity_skew_multipliers
    )


def test_exclude_source_from_quantity_skew_removes_only_the_source() -> None:
    assignments = quantity_skew_multiplier_by_domain(
        42,
        HETEROGENEITY_CONFIG.quantity_skew_multipliers,
    )
    source_domain = NBAIOT_DOMAIN_ORDER[0]
    excluded = exclude_source_from_quantity_skew(assignments, source_domain)
    assert all(assignment.domain is not source_domain for assignment in excluded)
    assert len(excluded) == len(assignments) - 1
    for assignment in excluded:
        assert quantity_skew_multiplier_for_domain(assignments, assignment.domain) == (
            assignment.multiplier
        )


def test_apply_quantity_skew_to_cap_floors() -> None:
    assert apply_quantity_skew_to_cap(100, 0.9) == 90
    assert apply_quantity_skew_to_cap(100, 0.35) == 35
    assert apply_quantity_skew_to_cap(3, 0.9) == 2


def test_select_heterogeneity_shift_features_is_deterministic_and_bounded() -> None:
    features = tuple(f"feature-{index}" for index in range(30))
    first = select_heterogeneity_shift_features(
        features,
        42,
        HETEROGENEITY_CONFIG.feature_shift_selected_feature_count,
    )
    second = select_heterogeneity_shift_features(
        features,
        42,
        HETEROGENEITY_CONFIG.feature_shift_selected_feature_count,
    )
    assert first == second
    assert len(first) == HETEROGENEITY_CONFIG.feature_shift_selected_feature_count
    assert set(first).issubset(set(features))


def test_feature_shift_sign_is_deterministic_and_plus_or_minus_one() -> None:
    domain = NBAIOT_DOMAIN_ORDER[0]
    first = feature_shift_sign(domain, "feature-1", 42)
    second = feature_shift_sign(domain, "feature-1", 42)
    assert first == second
    assert first in (1, -1)
