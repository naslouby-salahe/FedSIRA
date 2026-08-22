import math
from pathlib import Path

import pytest

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import DatasetExclusionReason, Role
from fedsira.datasets.nbaiot.preprocessing import (
    NBAIOT_PRIMARY_PREDICTOR_COUNT,
    assign_stream_roles_and_sample_ids,
    classify_row_finiteness,
    supported_class_sampling_caps,
    target_class_sampling_caps,
    validate_all_predictors_finite,
    validate_consistent_predictor_schema,
    validate_predictor_schema,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_TRIGGER_FEATURES, NBaiotClass

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
ROLE_INTERVALS = CONFIG.datasets.primary.role_intervals
SAMPLING_CAPS = CONFIG.datasets.primary.sampling_caps_per_domain


def _valid_header() -> tuple[str, ...]:
    base = tuple(f"feature_{i}" for i in range(NBAIOT_PRIMARY_PREDICTOR_COUNT - 4))
    return (*base, *NBAIOT_TRIGGER_FEATURES)


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
    header = tuple(f"feature_{i}" for i in range(NBAIOT_PRIMARY_PREDICTOR_COUNT))
    with pytest.raises(ValueError, match="missing required trigger features"):
        validate_predictor_schema(header)


def test_validate_consistent_predictor_schema_accepts_identical_headers() -> None:
    header = _valid_header()
    validate_consistent_predictor_schema(header, header)


def test_validate_consistent_predictor_schema_rejects_mismatched_headers() -> None:
    header = _valid_header()
    reordered = (header[1], header[0], *header[2:])
    with pytest.raises(ValueError, match="does not match the canonical reference schema"):
        validate_consistent_predictor_schema(header, reordered)


def test_classify_row_finiteness_accepts_finite_values() -> None:
    assert classify_row_finiteness([1.0, -2.0, 0.0]) is None


def test_classify_row_finiteness_detects_nan() -> None:
    assert classify_row_finiteness([1.0, math.nan]) is DatasetExclusionReason.NON_FINITE_PREDICTOR


def test_classify_row_finiteness_detects_infinity() -> None:
    assert classify_row_finiteness([1.0, math.inf]) is DatasetExclusionReason.NON_FINITE_PREDICTOR


def test_supported_class_sampling_caps_uses_benign_cap_for_benign() -> None:
    caps = supported_class_sampling_caps(SAMPLING_CAPS, NBaiotClass.BENIGN)
    assert caps[Role.REPORT_TEST] == SAMPLING_CAPS.report_test_benign


def test_supported_class_sampling_caps_uses_other_cap_for_non_benign() -> None:
    caps = supported_class_sampling_caps(SAMPLING_CAPS, NBaiotClass.GAFGYT_JUNK)
    assert caps[Role.REPORT_TEST] == SAMPLING_CAPS.report_test_other_supported_per_class


def test_supported_class_sampling_caps_leaves_post_reference_replay_uncapped() -> None:
    caps = supported_class_sampling_caps(SAMPLING_CAPS, NBaiotClass.BENIGN)
    assert caps[Role.POST_REFERENCE_REPLAY] is None


def test_target_class_sampling_caps_matches_configured_target_caps() -> None:
    caps = target_class_sampling_caps(SAMPLING_CAPS)
    assert caps[Role.SOURCE_PROPOSAL] == SAMPLING_CAPS.source_proposal_target
    assert caps[Role.CANDIDATE_SCREEN] == SAMPLING_CAPS.candidate_screen_target
    assert caps[Role.REPRODUCTION] == SAMPLING_CAPS.reproduction_target


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
    roles_seen = {assignment.role for assignment in assignments}
    assert roles_seen.issubset(
        {
            Role.ANCHOR_TRAIN,
            Role.ANCHOR_VALIDATION,
            Role.POST_REFERENCE_REPLAY,
            Role.ROW_VERIFICATION,
            Role.FINAL_GATE,
            Role.REPORT_TEST,
        }
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
    roles_seen = {assignment.role for assignment in assignments}
    assert roles_seen.issubset(
        {
            Role.SOURCE_PROPOSAL,
            Role.CANDIDATE_SCREEN,
            Role.REPRODUCTION,
            Role.ROW_VERIFICATION,
            Role.FINAL_GATE,
            Role.REPORT_TEST,
        }
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
    anchor_train_assignments = [a for a in assignments if a.role is Role.ANCHOR_TRAIN]
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
    anchor_train_assignments = [a for a in assignments if a.role is Role.ANCHOR_TRAIN]
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
    assigned_indices = {a.original_row_index for a in assignments}
    guard_gap_indices = {395, 396, 397, 398, 399, 495, 496, 497, 498, 499}
    assert assigned_indices.isdisjoint(guard_gap_indices)


def test_validate_all_predictors_finite_accepts_finite_numeric_data(tmp_path: Path) -> None:
    path = tmp_path / "clean.csv"
    path.write_text("a,b\n1.0,2.0\n3.0,4.0\n")
    validate_all_predictors_finite(path, ("a", "b"))


def test_validate_all_predictors_finite_rejects_nan(tmp_path: Path) -> None:
    path = tmp_path / "with_nan.csv"
    path.write_text("a,b\n1.0,2.0\n,4.0\n")
    with pytest.raises(ValueError, match="non-finite"):
        validate_all_predictors_finite(path, ("a", "b"))


def test_validate_all_predictors_finite_rejects_nonnumeric_columns(tmp_path: Path) -> None:
    path = tmp_path / "with_text.csv"
    path.write_text("a,b\n1.0,not_a_number\n3.0,also_text\n")
    with pytest.raises(ValueError, match=DatasetExclusionReason.UNPARSEABLE_PREDICTOR.value):
        validate_all_predictors_finite(path, ("a", "b"))
