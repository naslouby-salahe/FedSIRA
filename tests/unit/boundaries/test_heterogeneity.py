from pathlib import Path

from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import (
    DatasetAdapter,
    apply_quantity_skew_to_cap,
    dataset_specification,
    exclude_source_from_quantity_skew,
    feature_shift_sign,
    quantity_skew_multiplier_by_domain,
    quantity_skew_multiplier_for_domain,
    select_heterogeneity_shift_features,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, nbaiot_domain_hash_token
from fedsira.domain.enums import DatasetId

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
HETEROGENEITY_CONFIG = CONFIG.attacks_and_boundaries.heterogeneity
ADAPTER = DatasetAdapter(
    specification=dataset_specification(DatasetId.N_BAIOT),
    prepared_root=Path("outputs/preprocessing/prepared/N-BaIoT"),
)


def test_quantity_skew_multiplier_by_domain_is_deterministic_and_uses_all_multipliers() -> None:
    first = quantity_skew_multiplier_by_domain(
        ADAPTER, 42, HETEROGENEITY_CONFIG.quantity_skew_multipliers
    )
    second = quantity_skew_multiplier_by_domain(
        ADAPTER, 42, HETEROGENEITY_CONFIG.quantity_skew_multipliers
    )
    assert first == second
    assert {assignment.domain for assignment in first} == set(ADAPTER.domain_ids)
    assert {assignment.multiplier for assignment in first} == set(
        HETEROGENEITY_CONFIG.quantity_skew_multipliers
    )


def test_exclude_source_from_quantity_skew_removes_only_the_source() -> None:
    assignments = quantity_skew_multiplier_by_domain(
        ADAPTER,
        42,
        HETEROGENEITY_CONFIG.quantity_skew_multipliers,
    )
    source_domain = ADAPTER.domain_ids[0]
    excluded = exclude_source_from_quantity_skew(assignments, source_domain)
    assert all(assignment.domain != source_domain for assignment in excluded)
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
    domain_token = nbaiot_domain_hash_token(NBAIOT_DOMAIN_ORDER[0])
    first = feature_shift_sign(domain_token, "feature-1", 42)
    second = feature_shift_sign(domain_token, "feature-1", 42)
    assert first == second
    assert first in (1, -1)
