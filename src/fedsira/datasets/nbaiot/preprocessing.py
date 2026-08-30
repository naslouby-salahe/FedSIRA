from __future__ import annotations

import csv
import math
from pathlib import Path

import pandas

from fedsira.config.schema import RoleIntervals, SamplingCapsPerDomain, ScientificConfig
from fedsira.datasets.common import (
    SUPPORTED_ROLE_ORDER,
    TARGET_ROLE_ORDER,
    DatasetExclusionReason,
    Role,
    compute_sample_id,
    role_for_normalized_position,
    role_hash_token,
)
from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
    NBaiotDomain,
    nbaiot_domain_hash_token,
)
from fedsira.datasets.roles import supported_role_windows, target_role_windows
from fedsira.datasets.sampling import apply_sampling_cap
from fedsira.datasets.scaling import (
    FeatureMatrix,
    FeatureMoments,
    FeatureStatistic,
    FeatureVector,
    accumulate_feature_statistics,
    fit_feature_moments,
    standardize_row,
)
from fedsira.domain.records import (
    ArtifactDigest,
    DatasetClassToken,
    DatasetColumnName,
    DomainId,
    FiniteFloat,
    FrozenDomainModel,
    NonNegativeInt,
    OverwriteExisting,
    PredictorCount,
    PreparedViewKey,
    RelativePathText,
    RowCount,
    SampleIdPrefix,
    SamplingCap,
    SchemaVersion,
)

NBAIOT_PRIMARY_PREDICTOR_COUNT: PredictorCount = 115
NBAIOT_SAMPLE_ID_PREFIX: SampleIdPrefix = "NBAIOT_SAMPLE_ID_V1"
PREPARED_VIEW_SCHEMA_VERSION: SchemaVersion = "fedsira|nbaiot_prepared_view|1"
SCALER_SCHEMA_VERSION: SchemaVersion = "fedsira|nbaiot_scaler|1"


class RoleSamplingCap(FrozenDomainModel):
    role: Role
    cap: SamplingCap | None


class RoleAssignment(FrozenDomainModel):
    sample_id: ArtifactDigest
    role: Role
    original_row_index: NonNegativeInt


class PreparedView(FrozenDomainModel):
    domain: NBaiotDomain
    class_id: NBaiotClass
    role: Role
    sample_ids: tuple[ArtifactDigest, ...]
    features: FeatureMatrix
    labels: tuple[DatasetClassToken, ...]

    @property
    def row_count(self) -> RowCount:
        return len(self.sample_ids)


class PreparedViewMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    domain: NBaiotDomain
    class_id: NBaiotClass
    role: Role
    row_count: RowCount


class ScalerMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    feature_names: tuple[DatasetColumnName, ...]
    means: tuple[FiniteFloat, ...]
    standard_deviations: tuple[FiniteFloat, ...]
    training_row_count: RowCount


def validate_predictor_schema(ordered_header: tuple[DatasetColumnName, ...]) -> None:
    if len(set(ordered_header)) != len(ordered_header):
        raise ValueError("primary predictor header contains duplicate names")
    if len(ordered_header) != NBAIOT_PRIMARY_PREDICTOR_COUNT:
        raise ValueError(
            f"primary predictor header has {len(ordered_header)} columns, expected exactly "
            f"{NBAIOT_PRIMARY_PREDICTOR_COUNT}"
        )
    missing_trigger_features = tuple(
        feature for feature in NBAIOT_TRIGGER_FEATURES if feature not in ordered_header
    )
    if missing_trigger_features:
        raise ValueError(
            "primary predictor header is missing required trigger features: "
            f"{missing_trigger_features}"
        )


def validate_consistent_predictor_schema(
    reference_header: tuple[DatasetColumnName, ...],
    observed_header: tuple[DatasetColumnName, ...],
) -> None:
    if observed_header != reference_header:
        raise ValueError("primary predictor header does not match the fixed reference schema")


def classify_row_finiteness(values: FeatureVector) -> DatasetExclusionReason | None:
    for value in values:
        if math.isnan(value) or math.isinf(value):
            return DatasetExclusionReason.NON_FINITE_PREDICTOR
    return None


def read_predictor_header(path: Path) -> tuple[DatasetColumnName, ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError(f"primary CSV is empty: {path}") from error
    return tuple(name.strip() for name in header)


def count_csv_data_rows(path: Path) -> RowCount:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def _read_feature_matrix(
    path: Path,
    ordered_header: tuple[DatasetColumnName, ...],
) -> FeatureMatrix:
    rows: list[FeatureVector] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            observed_header = tuple(name.strip() for name in next(reader))
        except StopIteration as error:
            raise ValueError(f"primary CSV is empty: {path}") from error
        validate_consistent_predictor_schema(ordered_header, observed_header)
        for row_index, row in enumerate(reader):
            if len(row) != len(ordered_header):
                raise ValueError(
                    f"primary predictor row width mismatch in {path} at row {row_index}"
                )
            try:
                numeric_row: FeatureVector = tuple(float(value) for value in row)
            except ValueError as error:
                raise ValueError(
                    f"{DatasetExclusionReason.UNPARSEABLE_PREDICTOR.value} in {path} "
                    f"at row {row_index}"
                ) from error
            reason = classify_row_finiteness(numeric_row)
            if reason is not None:
                raise ValueError(
                    f"non-finite primary predictor value in {path} at row {row_index}: "
                    f"{reason.value}"
                )
            rows.append(numeric_row)
    return tuple(rows)


def validate_all_predictors_finite(
    path: Path,
    ordered_header: tuple[DatasetColumnName, ...],
) -> None:
    _read_feature_matrix(path, ordered_header)


def supported_class_sampling_caps(
    caps: SamplingCapsPerDomain,
    class_id: NBaiotClass,
) -> tuple[RoleSamplingCap, ...]:
    report_test_cap = (
        caps.report_test_benign
        if class_id is NBaiotClass.BENIGN
        else caps.report_test_other_supported_per_class
    )
    return (
        RoleSamplingCap(role=Role.ANCHOR_TRAIN, cap=caps.anchor_train_per_supported_class),
        RoleSamplingCap(
            role=Role.ANCHOR_VALIDATION,
            cap=caps.anchor_validation_per_supported_class,
        ),
        RoleSamplingCap(role=Role.POST_REFERENCE_REPLAY, cap=None),
        RoleSamplingCap(
            role=Role.ROW_VERIFICATION,
            cap=caps.row_verification_supported_per_supported_class,
        ),
        RoleSamplingCap(
            role=Role.FINAL_GATE,
            cap=caps.final_gate_supported_per_supported_class,
        ),
        RoleSamplingCap(role=Role.REPORT_TEST, cap=report_test_cap),
    )


def target_class_sampling_caps(
    caps: SamplingCapsPerDomain,
) -> tuple[RoleSamplingCap, ...]:
    return (
        RoleSamplingCap(role=Role.SOURCE_PROPOSAL, cap=caps.source_proposal_target),
        RoleSamplingCap(role=Role.CANDIDATE_SCREEN, cap=caps.candidate_screen_target),
        RoleSamplingCap(role=Role.REPRODUCTION, cap=caps.reproduction_target),
        RoleSamplingCap(role=Role.ROW_VERIFICATION, cap=caps.row_verification_target),
        RoleSamplingCap(role=Role.FINAL_GATE, cap=caps.final_gate_target),
        RoleSamplingCap(role=Role.REPORT_TEST, cap=caps.report_test_target),
    )


def _sampling_cap_for_role(
    sampling_caps: tuple[RoleSamplingCap, ...],
    role: Role,
) -> SamplingCap | None:
    for role_cap in sampling_caps:
        if role_cap.role is role:
            return role_cap.cap
    raise ValueError(f"sampling cap missing for role {role.value}")


def assign_stream_roles_and_sample_ids(
    dataset_file_sha256: ArtifactDigest,
    domain_hash_token: DomainId,
    class_id: NBaiotClass,
    normalized_relative_csv_path: RelativePathText,
    stream_row_count: RowCount,
    role_intervals: RoleIntervals,
    sampling_caps_per_domain: SamplingCapsPerDomain,
) -> tuple[RoleAssignment, ...]:
    is_target = class_id is NBaiotClass.GAFGYT_COMBO
    windows = (
        target_role_windows(role_intervals) if is_target else supported_role_windows(role_intervals)
    )
    ordered_roles = TARGET_ROLE_ORDER if is_target else SUPPORTED_ROLE_ORDER
    sampling_caps = (
        target_class_sampling_caps(sampling_caps_per_domain)
        if is_target
        else supported_class_sampling_caps(sampling_caps_per_domain, class_id)
    )
    assigned_rows = (
        tuple(
            (
                original_row_index,
                role_for_normalized_position(
                    original_row_index / stream_row_count,
                    windows,
                ),
            )
            for original_row_index in range(stream_row_count)
        )
        if stream_row_count
        else ()
    )
    assignments: list[RoleAssignment] = []
    for role in ordered_roles:
        original_row_indices = tuple(
            original_row_index
            for original_row_index, assigned_role in assigned_rows
            if assigned_role is role
        )
        cap = _sampling_cap_for_role(sampling_caps, role)
        selected_row_indices = (
            apply_sampling_cap(
                dataset_file_sha256,
                domain_hash_token,
                class_id.value,
                role_hash_token(role),
                original_row_indices,
                cap,
            )
            if cap is not None
            else original_row_indices
        )
        assignments.extend(
            RoleAssignment(
                sample_id=compute_sample_id(
                    NBAIOT_SAMPLE_ID_PREFIX,
                    normalized_relative_csv_path,
                    dataset_file_sha256,
                    original_row_index,
                ),
                role=role,
                original_row_index=original_row_index,
            )
            for original_row_index in selected_row_indices
        )
    return tuple(assignments)


def _sample_id_for_row(
    assignments: tuple[RoleAssignment, ...],
    original_row_index: NonNegativeInt,
) -> ArtifactDigest:
    for assignment in assignments:
        if assignment.original_row_index == original_row_index:
            return assignment.sample_id
    raise ValueError(f"sample identity missing for row {original_row_index}")


def _accumulate_anchor_train_statistics(
    item: DiscoveredCsvFile,
    config: ScientificConfig,
    feature_names: tuple[DatasetColumnName, ...],
    existing: tuple[FeatureStatistic, ...] | None,
) -> tuple[FeatureStatistic, ...]:
    row_count = count_csv_data_rows(item.absolute_path)
    assignments = assign_stream_roles_and_sample_ids(
        dataset_file_sha256=item.file_sha256,
        domain_hash_token=nbaiot_domain_hash_token(item.domain),
        class_id=item.class_id,
        normalized_relative_csv_path=f"{item.domain.value}/{item.relative_path}",
        stream_row_count=row_count,
        role_intervals=config.datasets.primary.role_intervals,
        sampling_caps_per_domain=config.datasets.primary.sampling_caps_per_domain,
    )
    anchor_train_rows = frozenset(
        assignment.original_row_index
        for assignment in assignments
        if assignment.role is Role.ANCHOR_TRAIN
    )
    feature_matrix = _read_feature_matrix(item.absolute_path, feature_names)
    selected_matrix: FeatureMatrix = tuple(
        row for row_index, row in enumerate(feature_matrix) if row_index in anchor_train_rows
    )
    return accumulate_feature_statistics(feature_names, selected_matrix, existing)


def _view_key(view: PreparedView) -> PreparedViewKey:
    return (
        f"{nbaiot_domain_hash_token(view.domain)}_{view.class_id.value}_"
        f"{role_hash_token(view.role)}"
    )


def view_parquet_path(prepared_root: Path, view_key: PreparedViewKey) -> Path:
    return prepared_root / f"{view_key}.parquet"


def _write_prepared_view_parquet(
    prepared_root: Path,
    view: PreparedView,
    feature_names: tuple[DatasetColumnName, ...],
    overwrite: OverwriteExisting,
) -> None:
    path = view_parquet_path(prepared_root, _view_key(view))
    if path.exists() and not overwrite:
        return
    rows = tuple(
        (sample_id, label, *features)
        for sample_id, label, features in zip(
            view.sample_ids,
            view.labels,
            view.features,
            strict=True,
        )
    )
    columns = ("sample_id", "label", *feature_names)
    frame = pandas.DataFrame(rows, columns=columns)
    frame.to_parquet(path, index=False)


def _write_metadata(
    path: Path,
    payload: PreparedViewMetadata | ScalerMetadata,
    overwrite: OverwriteExisting,
) -> None:
    if path.exists() and not overwrite:
        return
    path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")


def materialize_nbaiot_prepared_views(
    discovered: tuple[DiscoveredCsvFile, ...],
    config: ScientificConfig,
    prepared_root: Path,
    scaler_root: Path,
    overwrite: OverwriteExisting = False,
) -> tuple[tuple[PreparedView, ...], FeatureMoments]:
    if not discovered:
        raise ValueError("N-BaIoT discovery produced no CSV files")
    feature_names = read_predictor_header(discovered[0].absolute_path)
    validate_predictor_schema(feature_names)
    pooled_statistics: tuple[FeatureStatistic, ...] | None = None
    for item in discovered:
        observed_header = read_predictor_header(item.absolute_path)
        validate_consistent_predictor_schema(feature_names, observed_header)
        if item.class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        pooled_statistics = _accumulate_anchor_train_statistics(
            item,
            config,
            feature_names,
            pooled_statistics,
        )
    if pooled_statistics is None:
        raise ValueError("N-BaIoT has no supported Anchor-Train rows for scaler fitting")
    moments = fit_feature_moments(
        feature_names,
        pooled_statistics,
        config.datasets.primary.scaling,
    )
    views: list[PreparedView] = []
    for item in discovered:
        row_count = count_csv_data_rows(item.absolute_path)
        assignments = assign_stream_roles_and_sample_ids(
            dataset_file_sha256=item.file_sha256,
            domain_hash_token=nbaiot_domain_hash_token(item.domain),
            class_id=item.class_id,
            normalized_relative_csv_path=f"{item.domain.value}/{item.relative_path}",
            stream_row_count=row_count,
            role_intervals=config.datasets.primary.role_intervals,
            sampling_caps_per_domain=config.datasets.primary.sampling_caps_per_domain,
        )
        raw_rows = _read_feature_matrix(item.absolute_path, feature_names)
        ordered_roles = (
            TARGET_ROLE_ORDER if item.class_id is NBaiotClass.GAFGYT_COMBO else SUPPORTED_ROLE_ORDER
        )
        for role in ordered_roles:
            selected_rows = tuple(
                assignment.original_row_index
                for assignment in assignments
                if assignment.role is role
            )
            if not selected_rows:
                continue
            features = tuple(
                standardize_row(
                    raw_rows[original_row_index],
                    moments,
                    config.datasets.primary.scaling,
                )
                for original_row_index in selected_rows
            )
            views.append(
                PreparedView(
                    domain=item.domain,
                    class_id=item.class_id,
                    role=role,
                    sample_ids=tuple(
                        _sample_id_for_row(assignments, original_row_index)
                        for original_row_index in selected_rows
                    ),
                    features=features,
                    labels=tuple(item.class_id.value for _ in selected_rows),
                )
            )
    prepared_root.mkdir(parents=True, exist_ok=True)
    scaler_root.mkdir(parents=True, exist_ok=True)
    for view in views:
        _write_metadata(
            (prepared_root / _view_key(view)).with_suffix(".json"),
            PreparedViewMetadata(
                schema_version=PREPARED_VIEW_SCHEMA_VERSION,
                domain=view.domain,
                class_id=view.class_id,
                role=view.role,
                row_count=view.row_count,
            ),
            overwrite,
        )
        _write_prepared_view_parquet(prepared_root, view, feature_names, overwrite)
    _write_metadata(
        scaler_root / "nbaiot_scaler.json",
        ScalerMetadata(
            schema_version=SCALER_SCHEMA_VERSION,
            feature_names=feature_names,
            means=moments.means,
            standard_deviations=moments.standard_deviations,
            training_row_count=moments.training_row_count,
        ),
        overwrite,
    )
    return tuple(views), moments
