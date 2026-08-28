from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas
from pandas.io.parsers import TextFileReader

from fedsira.config.schema import RoleIntervals, SamplingCapsPerDomain, ScientificConfig
from fedsira.datasets.common import (
    ROLE_HASH_TOKEN,
    DatasetExclusionReason,
    Role,
    compute_sample_id,
    role_for_normalized_position,
)
from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_HASH_TOKEN,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.datasets.roles import supported_role_windows, target_role_windows
from fedsira.datasets.sampling import apply_sampling_cap
from fedsira.datasets.scaling import (
    FeatureMoments,
    accumulate_feature_statistics,
    fit_feature_moments,
    standardize_row,
)
from fedsira.domain.records import (
    ArtifactDigest,
    DatasetClassToken,
    DatasetColumnName,
    NonNegativeInt,
)

NBAIOT_PRIMARY_PREDICTOR_COUNT = 115
NBAIOT_SAMPLE_ID_PREFIX = "NBAIOT_SAMPLE_ID_V1"
PREPARED_VIEW_SCHEMA_VERSION = "fedsira|nbaiot_prepared_view|1"
SCALER_SCHEMA_VERSION = "fedsira|nbaiot_scaler|1"


def validate_predictor_schema(ordered_header: tuple[DatasetColumnName, ...]) -> None:
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
    reference_header: tuple[DatasetColumnName, ...], observed_header: tuple[DatasetColumnName, ...]
) -> None:
    if observed_header != reference_header:
        raise ValueError("primary predictor header does not match the canonical reference schema")


def classify_row_finiteness(values: Sequence[float]) -> DatasetExclusionReason | None:
    for value in values:
        if math.isnan(value) or math.isinf(value):
            return DatasetExclusionReason.NON_FINITE_PREDICTOR
    return None


def read_predictor_header(path: Path) -> tuple[DatasetColumnName, ...]:
    header_frame: pandas.DataFrame = pandas.read_csv(path, nrows=0)
    return tuple(str(name).strip() for name in header_frame.columns)


def count_csv_data_rows(path: Path) -> NonNegativeInt:
    with path.open("rb") as handle:
        return sum(1 for _ in handle) - 1


def validate_all_predictors_finite(
    path: Path, ordered_header: tuple[DatasetColumnName, ...]
) -> None:
    reader: TextFileReader = pandas.read_csv(path, usecols=list(ordered_header), chunksize=100_000)
    chunk_frame: pandas.DataFrame
    for chunk_frame in reader:
        nonnumeric_columns: list[DatasetColumnName] = [
            str(column)
            for column in chunk_frame.columns
            if not pandas.api.types.is_numeric_dtype(chunk_frame[column])
        ]
        if nonnumeric_columns:
            raise ValueError(
                f"{DatasetExclusionReason.UNPARSEABLE_PREDICTOR.value} in {path}: "
                f"non-numeric predictor columns {nonnumeric_columns}"
            )
        for row_index, row in enumerate(chunk_frame.itertuples(index=False, name=None)):
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


@dataclass(frozen=True)
class PreparedView:
    domain: NBaiotDomain
    class_id: NBaiotClass
    role: Role
    sample_ids: tuple[ArtifactDigest, ...]
    features: tuple[tuple[float, ...], ...]
    labels: tuple[DatasetColumnName, ...]

    @property
    def row_count(self) -> int:
        return len(self.sample_ids)


def assign_stream_roles_and_sample_ids(
    dataset_file_sha256: ArtifactDigest,
    domain_hash_token: DatasetColumnName,
    class_id: NBaiotClass,
    normalized_relative_csv_path: DatasetColumnName,
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
                    sample_id=sample_id,
                    role=role,
                    original_row_index=original_row_index,
                )
            )
    return tuple(assignments)


def materialize_nbaiot_prepared_views(
    discovered: Sequence[DiscoveredCsvFile],
    config: ScientificConfig,
    prepared_root: Path,
    scaler_root: Path,
    overwrite: bool = False,
) -> tuple[tuple[PreparedView, ...], FeatureMoments]:
    del overwrite
    role_intervals = config.datasets.primary.role_intervals
    sampling_caps = config.datasets.primary.sampling_caps_per_domain
    scaling_config = config.datasets.primary.scaling

    anchor_train_statistics: dict[DatasetColumnName, tuple[tuple[float, float, float], ...]] = {}
    feature_names = read_predictor_header(discovered[0].absolute_path)

    for item in discovered:
        if item.class_id is not NBaiotClass.GAFGYT_COMBO:
            stream_statistics = _accumulate_anchor_train_statistics(
                item, config, anchor_train_statistics
            )
            anchor_train_statistics.setdefault(item.class_id.value, stream_statistics)

    pooled_statistics: list[tuple[float, float, float]] = []
    for feature_index in range(len(feature_names)):
        count = 0.0
        total = 0.0
        total_squared = 0.0
        for class_statistics in anchor_train_statistics.values():
            count += class_statistics[feature_index][0]
            total += class_statistics[feature_index][1]
            total_squared += class_statistics[feature_index][2]
        pooled_statistics.append((count, total, total_squared))

    moments = fit_feature_moments(feature_names, tuple(pooled_statistics), scaling_config)

    views: list[PreparedView] = []
    for item in discovered:
        row_count = count_csv_data_rows(item.absolute_path)
        assignments = assign_stream_roles_and_sample_ids(
            dataset_file_sha256=item.file_sha256,
            domain_hash_token=NBAIOT_DOMAIN_HASH_TOKEN[item.domain],
            class_id=item.class_id,
            normalized_relative_csv_path=f"{item.domain.value}/{item.relative_path}",
            stream_row_count=row_count,
            role_intervals=role_intervals,
            sampling_caps_per_domain=sampling_caps,
        )
        selected_rows_by_role: dict[Role, list[int]] = {}
        sample_id_by_row: dict[int, ArtifactDigest] = {}
        for assignment in assignments:
            selected_rows_by_role.setdefault(assignment.role, []).append(
                assignment.original_row_index
            )
            sample_id_by_row[assignment.original_row_index] = assignment.sample_id

        frame: pandas.DataFrame = pandas.read_csv(item.absolute_path, usecols=list(feature_names))
        raw_rows = tuple(frame[list(feature_names)].itertuples(index=False, name=None))
        for role, selected_rows in selected_rows_by_role.items():
            if not selected_rows:
                continue
            features: list[tuple[float, ...]] = []
            labels: list[DatasetClassToken] = []
            sample_ids: list[ArtifactDigest] = []
            for original_row_index in selected_rows:
                raw_row = raw_rows[original_row_index]
                standardized_row = standardize_row(raw_row, moments, scaling_config)
                features.append(standardized_row)
                labels.append(item.class_id.value)
                sample_ids.append(sample_id_by_row[original_row_index])
            views.append(
                PreparedView(
                    domain=item.domain,
                    class_id=item.class_id,
                    role=role,
                    sample_ids=tuple(sample_ids),
                    features=tuple(features),
                    labels=tuple(labels),
                )
            )

    prepared_root.mkdir(parents=True, exist_ok=True)
    scaler_root.mkdir(parents=True, exist_ok=True)
    for view in views:
        payload = {
            "schema_version": PREPARED_VIEW_SCHEMA_VERSION,
            "domain": view.domain.value,
            "class_id": view.class_id.value,
            "role": view.role.value,
            "row_count": view.row_count,
        }
        (prepared_root / _view_key(view)).with_suffix(".json").write_text(
            _stable_json(payload), encoding="utf-8"
        )
        _write_prepared_view_parquet(prepared_root, view, tuple(moments.feature_names))
    scaler_payload = {
        "schema_version": SCALER_SCHEMA_VERSION,
        "feature_names": list(moments.feature_names),
        "means": list(moments.means),
        "standard_deviations": list(moments.standard_deviations),
        "training_row_count": moments.training_row_count,
    }
    (scaler_root / "nbaiot_scaler.json").write_text(_stable_json(scaler_payload), encoding="utf-8")
    return tuple(views), moments


def _accumulate_anchor_train_statistics(
    item: DiscoveredCsvFile,
    config: ScientificConfig,
    existing: dict[DatasetColumnName, tuple[tuple[float, float, float], ...]],
) -> tuple[tuple[float, float, float], ...]:
    role_intervals = config.datasets.primary.role_intervals
    sampling_caps = config.datasets.primary.sampling_caps_per_domain
    feature_names = read_predictor_header(item.absolute_path)
    row_count = count_csv_data_rows(item.absolute_path)
    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256=item.file_sha256,
        domain_hash_token=NBAIOT_DOMAIN_HASH_TOKEN[item.domain],
        class_id=item.class_id,
        normalized_relative_csv_path=f"{item.domain.value}/{item.relative_path}",
        stream_row_count=row_count,
        role_intervals=role_intervals,
        sampling_caps_per_domain=sampling_caps,
    )
    anchor_train_rows = {
        assignment.original_row_index
        for assignment in assignments
        if assignment.role is Role.ANCHOR_TRAIN
    }
    frame: pandas.DataFrame = pandas.read_csv(item.absolute_path, usecols=list(feature_names))
    selected_frame = frame.iloc[sorted(anchor_train_rows)]
    statistics = existing.get(item.class_id.value)
    return accumulate_feature_statistics(
        feature_names, selected_frame.itertuples(index=False, name=None), statistics
    )


def _view_key(view: PreparedView) -> str:
    domain_token = NBAIOT_DOMAIN_HASH_TOKEN[view.domain]
    return f"{domain_token}_{view.class_id.value}_{ROLE_HASH_TOKEN[view.role]}"


def view_parquet_path(prepared_root: Path, view_key: DatasetColumnName) -> Path:
    return prepared_root / f"{view_key}.parquet"


def _write_prepared_view_parquet(
    prepared_root: Path,
    view: PreparedView,
    feature_names: tuple[DatasetColumnName, ...],
) -> None:
    columns: dict[str, list[ArtifactDigest] | list[DatasetClassToken] | list[float]] = {
        "sample_id": list(view.sample_ids),
        "label": list(view.labels),
    }
    for feature_index, feature_name in enumerate(feature_names):
        columns[feature_name] = [row[feature_index] for row in view.features]
    frame = pandas.DataFrame(columns)
    frame.to_parquet(view_parquet_path(prepared_root, _view_key(view)), index=False)


def _stable_json(
    payload: Mapping[str, str | int | float | Sequence[str] | Sequence[float]],
) -> str:
    return json.dumps(payload, sort_keys=True, indent=2)
