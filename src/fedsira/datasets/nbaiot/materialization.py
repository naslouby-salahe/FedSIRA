from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas

from fedsira.config.schema import (
    ScientificConfig,
)
from fedsira.datasets.common import ROLE_HASH_TOKEN, Role
from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.preprocessing import (
    assign_stream_roles_and_sample_ids,
    count_csv_data_rows,
    read_predictor_header,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_HASH_TOKEN, NBaiotClass, NBaiotDomain
from fedsira.datasets.scaling import (
    FeatureMoments,
    accumulate_feature_statistics,
    fit_feature_moments,
    standardize_row,
)
from fedsira.domain.records import ArtifactDigest, CanonicalToken

PREPARED_VIEW_SCHEMA_VERSION = "fedsira|nbaiot_prepared_view|1"
SCALER_SCHEMA_VERSION = "fedsira|nbaiot_scaler|1"


@dataclass(frozen=True)
class PreparedView:
    domain: NBaiotDomain
    class_id: NBaiotClass
    role: Role
    sample_ids: tuple[ArtifactDigest, ...]
    features: tuple[tuple[float, ...], ...]
    labels: tuple[CanonicalToken, ...]

    @property
    def row_count(self) -> int:
        return len(self.sample_ids)


def materialize_nbaiot_prepared_views(
    discovered: Sequence[DiscoveredCsvFile],
    config: ScientificConfig,
    prepared_root: Path,
    scaler_root: Path,
    overwrite: bool = False,
) -> tuple[tuple[PreparedView, ...], FeatureMoments]:
    role_intervals = config.datasets.primary.role_intervals
    sampling_caps = config.datasets.primary.sampling_caps_per_domain
    scaling_config = config.datasets.primary.scaling

    anchor_train_statistics: dict[CanonicalToken, tuple[tuple[float, float, float], ...]] = {}
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
            labels: list[CanonicalToken] = []
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
        (prepared_root / _view_key(view)).with_suffix(".json").write_text(_stable_json(payload))
        _write_prepared_view_parquet(prepared_root, view, tuple(moments.feature_names))
    scaler_payload = {
        "schema_version": SCALER_SCHEMA_VERSION,
        "feature_names": list(moments.feature_names),
        "means": list(moments.means),
        "standard_deviations": list(moments.standard_deviations),
        "training_row_count": moments.training_row_count,
    }
    (scaler_root / "nbaiot_scaler.json").write_text(_stable_json(scaler_payload))
    return tuple(views), moments


def _accumulate_anchor_train_statistics(
    item: DiscoveredCsvFile,
    config: ScientificConfig,
    existing: dict[CanonicalToken, tuple[tuple[float, float, float], ...]],
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


def view_parquet_path(prepared_root: Path, view_key: CanonicalToken) -> Path:
    return prepared_root / f"{view_key}.parquet"


def _write_prepared_view_parquet(
    prepared_root: Path, view: PreparedView, feature_names: tuple[CanonicalToken, ...]
) -> None:
    columns: dict[str, list[ArtifactDigest] | list[CanonicalToken] | list[float]] = {
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
    import json

    return json.dumps(payload, sort_keys=True, indent=2)
