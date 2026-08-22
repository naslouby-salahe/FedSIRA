from fedsira.baselines.registry import (
    BASELINE_VALIDATION_FIXTURE_MAP,
    BaselineIdentity,
    BaselineValidationFixture,
)


def test_fixture_map_covers_every_registered_baseline_exactly_once() -> None:
    assert set(BASELINE_VALIDATION_FIXTURE_MAP.keys()) == set(BaselineIdentity)
    assert len(BASELINE_VALIDATION_FIXTURE_MAP) == 17


def test_ordinary_utility_references_use_legitimate_target_capability() -> None:
    ordinary = (
        BaselineIdentity.LOCAL_ONLY_REFERENCE,
        BaselineIdentity.CENTRALIZED_REFERENCE,
        BaselineIdentity.FEDAVG_REFERENCE,
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
        BaselineIdentity.CANDIDATE_FREE_FULL_PATH,
        BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
    )
    for identity in ordinary:
        assert (
            BASELINE_VALIDATION_FIXTURE_MAP[identity]
            is BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY
        )


def test_robust_update_filtering_references_use_model_replacement_backdoor() -> None:
    robust = (
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
        BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE,
        BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER,
        BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN,
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
    )
    for identity in robust:
        assert (
            BASELINE_VALIDATION_FIXTURE_MAP[identity]
            is BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR
        )
