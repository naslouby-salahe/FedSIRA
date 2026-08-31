import math
from pathlib import Path
from typing import cast

import pandas
import pytest

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import DatasetExclusionReason, Role, role_hash_token
from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.preprocessing import (
    NBAIOT_PRIMARY_PREDICTOR_COUNT,
    PreparedView,
    RoleSamplingCap,
    assign_stream_roles_and_sample_ids,
    classify_row_finiteness,
    materialize_nbaiot_prepared_views,
    supported_class_sampling_caps,
    target_class_sampling_caps,
    validate_all_predictors_finite,
    validate_consistent_predictor_schema,
    validate_predictor_schema,
    view_parquet_path,
)
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
    NBaiotDomain,
    nbaiot_domain_hash_token,
)
from fedsira.runtime.state import current_application_context

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
ROLE_INTERVALS = CONFIG.datasets.primary.role_intervals
SAMPLING_CAPS = CONFIG.datasets.primary.sampling_caps_per_domain
TRIGGER_FEATURES = (
    "MI_dir_L0.1_weight",
    "H_L0.1_weight",
    "HH_L0.1_magnitude",
    "HpHp_L0.1_mean",
)


def _valid_header() -> tuple[str, ...]:
    base = tuple(f"feature_{index}" for index in range(NBAIOT_PRIMARY_PREDICTOR_COUNT - 4))
    return (*base, *NBAIOT_TRIGGER_FEATURES)


def _cap_for_role(caps: tuple[RoleSamplingCap, ...], role: Role) -> int | None:
    for role_cap in caps:
        if role_cap.role is role:
            return role_cap.cap
    raise AssertionError(f"missing cap for {role.value}")


def test_validate_predictor_schema_accepts_a_well_formed_header() -> None:
    validate_predictor_schema(_valid_header())


def test_validate_predictor_schema_rejects_duplicate_names() -> None:
    header = _valid_header()
    duplicated = (header[0], *header[1:-1], header[0])
    with pytest.raises(ValueError, match="duplicate names"):
        validate_predictor_schema(duplicated)


def test_validate_predictor_schema_rejects_wrong_column_count() -> None:
    with pytest.raises(ValueError, match="expected exactly 115"):
        validate_predictor_schema(("a", "b"))


def test_validate_predictor_schema_rejects_missing_trigger_features() -> None:
    header = tuple(f"feature_{index}" for index in range(NBAIOT_PRIMARY_PREDICTOR_COUNT))
    with pytest.raises(ValueError, match="missing required trigger features"):
        validate_predictor_schema(header)


def test_validate_consistent_predictor_schema_accepts_identical_headers() -> None:
    header = _valid_header()
    validate_consistent_predictor_schema(header, header)


def test_validate_consistent_predictor_schema_rejects_mismatched_headers() -> None:
    header = _valid_header()
    reordered = (header[1], header[0], *header[2:])
    with pytest.raises(ValueError, match="does not match the fixed reference schema"):
        validate_consistent_predictor_schema(header, reordered)


def test_classify_row_finiteness_accepts_finite_values() -> None:
    assert classify_row_finiteness((1.0, -2.0, 0.0)) is None


def test_classify_row_finiteness_detects_nan() -> None:
    assert classify_row_finiteness((1.0, math.nan)) is DatasetExclusionReason.NON_FINITE_PREDICTOR


def test_classify_row_finiteness_detects_infinity() -> None:
    assert classify_row_finiteness((1.0, math.inf)) is DatasetExclusionReason.NON_FINITE_PREDICTOR


def test_supported_class_sampling_caps_uses_benign_cap_for_benign() -> None:
    caps = supported_class_sampling_caps(SAMPLING_CAPS, NBaiotClass.BENIGN)
    assert _cap_for_role(caps, Role.REPORT_TEST) == SAMPLING_CAPS.report_test_benign


def test_supported_class_sampling_caps_uses_other_cap_for_non_benign() -> None:
    caps = supported_class_sampling_caps(SAMPLING_CAPS, NBaiotClass.GAFGYT_JUNK)
    assert _cap_for_role(caps, Role.REPORT_TEST) == (
        SAMPLING_CAPS.report_test_other_supported_per_class
    )


def test_supported_class_sampling_caps_leaves_post_reference_replay_uncapped() -> None:
    caps = supported_class_sampling_caps(SAMPLING_CAPS, NBaiotClass.BENIGN)
    assert _cap_for_role(caps, Role.POST_REFERENCE_REPLAY) is None


def test_target_class_sampling_caps_matches_configured_target_caps() -> None:
    caps = target_class_sampling_caps(SAMPLING_CAPS)
    assert _cap_for_role(caps, Role.SOURCE_PROPOSAL) == SAMPLING_CAPS.source_proposal_target
    assert _cap_for_role(caps, Role.CANDIDATE_SCREEN) == SAMPLING_CAPS.candidate_screen_target
    assert _cap_for_role(caps, Role.REPRODUCTION) == SAMPLING_CAPS.reproduction_target


def test_assign_stream_roles_and_sample_ids_assigns_supported_roles() -> None:
    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path="Danmini_Doorbell/benign_traffic.csv",
        stream_row_count=1000,
        role_intervals=ROLE_INTERVALS,
        sampling_caps_per_domain=SAMPLING_CAPS,
    )
    roles_seen = frozenset(assignment.role for assignment in assignments)
    assert roles_seen.issubset(
        frozenset(
            (
                Role.ANCHOR_TRAIN,
                Role.ANCHOR_VALIDATION,
                Role.POST_REFERENCE_REPLAY,
                Role.ROW_VERIFICATION,
                Role.FINAL_GATE,
                Role.REPORT_TEST,
            )
        )
    )
    assert Role.SOURCE_PROPOSAL not in roles_seen


def test_assign_stream_roles_and_sample_ids_assigns_target_roles() -> None:
    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.GAFGYT_COMBO,
        normalized_relative_csv_path="Danmini_Doorbell/gafgyt_attacks/combo.csv",
        stream_row_count=1000,
        role_intervals=ROLE_INTERVALS,
        sampling_caps_per_domain=SAMPLING_CAPS,
    )
    roles_seen = frozenset(assignment.role for assignment in assignments)
    assert roles_seen.issubset(
        frozenset(
            (
                Role.SOURCE_PROPOSAL,
                Role.CANDIDATE_SCREEN,
                Role.REPRODUCTION,
                Role.ROW_VERIFICATION,
                Role.FINAL_GATE,
                Role.REPORT_TEST,
            )
        )
    )
    assert Role.ANCHOR_TRAIN not in roles_seen


def test_assign_stream_roles_and_sample_ids_respects_the_anchor_train_cap() -> None:
    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path="Danmini_Doorbell/benign_traffic.csv",
        stream_row_count=100_000,
        role_intervals=ROLE_INTERVALS,
        sampling_caps_per_domain=SAMPLING_CAPS,
    )
    anchor_train_assignments = tuple(
        assignment for assignment in assignments if assignment.role is Role.ANCHOR_TRAIN
    )
    assert len(anchor_train_assignments) == SAMPLING_CAPS.anchor_train_per_supported_class


def test_assign_stream_roles_and_sample_ids_uses_all_rows_under_the_cap() -> None:
    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path="Danmini_Doorbell/benign_traffic.csv",
        stream_row_count=10,
        role_intervals=ROLE_INTERVALS,
        sampling_caps_per_domain=SAMPLING_CAPS,
    )
    anchor_train_assignments = tuple(
        assignment for assignment in assignments if assignment.role is Role.ANCHOR_TRAIN
    )
    assert len(anchor_train_assignments) == 4


def test_assign_stream_roles_and_sample_ids_is_deterministic() -> None:
    first = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path="Danmini_Doorbell/benign_traffic.csv",
        stream_row_count=1000,
        role_intervals=ROLE_INTERVALS,
        sampling_caps_per_domain=SAMPLING_CAPS,
    )
    second = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path="Danmini_Doorbell/benign_traffic.csv",
        stream_row_count=1000,
        role_intervals=ROLE_INTERVALS,
        sampling_caps_per_domain=SAMPLING_CAPS,
    )
    assert first == second


def test_assign_stream_roles_and_sample_ids_never_assigns_guard_gap_rows() -> None:
    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=NBaiotClass.BENIGN,
        normalized_relative_csv_path="Danmini_Doorbell/benign_traffic.csv",
        stream_row_count=1000,
        role_intervals=ROLE_INTERVALS,
        sampling_caps_per_domain=SAMPLING_CAPS,
    )
    assigned_indices = frozenset(assignment.original_row_index for assignment in assignments)
    guard_gap_indices = frozenset((395, 396, 397, 398, 399, 495, 496, 497, 498, 499))
    assert assigned_indices.isdisjoint(guard_gap_indices)


def test_validate_all_predictors_finite_accepts_finite_numeric_data(tmp_path: Path) -> None:
    path = tmp_path / "clean.csv"
    path.write_text("a,b\n1.0,2.0\n3.0,4.0\n")
    validate_all_predictors_finite(path, ("a", "b"))


def test_validate_all_predictors_finite_rejects_nan(tmp_path: Path) -> None:
    path = tmp_path / "with_nan.csv"
    path.write_text("a,b\n1.0,2.0\n,4.0\n")
    with pytest.raises(ValueError):
        validate_all_predictors_finite(path, ("a", "b"))


def test_validate_all_predictors_finite_rejects_nonnumeric_columns(tmp_path: Path) -> None:
    path = tmp_path / "with_text.csv"
    path.write_text("a,b\n1.0,not_a_number\n3.0,also_text\n")
    with pytest.raises(ValueError, match=DatasetExclusionReason.UNPARSEABLE_PREDICTOR.value):
        validate_all_predictors_finite(path, ("a", "b"))


def _feature_names() -> list[str]:
    names = [f"feature_{index:03d}" for index in range(NBAIOT_PRIMARY_PREDICTOR_COUNT)]
    for index, trigger in enumerate(TRIGGER_FEATURES):
        names[index] = trigger
    return names


def _write_benign_csv(path: Path, row_count: int) -> None:
    frame = pandas.DataFrame(
        {name: [index * 0.001 for index in range(row_count)] for name in _feature_names()}
    )
    frame.to_csv(path, index=False)


def _discovered_csv(path: Path) -> DiscoveredCsvFile:
    return DiscoveredCsvFile(
        domain=NBaiotDomain.DANMINI_DOORBELL,
        class_id=NBaiotClass.BENIGN,
        relative_path="benign_traffic.csv",
        file_sha256="a" * 64,
        absolute_path=path,
    )


def _storage(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "prepared", tmp_path / "scaler"


def test_prepared_view_row_count() -> None:
    view = PreparedView(
        domain=NBaiotDomain.DANMINI_DOORBELL,
        class_id=NBaiotClass.BENIGN,
        role=Role.ANCHOR_TRAIN,
        sample_ids=("a" * 64, "b" * 64),
        features=((0.0,), (1.0,)),
        labels=("BENIGN", "BENIGN"),
    )
    assert view.row_count == 2


def test_materialization_runs_and_writes_artifacts(tmp_path: Path) -> None:
    csv_path = tmp_path / "benign.csv"
    _write_benign_csv(csv_path, 6000)
    prepared_root, scaler_root = _storage(tmp_path)
    views, moments = materialize_nbaiot_prepared_views(
        (_discovered_csv(csv_path),),
        prepared_root,
        scaler_root,
        overwrite=True,
    )
    assert views
    assert len(moments.feature_names) == NBAIOT_PRIMARY_PREDICTOR_COUNT
    assert (scaler_root / "nbaiot_scaler.json").exists()


def test_materialization_is_deterministic(tmp_path: Path) -> None:
    csv_path = tmp_path / "benign.csv"
    _write_benign_csv(csv_path, 6000)
    prepared_root, scaler_root = _storage(tmp_path)
    discovered = (_discovered_csv(csv_path),)
    views_one, moments_one = materialize_nbaiot_prepared_views(
        discovered,
        prepared_root,
        scaler_root,
        overwrite=True,
    )
    prepared_two = tmp_path / "prepared_two"
    views_two, moments_two = materialize_nbaiot_prepared_views(
        discovered,
        prepared_two,
        scaler_root,
        overwrite=True,
    )
    assert tuple((view.role, view.row_count) for view in views_one) == tuple(
        (view.role, view.row_count) for view in views_two
    )
    assert moments_one.means == moments_two.means
    assert moments_one.standard_deviations == moments_two.standard_deviations


def test_materialization_writes_readable_prepared_row_parquet(tmp_path: Path) -> None:
    csv_path = tmp_path / "benign.csv"
    _write_benign_csv(csv_path, 6000)
    prepared_root, scaler_root = _storage(tmp_path)
    views, moments = materialize_nbaiot_prepared_views(
        (_discovered_csv(csv_path),),
        prepared_root,
        scaler_root,
        overwrite=True,
    )
    assert views
    view = views[0]
    view_key = (
        f"{nbaiot_domain_hash_token(view.domain)}_{view.class_id.value}_"
        f"{role_hash_token(view.role)}"
    )
    parquet_path = view_parquet_path(prepared_root, view_key)
    assert parquet_path.exists()
    frame: pandas.DataFrame = pandas.read_parquet(parquet_path)
    assert len(frame) == view.row_count
    sample_ids = cast("pandas.Series[str]", frame["sample_id"])
    labels = cast("pandas.Series[str]", frame["label"])
    assert tuple(sample_ids) == view.sample_ids
    assert tuple(labels) == view.labels
    for feature_name in moments.feature_names:
        assert feature_name in frame.columns


def test_materialization_standardized_features_are_finite_and_clipped(tmp_path: Path) -> None:
    csv_path = tmp_path / "benign.csv"
    _write_benign_csv(csv_path, 6000)
    prepared_root, scaler_root = _storage(tmp_path)
    views, _moments = materialize_nbaiot_prepared_views(
        (_discovered_csv(csv_path),),
        prepared_root,
        scaler_root,
        overwrite=True,
    )
    assert views
    scaling = current_application_context().scientific_config.datasets.primary.scaling
    clip_max = scaling.clip_max
    clip_min = scaling.clip_min
    for view in views:
        for row in view.features:
            assert all(clip_min <= value <= clip_max for value in row)
