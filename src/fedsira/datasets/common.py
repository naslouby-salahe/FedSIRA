from __future__ import annotations

import hashlib
import math
from enum import StrEnum
from pathlib import Path
from typing import Self

import duckdb
from pydantic import model_validator

from fedsira.config import RoleIntervals, SamplingCapsPerDomain, ScalingConfig
from fedsira.domain.enums import Role
from fedsira.domain.types import (
    UINT32_MODULUS,
    ArtifactDigest,
    BooleanValue,
    ClassLabel,
    DatasetColumnName,
    DatasetFileDigest,
    DerivedSeed,
    DomainId,
    FeatureAccumulator,
    FeatureMoment,
    FeatureName,
    FrozenDomainModel,
    OverwriteExisting,
    PreparedViewKey,
    RelativePathText,
    RoleBoundary,
    RolePosition,
    RoleToken,
    RoleWindowContainsSample,
    RowCount,
    SampleIdPrefix,
    SamplingCap,
    SamplingSelectionDigest,
    SchemaVersion,
    SourceRowIndex,
    SquaredFeatureAccumulator,
    TextValue,
)
from fedsira.runtime import framed_bytes

SUPPORTED_ROLE_ORDER: tuple[Role, ...] = (
    Role.ANCHOR_TRAIN,
    Role.ANCHOR_VALIDATION,
    Role.POST_REFERENCE_REPLAY,
    Role.ROW_VERIFICATION,
    Role.FINAL_GATE,
    Role.REPORT_TEST,
)
TARGET_ROLE_ORDER: tuple[Role, ...] = (
    Role.SOURCE_PROPOSAL,
    Role.CANDIDATE_SCREEN,
    Role.REPRODUCTION,
    Role.ROW_VERIFICATION,
    Role.FINAL_GATE,
    Role.REPORT_TEST,
)
TRAINING_AND_SCREENING_ROLES: frozenset[Role] = frozenset(
    (
        Role.ANCHOR_TRAIN,
        Role.ANCHOR_VALIDATION,
        Role.POST_REFERENCE_REPLAY,
        Role.SOURCE_PROPOSAL,
        Role.CANDIDATE_SCREEN,
        Role.REPRODUCTION,
    )
)
EVIDENCE_ROLES: frozenset[Role] = frozenset(
    (Role.ROW_VERIFICATION, Role.FINAL_GATE, Role.REPORT_TEST)
)
PREPROCESSING_SAMPLE_ORDER_SEED: DerivedSeed = (
    int.from_bytes(
        hashlib.sha256(b"FedSIRA|preprocess_sample_order|1").digest()[0:8], byteorder="big"
    )
    % UINT32_MODULUS
)
FILE_DIGEST_CHUNK_BYTES = 1_048_576


class DatasetExclusionReason(StrEnum):
    NON_FINITE_PREDICTOR = "non_finite_predictor"
    UNPARSEABLE_PREDICTOR = "unparseable_predictor"


class RoleWindow(FrozenDomainModel):
    role: Role
    lower_inclusive: RoleBoundary
    upper_exclusive: RoleBoundary

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.lower_inclusive >= self.upper_exclusive:
            raise ValueError(
                f"role interval for {self.role.name} must satisfy lower < upper, "
                f"got [{self.lower_inclusive}, {self.upper_exclusive})"
            )
        return self

    def contains(self, normalized_position: RolePosition) -> RoleWindowContainsSample:
        return self.lower_inclusive <= normalized_position < self.upper_exclusive


class FeatureStatistic(FrozenDomainModel):
    count: RowCount
    total: FeatureAccumulator
    total_squared: SquaredFeatureAccumulator


class FeatureMoments(FrozenDomainModel):
    feature_names: tuple[FeatureName, ...]
    means: tuple[FeatureMoment, ...]
    standard_deviations: tuple[FeatureMoment, ...]
    training_row_count: RowCount

    @model_validator(mode="after")
    def _validate_consistency(self) -> Self:
        if not (len(self.feature_names) == len(self.means) == len(self.standard_deviations)):
            raise ValueError("feature moments must have matching lengths")
        if any(standard_deviation <= 0.0 for standard_deviation in self.standard_deviations):
            raise ValueError("feature standard deviations must be positive")
        return self


class ScalerMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    feature_names: tuple[DatasetColumnName, ...]
    means: tuple[FeatureMoment, ...]
    standard_deviations: tuple[FeatureMoment, ...]
    training_row_count: RowCount


class RoleSamplingCap(FrozenDomainModel):
    role: Role
    cap: SamplingCap | None


if not TRAINING_AND_SCREENING_ROLES.isdisjoint(EVIDENCE_ROLES):
    raise AssertionError("evidence roles must never also be eligible for training/screening")


def role_hash_token(role: Role) -> RoleToken:
    return role.name


def role_from_hash_token(token: RoleToken) -> Role:
    try:
        return Role[token]
    except KeyError as error:
        raise ValueError(f"unsupported role token: {token}") from error


def role_for_normalized_position(
    normalized_position: RolePosition,
    windows: tuple[RoleWindow, ...],
) -> Role | None:
    for window in windows:
        if window.contains(normalized_position):
            return window.role
    return None


def supported_role_windows(role_intervals: RoleIntervals) -> tuple[RoleWindow, ...]:
    return tuple(
        RoleWindow(
            role=role,
            lower_inclusive=role_intervals.supported.interval_for(role)[0],
            upper_exclusive=role_intervals.supported.interval_for(role)[1],
        )
        for role in SUPPORTED_ROLE_ORDER
    )


def target_role_windows(role_intervals: RoleIntervals) -> tuple[RoleWindow, ...]:
    return tuple(
        RoleWindow(
            role=role,
            lower_inclusive=role_intervals.target.interval_for(role)[0],
            upper_exclusive=role_intervals.target.interval_for(role)[1],
        )
        for role in TARGET_ROLE_ORDER
    )


def compute_sample_id(
    sample_id_prefix: SampleIdPrefix,
    normalized_relative_csv_path: RelativePathText,
    file_sha256: ArtifactDigest,
    zero_based_original_row_index: SourceRowIndex,
) -> ArtifactDigest:
    return hashlib.sha256(
        framed_bytes(
            sample_id_prefix,
            normalized_relative_csv_path,
            file_sha256,
            zero_based_original_row_index,
        )
    ).hexdigest()


def compute_file_checksum(path: Path) -> DatasetFileDigest:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(FILE_DIGEST_CHUNK_BYTES), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sampling_cap_selection_digest(
    dataset_file_sha256: DatasetFileDigest,
    domain_hash_token: DomainId,
    class_id: ClassLabel,
    role_hash_token_value: RoleToken,
    original_row_index: SourceRowIndex,
) -> SamplingSelectionDigest:
    return hashlib.sha256(
        framed_bytes(
            dataset_file_sha256,
            domain_hash_token,
            class_id,
            role_hash_token_value,
            original_row_index,
            PREPROCESSING_SAMPLE_ORDER_SEED,
        )
    ).digest()


def apply_sampling_cap(
    dataset_file_sha256: DatasetFileDigest,
    domain_hash_token: DomainId,
    class_id: ClassLabel,
    role_hash_token_value: RoleToken,
    original_row_indices: tuple[SourceRowIndex, ...],
    cap: SamplingCap,
) -> tuple[SourceRowIndex, ...]:
    if len(original_row_indices) <= cap:
        return original_row_indices
    ordered = sorted(
        original_row_indices,
        key=lambda original_row_index: (
            sampling_cap_selection_digest(
                dataset_file_sha256,
                domain_hash_token,
                class_id,
                role_hash_token_value,
                original_row_index,
            ),
            original_row_index,
        ),
    )
    return tuple(ordered[:cap])


def sampling_cap_for_role(
    caps: SamplingCapsPerDomain,
    role: Role,
    is_target: BooleanValue,
    is_benign: BooleanValue,
) -> SamplingCap | None:
    if is_target:
        return _target_sampling_cap(caps, role)
    return _supported_sampling_cap(caps, role, is_benign)


def _target_sampling_cap(caps: SamplingCapsPerDomain, role: Role) -> SamplingCap | None:
    if role is Role.SOURCE_PROPOSAL:
        return caps.source_proposal_target
    if role is Role.CANDIDATE_SCREEN:
        return caps.candidate_screen_target
    if role is Role.REPRODUCTION:
        return caps.reproduction_target
    if role is Role.ROW_VERIFICATION:
        return caps.row_verification_target
    if role is Role.FINAL_GATE:
        return caps.final_gate_target
    if role is Role.REPORT_TEST:
        return caps.report_test_target
    raise ValueError(f"unsupported target-data role: {role.name}")


def _supported_sampling_cap(
    caps: SamplingCapsPerDomain,
    role: Role,
    is_benign: BooleanValue,
) -> SamplingCap | None:
    if role is Role.ANCHOR_TRAIN:
        return caps.anchor_train_per_supported_class
    if role is Role.ANCHOR_VALIDATION:
        return caps.anchor_validation_per_supported_class
    if role is Role.POST_REFERENCE_REPLAY:
        return None
    if role is Role.ROW_VERIFICATION:
        return caps.row_verification_supported_per_supported_class
    if role is Role.FINAL_GATE:
        return caps.final_gate_supported_per_supported_class
    if role is Role.REPORT_TEST:
        return caps.report_test_benign if is_benign else caps.report_test_other_supported_per_class
    raise ValueError(f"unsupported supported-data role: {role.name}")


def fit_feature_moments(
    feature_names: tuple[FeatureName, ...],
    statistics: tuple[FeatureStatistic, ...],
    scaling_config: ScalingConfig,
) -> FeatureMoments:
    if len(feature_names) != len(statistics):
        raise ValueError("feature name count must match statistics count")
    means: list[FeatureMoment] = []
    standard_deviations: list[FeatureMoment] = []
    row_count: RowCount = 0
    for feature_index, feature_name in enumerate(feature_names):
        statistic = statistics[feature_index]
        if statistic.count <= 0:
            raise ValueError(f"feature {feature_name} has no supported anchor-train rows")
        row_count = statistic.count
        mean = statistic.total / statistic.count
        variance = max(statistic.total_squared / statistic.count - mean * mean, 0.0)
        standard_deviation = math.sqrt(variance)
        if standard_deviation == 0.0:
            standard_deviation = scaling_config.zero_standard_deviation_scale
        means.append(mean)
        standard_deviations.append(standard_deviation)
    return FeatureMoments(
        feature_names=feature_names,
        means=tuple(means),
        standard_deviations=tuple(standard_deviations),
        training_row_count=row_count,
    )


def sql_string(value: TextValue) -> TextValue:
    return "'" + value.replace("'", "''") + "'"


def sql_ident(name: DatasetColumnName) -> TextValue:
    return '"' + name.replace('"', '""') + '"'


def varchar_column_map(names: tuple[DatasetColumnName, ...]) -> TextValue:
    return "{" + ", ".join(f"{sql_string(name)}: 'VARCHAR'" for name in names) + "}"


def read_csv_relation(
    path: Path,
    header: tuple[DatasetColumnName, ...],
) -> TextValue:
    return (
        "read_csv("
        f"{sql_string(path.as_posix())}, header=true, delim=',', quote='\"', escape='\"', "
        f"auto_detect=false, columns={varchar_column_map(header)})"
    )


def role_case_sql(position_sql: TextValue, windows: tuple[RoleWindow, ...]) -> TextValue:
    clauses = tuple(
        "WHEN "
        f"{position_sql} >= {window.lower_inclusive} AND {position_sql} < {window.upper_exclusive} "
        f"THEN {sql_string(role_hash_token(window.role))}"
        for window in windows
    )
    return "CASE " + " ".join(clauses) + " END"


def standardized_feature_sql(
    column: DatasetColumnName,
    mean: FeatureMoment,
    standard_deviation: FeatureMoment,
    scaling_config: ScalingConfig,
) -> TextValue:
    expression = f"(({sql_ident(column)} - ({mean})) / ({standard_deviation}))"
    return (
        f"LEAST(GREATEST({expression}, {scaling_config.clip_min}), {scaling_config.clip_max}) "
        f"AS {sql_ident(column)}"
    )


def open_tabular_engine(database_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:" if database_path is None else str(database_path))
    connection.execute("SET threads TO 1")
    return connection


def copy_query_to_parquet(
    connection: duckdb.DuckDBPyConnection,
    query: TextValue,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection.execute(f"COPY ({query}) TO {sql_string(path.as_posix())} (FORMAT PARQUET)")


def write_json_payload(
    path: Path,
    payload: FrozenDomainModel,
    overwrite: OverwriteExisting,
) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")


def view_parquet_path(prepared_root: Path, view_key: PreparedViewKey) -> Path:
    return prepared_root / f"{view_key}.parquet"


def fetch_feature_statistics(
    connection: duckdb.DuckDBPyConnection,
    source_sql: TextValue,
    feature_names: tuple[DatasetColumnName, ...],
) -> tuple[FeatureStatistic, ...]:
    aggregations = ", ".join(
        f"count(*), sum({sql_ident(name)}), sum({sql_ident(name)} * {sql_ident(name)})"
        for name in feature_names
    )
    row = connection.execute(f"SELECT {aggregations} FROM ({source_sql})").fetchone()
    if row is None:
        raise ValueError("feature statistic query returned no row")
    statistics: list[FeatureStatistic] = []
    for feature_index in range(len(feature_names)):
        offset = feature_index * 3
        count = row[offset]
        total = row[offset + 1]
        total_squared = row[offset + 2]
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise TypeError("feature count must be a non-negative integer")
        if total is None or total_squared is None:
            raise ValueError("feature aggregates must be present")
        statistics.append(
            FeatureStatistic(
                count=count,
                total=float(total),
                total_squared=float(total_squared),
            )
        )
    return tuple(statistics)
