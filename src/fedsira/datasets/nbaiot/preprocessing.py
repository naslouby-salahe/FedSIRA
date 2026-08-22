import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas

from fedsira.config.schema import RoleIntervals, SamplingCapsPerDomain
from fedsira.datasets.common import (
    ROLE_HASH_TOKEN,
    DatasetExclusionReason,
    Role,
    compute_sample_id,
    role_for_normalized_position,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_TRIGGER_FEATURES, NBaiotClass
from fedsira.datasets.roles import supported_role_windows, target_role_windows
from fedsira.datasets.sampling import apply_sampling_cap
from fedsira.domain.records import ArtifactDigest, CanonicalToken, NonNegativeInt

NBAIOT_PRIMARY_PREDICTOR_COUNT = 115
NBAIOT_SAMPLE_ID_PREFIX = "NBAIOT_SAMPLE_ID_V1"


def validate_predictor_schema(ordered_header: tuple[CanonicalToken, ...]) -> None:
    if len(set(ordered_header)) != len(ordered_header):
        raise ValueError("primary predictor header contains duplicate names")
    if len(ordered_header) != NBAIOT_PRIMARY_PREDICTOR_COUNT:
        raise ValueError(
            f"primary predictor header has {len(ordered_header)} columns, expected exactly "
            f"{NBAIOT_PRIMARY_PREDICTOR_COUNT}"
        )
    missing_trigger_features = [
        feature for feature in NBAIOT_TRIGGER_FEATURES if feature not in ordered_header
    ]
    if missing_trigger_features:
        raise ValueError(
            f"primary predictor header is missing required trigger features: "
            f"{missing_trigger_features}"
        )


def validate_consistent_predictor_schema(
    reference_header: tuple[CanonicalToken, ...], observed_header: tuple[CanonicalToken, ...]
) -> None:
    if observed_header != reference_header:
        raise ValueError("primary predictor header does not match the canonical reference schema")


def classify_row_finiteness(values: Sequence[float]) -> DatasetExclusionReason | None:
    for value in values:
        if math.isnan(value) or math.isinf(value):
            return DatasetExclusionReason.NON_FINITE_PREDICTOR
    return None


def read_predictor_header(path: Path) -> tuple[CanonicalToken, ...]:
    header = pandas.read_csv(path, nrows=0).columns
    return tuple(str(name).strip() for name in header)


def count_csv_data_rows(path: Path) -> NonNegativeInt:
    with path.open("rb") as handle:
        return sum(1 for _ in handle) - 1


def validate_all_predictors_finite(path: Path, ordered_header: tuple[CanonicalToken, ...]) -> None:
    for chunk in pandas.read_csv(path, usecols=list(ordered_header), chunksize=100_000):
        nonnumeric_columns = [
            column
            for column in chunk.columns
            if not pandas.api.types.is_numeric_dtype(chunk[column])
        ]
        if nonnumeric_columns:
            raise ValueError(
                f"{DatasetExclusionReason.UNPARSEABLE_PREDICTOR.value} in {path}: "
                f"non-numeric predictor columns {nonnumeric_columns}"
            )
        for row_index, row in enumerate(chunk.itertuples(index=False)):
            reason = classify_row_finiteness(row)
            if reason is not None:
                raise ValueError(
                    f"non-finite primary predictor value in {path} at row {row_index}: "
                    f"{reason.value}"
                )


def supported_class_sampling_caps(
    caps: SamplingCapsPerDomain, class_id: NBaiotClass
) -> dict[Role, NonNegativeInt | None]:
    report_test_cap = (
        caps.report_test_benign
        if class_id is NBaiotClass.BENIGN
        else caps.report_test_other_supported_per_class
    )
    return {
        Role.ANCHOR_TRAIN: caps.anchor_train_per_supported_class,
        Role.ANCHOR_VALIDATION: caps.anchor_validation_per_supported_class,
        Role.POST_REFERENCE_REPLAY: None,
        Role.ROW_VERIFICATION: caps.row_verification_supported_per_supported_class,
        Role.FINAL_GATE: caps.final_gate_supported_per_supported_class,
        Role.REPORT_TEST: report_test_cap,
    }


def target_class_sampling_caps(caps: SamplingCapsPerDomain) -> dict[Role, NonNegativeInt | None]:
    return {
        Role.SOURCE_PROPOSAL: caps.source_proposal_target,
        Role.CANDIDATE_SCREEN: caps.candidate_screen_target,
        Role.REPRODUCTION: caps.reproduction_target,
        Role.ROW_VERIFICATION: caps.row_verification_target,
        Role.FINAL_GATE: caps.final_gate_target,
        Role.REPORT_TEST: caps.report_test_target,
    }


@dataclass(frozen=True)
class RoleAssignment:
    sample_id: ArtifactDigest
    role: Role
    original_row_index: NonNegativeInt


def assign_stream_roles_and_sample_ids(
    dataset_file_sha256: ArtifactDigest,
    domain_hash_token: CanonicalToken,
    class_id: NBaiotClass,
    normalized_relative_csv_path: CanonicalToken,
    stream_row_count: NonNegativeInt,
    role_intervals: RoleIntervals,
    sampling_caps_per_domain: SamplingCapsPerDomain,
) -> tuple[RoleAssignment, ...]:
    is_target = class_id is NBaiotClass.GAFGYT_COMBO
    windows = (
        target_role_windows(role_intervals) if is_target else supported_role_windows(role_intervals)
    )
    sampling_caps = (
        target_class_sampling_caps(sampling_caps_per_domain)
        if is_target
        else supported_class_sampling_caps(sampling_caps_per_domain, class_id)
    )

    rows_by_role: dict[Role, list[NonNegativeInt]] = {}
    for original_row_index in range(stream_row_count):
        normalized_position = original_row_index / stream_row_count
        role = role_for_normalized_position(normalized_position, windows)
        if role is None:
            continue
        rows_by_role.setdefault(role, []).append(original_row_index)

    assignments: list[RoleAssignment] = []
    for role, original_row_indices in rows_by_role.items():
        cap = sampling_caps.get(role)
        selected_row_indices = (
            apply_sampling_cap(
                dataset_file_sha256,
                domain_hash_token,
                class_id.value,
                ROLE_HASH_TOKEN[role],
                original_row_indices,
                cap,
            )
            if cap is not None
            else tuple(original_row_indices)
        )
        for original_row_index in selected_row_indices:
            sample_id = compute_sample_id(
                NBAIOT_SAMPLE_ID_PREFIX,
                normalized_relative_csv_path,
                dataset_file_sha256,
                original_row_index,
            )
            assignments.append(
                RoleAssignment(
                    sample_id=sample_id, role=role, original_row_index=original_row_index
                )
            )
    return tuple(assignments)
