from fedsira.baselines.source_authority import (
    independent_local_reference_reviewer_is_positive,
    secure_continual_assessment_post_reference_rounds,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
MATERIALITY_CONFIG = CONFIG.metrics_and_statistics.materiality
BASELINES_CONFIG = CONFIG.baselines


def test_secure_continual_assessment_post_reference_rounds_uses_governed_config() -> None:
    assert (
        secure_continual_assessment_post_reference_rounds(BASELINES_CONFIG)
        == BASELINES_CONFIG.secure_continual_assessment_post_reference_rounds
    )


def test_independent_local_reference_reviewer_negative_when_capability_contract_fails() -> None:
    assert (
        independent_local_reference_reviewer_is_positive(
            False, 0.9, 0.9, 0.01, 0.01, MATERIALITY_CONFIG
        )
        is False
    )


def test_independent_local_reference_reviewer_positive_within_noninferiority_margins() -> None:
    assert (
        independent_local_reference_reviewer_is_positive(
            True, 0.88, 0.90, 0.02, 0.01, MATERIALITY_CONFIG
        )
        is True
    )


def test_independent_local_reference_reviewer_negative_beyond_supported_f1_margin() -> None:
    assert (
        independent_local_reference_reviewer_is_positive(
            True, 0.80, 0.90, 0.01, 0.01, MATERIALITY_CONFIG
        )
        is False
    )


def test_independent_local_reference_reviewer_negative_beyond_benign_far_margin() -> None:
    assert (
        independent_local_reference_reviewer_is_positive(
            True, 0.90, 0.90, 0.05, 0.01, MATERIALITY_CONFIG
        )
        is False
    )
