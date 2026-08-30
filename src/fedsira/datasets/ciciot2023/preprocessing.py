from __future__ import annotations

import csv
import hashlib
import heapq
import math
import sqlite3
import struct
from collections.abc import Iterator
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from typing import Annotated, Protocol, TypeAlias, cast

from pydantic import Field

from fedsira.config.schema import RoleIntervals, SamplingCapsPerDomain, ScientificConfig
from fedsira.datasets.ciciot2023.acquisition import (
    SecondaryCsvFile,
    compute_dataset_manifest_hash,
    read_csv_header,
    resolve_label_column,
    validate_consistent_header,
)
from fedsira.datasets.ciciot2023.schema import (
    BENIGN_LABEL,
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    ROW_IDENTIFIER_TOKENS,
    TARGET_LABEL,
    CICIoT2023PseudoDomain,
    build_class_registry,
    hash_to_pseudo_domain,
    normalize_label,
    normalize_label_token,
)
from fedsira.datasets.ciciot2023.validation import (
    validate_label_collisions,
    validate_target_label_present,
)
from fedsira.datasets.common import (
    SUPPORTED_ROLE_ORDER,
    TARGET_ROLE_ORDER,
    DatasetExclusionReason,
    Role,
    role_for_normalized_position,
    role_from_hash_token,
    role_hash_token,
)
from fedsira.datasets.roles import supported_role_windows, target_role_windows
from fedsira.datasets.sampling import (
    PREPROCESSING_SAMPLE_ORDER_SEED,
    SamplingSelectionDigest,
)
from fedsira.datasets.scaling import (
    FeatureMoments,
    FeatureVector,
    accumulate_feature_statistics,
    fit_feature_moments,
    standardize_row,
)
from fedsira.domain.records import (
    ArtifactDigest,
    BooleanValue,
    ClassLabel,
    DatasetClassToken,
    DatasetColumnName,
    DatasetManifestDigest,
    DeterministicInteger,
    FiniteFloat,
    FrozenDomainModel,
    NonNegativeInt,
    OverwriteExisting,
    PartitionSalt,
    PositiveInt,
    PredictorCount,
    PredictorCountMatchesOfficial,
    PreparedViewKey,
    RelativePathText,
    RepositoryPath,
    RolePosition,
    RowCount,
    SampleIdPrefix,
    SamplingCap,
    SchemaVersion,
    TextValue,
)
from fedsira.runtime.determinism import framed_bytes

RawCsvValue = Annotated[str, Field(strict=True)]
FeaturePayloadBytes = Annotated[bytes, Field(min_length=8)]
SqliteScalar: TypeAlias = TextValue | NonNegativeInt | FeaturePayloadBytes
ParquetScalar: TypeAlias = TextValue | NonNegativeInt | FiniteFloat

STABLE_ROW_ID_PREFIX: SampleIdPrefix = "CICIOT2023_SAMPLE_ID_V1"
PREPARED_VIEW_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_prepared_view|1"
SCALER_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_scaler|1"
ROLE_MANIFEST_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_role_manifest|1"
EXCLUSION_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_exclusions|1"
READ_BATCH_ROWS: PositiveInt = 25_000
WRITE_BATCH_ROWS: PositiveInt = 25_000


class _ParquetScalarKind(StrEnum):
    STRING = "string"
    INT64 = "int64"
    FLOAT64 = "float64"


class _ArrowDataType(Protocol):
    pass


class _ArrowArray(Protocol):
    pass


class _ArrowSchema(Protocol):
    pass


class _ArrowTable(Protocol):
    @property
    def schema(self) -> _ArrowSchema: ...


class _ArrowModule(Protocol):
    def array(
        self,
        values: tuple[ParquetScalar, ...],
        data_type: _ArrowDataType,
    ) -> _ArrowArray: ...

    def table(
        self,
        arrays: tuple[_ArrowArray, ...],
        names: tuple[DatasetColumnName, ...],
    ) -> _ArrowTable: ...

    def string(self) -> _ArrowDataType: ...

    def int64(self) -> _ArrowDataType: ...

    def float64(self) -> _ArrowDataType: ...


class _ParquetWriter(Protocol):
    def write_table(self, table: _ArrowTable) -> None: ...

    def close(self) -> None: ...


class _ParquetWriterFactory(Protocol):
    def __call__(self, where: RepositoryPath, schema: _ArrowSchema) -> _ParquetWriter: ...


class _ParquetModule(Protocol):
    ParquetWriter: _ParquetWriterFactory


class SecondaryRawRow(FrozenDomainModel):
    original_row_index: NonNegativeInt
    values: tuple[RawCsvValue, ...]


class SecondaryRetainedRow(FrozenDomainModel):
    stable_row_id: ArtifactDigest
    file_sha256: ArtifactDigest
    relative_path: RelativePathText
    original_row_index: NonNegativeInt
    normalized_label: DatasetClassToken
    pseudo_domain: CICIoT2023PseudoDomain
    features: FeatureVector


class SecondaryExcludedRow(FrozenDomainModel):
    stable_row_id: ArtifactDigest
    file_sha256: ArtifactDigest
    relative_path: RelativePathText
    original_row_index: NonNegativeInt
    reason: DatasetExclusionReason


class SecondaryRoleAssignment(FrozenDomainModel):
    stable_row_id: ArtifactDigest
    normalized_label: DatasetClassToken
    pseudo_domain: CICIoT2023PseudoDomain
    role: Role


class SecondaryPreparedViewSummary(FrozenDomainModel):
    pseudo_domain: CICIoT2023PseudoDomain
    normalized_label: DatasetClassToken
    role: Role
    row_count: RowCount
    parquet_path: Path


class SecondaryMaterializationSummary(FrozenDomainModel):
    dataset_manifest_hash: DatasetManifestDigest
    class_registry: tuple[DatasetClassToken, ...]
    predictor_columns: tuple[DatasetColumnName, ...]
    predictor_count_matches_official: PredictorCountMatchesOfficial
    raw_row_count: RowCount
    retained_row_count: RowCount
    excluded_row_count: RowCount
    views: tuple[SecondaryPreparedViewSummary, ...]
    scaler: FeatureMoments


class _GroupIdentity(FrozenDomainModel):
    normalized_label: DatasetClassToken
    pseudo_domain: CICIoT2023PseudoDomain


class _PreparedViewIdentity(FrozenDomainModel):
    pseudo_domain: CICIoT2023PseudoDomain
    normalized_label: DatasetClassToken
    role: Role
    row_count: RowCount


class _StoredFeatureRow(FrozenDomainModel):
    stable_row_id: ArtifactDigest
    features: FeatureVector


class _PreparedParquetRow(FrozenDomainModel):
    stable_row_id: ArtifactDigest
    normalized_label: DatasetClassToken
    features: FeatureVector


class _PreparedViewMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    pseudo_domain: CICIoT2023PseudoDomain
    normalized_label: DatasetClassToken
    role: Role
    row_count: RowCount


class _ScalerMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    feature_names: tuple[DatasetColumnName, ...]
    means: tuple[FiniteFloat, ...]
    standard_deviations: tuple[FiniteFloat, ...]
    training_row_count: RowCount


def compute_stable_row_id(
    normalized_relative_csv_path: RelativePathText,
    file_sha256: ArtifactDigest,
    zero_based_original_row_index: NonNegativeInt,
) -> ArtifactDigest:
    return hashlib.sha256(
        framed_bytes(
            STABLE_ROW_ID_PREFIX,
            normalized_relative_csv_path,
            file_sha256,
            zero_based_original_row_index,
        )
    ).hexdigest()


def _column_index(
    header: tuple[DatasetColumnName, ...],
    column: DatasetColumnName,
) -> NonNegativeInt:
    try:
        return header.index(column)
    except ValueError as error:
        raise ValueError(f"CICIoT2023 column missing from validated header: {column}") from error


def resolve_predictor_columns(
    header: tuple[DatasetColumnName, ...],
    label_column: DatasetColumnName,
    row_identifier_columns: frozenset[DatasetColumnName] = frozenset(),
) -> tuple[DatasetColumnName, ...]:
    predictors = tuple(
        column
        for column in header
        if column != label_column and column not in row_identifier_columns
    )
    if not predictors:
        raise ValueError("CICIoT2023 resolved no predictor columns")
    if len(set(predictors)) != len(predictors):
        raise ValueError("CICIoT2023 predictor schema contains duplicate names")
    return predictors


def parse_complete_case_rows(
    raw_rows: tuple[SecondaryRawRow, ...],
    *,
    header: tuple[DatasetColumnName, ...],
    relative_path: RelativePathText,
    file_sha256: ArtifactDigest,
    label_column: DatasetColumnName,
    predictor_columns: tuple[DatasetColumnName, ...],
    dataset_manifest_hash: DatasetManifestDigest,
    pseudo_domain_partition_salt: PartitionSalt,
) -> tuple[tuple[SecondaryRetainedRow, ...], tuple[SecondaryExcludedRow, ...]]:
    label_index = _column_index(header, label_column)
    predictor_indices = tuple(_column_index(header, column) for column in predictor_columns)
    retained: list[SecondaryRetainedRow] = []
    excluded: list[SecondaryExcludedRow] = []
    for raw_row in raw_rows:
        if len(raw_row.values) != len(header):
            raise ValueError(
                "CICIoT2023 row width does not match the validated header: "
                f"row={raw_row.original_row_index}, expected={len(header)}, "
                f"observed={len(raw_row.values)}"
            )
        stable_row_id = compute_stable_row_id(
            relative_path,
            file_sha256,
            raw_row.original_row_index,
        )
        try:
            features: FeatureVector = tuple(
                float(raw_row.values[index]) for index in predictor_indices
            )
        except ValueError:
            excluded.append(
                SecondaryExcludedRow(
                    stable_row_id=stable_row_id,
                    file_sha256=file_sha256,
                    relative_path=relative_path,
                    original_row_index=raw_row.original_row_index,
                    reason=DatasetExclusionReason.UNPARSEABLE_PREDICTOR,
                )
            )
            continue
        if any(not math.isfinite(value) for value in features):
            excluded.append(
                SecondaryExcludedRow(
                    stable_row_id=stable_row_id,
                    file_sha256=file_sha256,
                    relative_path=relative_path,
                    original_row_index=raw_row.original_row_index,
                    reason=DatasetExclusionReason.NON_FINITE_PREDICTOR,
                )
            )
            continue
        normalized_label = normalize_label(raw_row.values[label_index])
        pseudo_domain = hash_to_pseudo_domain(
            dataset_manifest_hash,
            normalized_label,
            stable_row_id,
            pseudo_domain_partition_salt,
        )
        retained.append(
            SecondaryRetainedRow(
                stable_row_id=stable_row_id,
                file_sha256=file_sha256,
                relative_path=relative_path,
                original_row_index=raw_row.original_row_index,
                normalized_label=normalized_label,
                pseudo_domain=pseudo_domain,
                features=features,
            )
        )
    return tuple(retained), tuple(excluded)


def assign_pseudo_domains(
    dataset_manifest_hash: DatasetManifestDigest,
    normalized_label: DatasetClassToken,
    stable_row_ids: tuple[ArtifactDigest, ...],
    pseudo_domain_partition_salt: PartitionSalt,
) -> tuple[CICIoT2023PseudoDomain, ...]:
    return tuple(
        hash_to_pseudo_domain(
            dataset_manifest_hash,
            normalized_label,
            stable_row_id,
            pseudo_domain_partition_salt,
        )
        for stable_row_id in stable_row_ids
    )


def order_group_by_stable_row_id(
    stable_row_ids: tuple[ArtifactDigest, ...],
) -> tuple[ArtifactDigest, ...]:
    return tuple(sorted(stable_row_ids, key=bytes.fromhex))


def assign_group_local_roles(
    normalized_label: DatasetClassToken,
    stable_row_ids_ascending: tuple[ArtifactDigest, ...],
    role_intervals: RoleIntervals,
) -> tuple[Role | None, ...]:
    if stable_row_ids_ascending != order_group_by_stable_row_id(stable_row_ids_ascending):
        raise ValueError(
            "CICIoT2023 group rows must be ordered by stable_row_id before role assignment"
        )
    windows = (
        target_role_windows(role_intervals)
        if normalized_label == TARGET_LABEL
        else supported_role_windows(role_intervals)
    )
    group_size = len(stable_row_ids_ascending)
    if group_size == 0:
        return ()
    roles: list[Role | None] = []
    for group_local_index in range(group_size):
        normalized_position: RolePosition = group_local_index / group_size
        roles.append(role_for_normalized_position(normalized_position, windows))
    return tuple(roles)


def sampling_cap_for_secondary_role(
    caps: SamplingCapsPerDomain,
    normalized_label: DatasetClassToken,
    role: Role,
) -> SamplingCap | None:
    if normalized_label == TARGET_LABEL:
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
        return None
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
        return (
            caps.report_test_benign
            if normalized_label == BENIGN_LABEL
            else caps.report_test_other_supported_per_class
        )
    return None


def secondary_sampling_selection_key(
    dataset_manifest_hash: DatasetManifestDigest,
    normalized_label: DatasetClassToken,
    pseudo_domain: CICIoT2023PseudoDomain,
    role: Role,
    stable_row_id: ArtifactDigest,
) -> tuple[SamplingSelectionDigest, ArtifactDigest]:
    digest: SamplingSelectionDigest = hashlib.sha256(
        framed_bytes(
            dataset_manifest_hash,
            pseudo_domain.display_token,
            normalized_label,
            role_hash_token(role),
            stable_row_id,
            PREPROCESSING_SAMPLE_ORDER_SEED,
        )
    ).digest()
    return digest, stable_row_id


def apply_secondary_sampling_cap(
    dataset_manifest_hash: DatasetManifestDigest,
    normalized_label: DatasetClassToken,
    pseudo_domain: CICIoT2023PseudoDomain,
    role: Role,
    stable_row_ids: tuple[ArtifactDigest, ...],
    cap: SamplingCap | None,
) -> tuple[ArtifactDigest, ...]:
    if cap is None or len(stable_row_ids) <= cap:
        return stable_row_ids
    return tuple(
        sorted(
            stable_row_ids,
            key=lambda stable_row_id: secondary_sampling_selection_key(
                dataset_manifest_hash,
                normalized_label,
                pseudo_domain,
                role,
                stable_row_id,
            ),
        )[:cap]
    )


def assign_secondary_roles(
    rows: tuple[SecondaryRetainedRow, ...],
    role_intervals: RoleIntervals,
    sampling_caps: SamplingCapsPerDomain,
    dataset_manifest_hash: DatasetManifestDigest,
) -> tuple[SecondaryRoleAssignment, ...]:
    groups = tuple(
        sorted(
            frozenset((row.normalized_label, row.pseudo_domain) for row in rows),
            key=lambda group: (group[0], int(group[1])),
        )
    )
    assignments: list[SecondaryRoleAssignment] = []
    for normalized_label, pseudo_domain in groups:
        group_rows = tuple(
            sorted(
                (
                    row
                    for row in rows
                    if row.normalized_label == normalized_label
                    and row.pseudo_domain is pseudo_domain
                ),
                key=lambda row: bytes.fromhex(row.stable_row_id),
            )
        )
        stable_row_ids = tuple(row.stable_row_id for row in group_rows)
        roles = assign_group_local_roles(normalized_label, stable_row_ids, role_intervals)
        ordered_roles = (
            TARGET_ROLE_ORDER if normalized_label == TARGET_LABEL else SUPPORTED_ROLE_ORDER
        )
        for role in ordered_roles:
            role_ids = tuple(
                stable_row_id
                for stable_row_id, assigned_role in zip(stable_row_ids, roles, strict=True)
                if assigned_role is role
            )
            selected_ids = apply_secondary_sampling_cap(
                dataset_manifest_hash,
                normalized_label,
                pseudo_domain,
                role,
                role_ids,
                sampling_cap_for_secondary_role(sampling_caps, normalized_label, role),
            )
            assignments.extend(
                SecondaryRoleAssignment(
                    stable_row_id=stable_row_id,
                    normalized_label=normalized_label,
                    pseudo_domain=pseudo_domain,
                    role=role,
                )
                for stable_row_id in selected_ids
            )
    return tuple(assignments)


def _sqlite_int(value: SqliteScalar) -> NonNegativeInt:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise TypeError(f"expected non-negative SQLite integer, received {type(value).__name__}")
    return value


def _sqlite_text(value: SqliteScalar) -> TextValue:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"expected non-empty SQLite text, received {type(value).__name__}")
    return value


def _sqlite_bytes(value: SqliteScalar) -> FeaturePayloadBytes:
    if not isinstance(value, bytes) or not value:
        raise TypeError(f"expected SQLite feature bytes, received {type(value).__name__}")
    return value


class _SecondaryPreparationStore:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("PRAGMA temp_store=FILE")
        self._create_schema()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS retained (
                stable_row_id TEXT PRIMARY KEY,
                file_sha256 TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                original_row_index INTEGER NOT NULL,
                normalized_label TEXT NOT NULL,
                pseudo_domain INTEGER NOT NULL,
                features BLOB NOT NULL
            );
            CREATE INDEX IF NOT EXISTS retained_group_order
                ON retained(normalized_label, pseudo_domain, stable_row_id);
            CREATE TABLE IF NOT EXISTS exclusions (
                stable_row_id TEXT PRIMARY KEY,
                file_sha256 TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                original_row_index INTEGER NOT NULL,
                reason TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS role_assignments (
                stable_row_id TEXT PRIMARY KEY,
                normalized_label TEXT NOT NULL,
                pseudo_domain INTEGER NOT NULL,
                role TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS role_view_order
                ON role_assignments(pseudo_domain, normalized_label, role, stable_row_id);
            """
        )
        self._connection.commit()

    def reset(self) -> None:
        self._connection.executescript(
            "DELETE FROM role_assignments; DELETE FROM exclusions; DELETE FROM retained;"
        )
        self._connection.commit()

    def add_rows(
        self,
        retained: tuple[SecondaryRetainedRow, ...],
        exclusions: tuple[SecondaryExcludedRow, ...],
    ) -> None:
        self._connection.executemany(
            """
            INSERT INTO retained(
                stable_row_id, file_sha256, relative_path, original_row_index,
                normalized_label, pseudo_domain, features
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    row.stable_row_id,
                    row.file_sha256,
                    row.relative_path,
                    row.original_row_index,
                    row.normalized_label,
                    int(row.pseudo_domain),
                    _pack_features(row.features),
                )
                for row in retained
            ),
        )
        self._connection.executemany(
            """
            INSERT INTO exclusions(
                stable_row_id, file_sha256, relative_path, original_row_index, reason
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                (
                    row.stable_row_id,
                    row.file_sha256,
                    row.relative_path,
                    row.original_row_index,
                    row.reason.value,
                )
                for row in exclusions
            ),
        )
        self._connection.commit()

    def groups(self) -> tuple[_GroupIdentity, ...]:
        cursor = self._connection.execute(
            """
            SELECT normalized_label, pseudo_domain
            FROM retained
            GROUP BY normalized_label, pseudo_domain
            ORDER BY normalized_label, pseudo_domain
            """
        )
        groups: list[_GroupIdentity] = []
        for raw_row in cursor:
            row = cast(tuple[SqliteScalar, SqliteScalar], raw_row)
            groups.append(
                _GroupIdentity(
                    normalized_label=_sqlite_text(row[0]),
                    pseudo_domain=CICIoT2023PseudoDomain(_sqlite_int(row[1])),
                )
            )
        return tuple(groups)

    def group_size(self, group: _GroupIdentity) -> RowCount:
        raw_row = self._connection.execute(
            """
            SELECT COUNT(*) FROM retained
            WHERE normalized_label = ? AND pseudo_domain = ?
            """,
            (group.normalized_label, int(group.pseudo_domain)),
        ).fetchone()
        if raw_row is None:
            return 0
        row = cast(tuple[SqliteScalar], raw_row)
        return _sqlite_int(row[0])

    def group_stable_ids(self, group: _GroupIdentity) -> Iterator[ArtifactDigest]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id FROM retained
            WHERE normalized_label = ? AND pseudo_domain = ?
            ORDER BY stable_row_id
            """,
            (group.normalized_label, int(group.pseudo_domain)),
        )
        for raw_row in cursor:
            row = cast(tuple[SqliteScalar], raw_row)
            yield _sqlite_text(row[0])

    def add_role_assignments(
        self,
        group: _GroupIdentity,
        role: Role,
        stable_row_ids: tuple[ArtifactDigest, ...],
    ) -> None:
        if not stable_row_ids:
            return
        self._connection.executemany(
            """
            INSERT INTO role_assignments(stable_row_id, normalized_label, pseudo_domain, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                (
                    stable_row_id,
                    group.normalized_label,
                    int(group.pseudo_domain),
                    role_hash_token(role),
                )
                for stable_row_id in stable_row_ids
            ),
        )
        self._connection.commit()

    def counts(self) -> tuple[RowCount, RowCount]:
        retained_row = self._connection.execute("SELECT COUNT(*) FROM retained").fetchone()
        excluded_row = self._connection.execute("SELECT COUNT(*) FROM exclusions").fetchone()
        if retained_row is None or excluded_row is None:
            raise RuntimeError("CIC preprocessing store count query returned no row")
        retained = _sqlite_int(cast(tuple[SqliteScalar], retained_row)[0])
        excluded = _sqlite_int(cast(tuple[SqliteScalar], excluded_row)[0])
        return retained, excluded

    def assigned_views(self) -> tuple[_PreparedViewIdentity, ...]:
        cursor = self._connection.execute(
            """
            SELECT pseudo_domain, normalized_label, role, COUNT(*)
            FROM role_assignments
            GROUP BY pseudo_domain, normalized_label, role
            ORDER BY pseudo_domain, normalized_label, role
            """
        )
        identities: list[_PreparedViewIdentity] = []
        for raw_row in cursor:
            row = cast(
                tuple[SqliteScalar, SqliteScalar, SqliteScalar, SqliteScalar],
                raw_row,
            )
            identities.append(
                _PreparedViewIdentity(
                    pseudo_domain=CICIoT2023PseudoDomain(_sqlite_int(row[0])),
                    normalized_label=_sqlite_text(row[1]),
                    role=role_from_hash_token(_sqlite_text(row[2])),
                    row_count=_sqlite_int(row[3]),
                )
            )
        return tuple(identities)

    def iter_view_rows(
        self,
        identity: _PreparedViewIdentity,
    ) -> Iterator[_StoredFeatureRow]:
        cursor = self._connection.execute(
            """
            SELECT retained.stable_row_id, retained.features
            FROM role_assignments
            JOIN retained USING(stable_row_id)
            WHERE role_assignments.pseudo_domain = ?
              AND role_assignments.normalized_label = ?
              AND role_assignments.role = ?
            ORDER BY retained.stable_row_id
            """,
            (
                int(identity.pseudo_domain),
                identity.normalized_label,
                role_hash_token(identity.role),
            ),
        )
        for raw_row in cursor:
            row = cast(tuple[SqliteScalar, SqliteScalar], raw_row)
            yield _StoredFeatureRow(
                stable_row_id=_sqlite_text(row[0]),
                features=_unpack_features(_sqlite_bytes(row[1])),
            )

    def iter_anchor_train_features(self) -> Iterator[FeatureVector]:
        cursor = self._connection.execute(
            """
            SELECT retained.features
            FROM role_assignments
            JOIN retained USING(stable_row_id)
            WHERE role_assignments.role = ? AND retained.normalized_label != ?
            ORDER BY retained.normalized_label, retained.pseudo_domain, retained.stable_row_id
            """,
            (role_hash_token(Role.ANCHOR_TRAIN), TARGET_LABEL),
        )
        for raw_row in cursor:
            row = cast(tuple[SqliteScalar], raw_row)
            yield _unpack_features(_sqlite_bytes(row[0]))

    def iter_exclusions(self) -> Iterator[SecondaryExcludedRow]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id, file_sha256, relative_path, original_row_index, reason
            FROM exclusions ORDER BY relative_path, original_row_index
            """
        )
        for raw_row in cursor:
            row = cast(
                tuple[SqliteScalar, SqliteScalar, SqliteScalar, SqliteScalar, SqliteScalar],
                raw_row,
            )
            yield SecondaryExcludedRow(
                stable_row_id=_sqlite_text(row[0]),
                file_sha256=_sqlite_text(row[1]),
                relative_path=_sqlite_text(row[2]),
                original_row_index=_sqlite_int(row[3]),
                reason=DatasetExclusionReason(_sqlite_text(row[4])),
            )

    def iter_role_manifest(self) -> Iterator[SecondaryRoleAssignment]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id, normalized_label, pseudo_domain, role
            FROM role_assignments
            ORDER BY normalized_label, pseudo_domain, stable_row_id
            """
        )
        for raw_row in cursor:
            row = cast(
                tuple[SqliteScalar, SqliteScalar, SqliteScalar, SqliteScalar],
                raw_row,
            )
            yield SecondaryRoleAssignment(
                stable_row_id=_sqlite_text(row[0]),
                normalized_label=_sqlite_text(row[1]),
                pseudo_domain=CICIoT2023PseudoDomain(_sqlite_int(row[2])),
                role=role_from_hash_token(_sqlite_text(row[3])),
            )

    def close(self) -> None:
        self._connection.close()


def _pack_features(features: FeatureVector) -> FeaturePayloadBytes:
    return struct.pack(f"!{len(features)}d", *features)


def _unpack_features(payload: FeaturePayloadBytes) -> FeatureVector:
    feature_count: PredictorCount = len(payload) // 8
    return tuple(struct.unpack(f"!{feature_count}d", payload))


def _assign_group_role(
    store: _SecondaryPreparationStore,
    group: _GroupIdentity,
    role: Role,
    config: ScientificConfig,
    dataset_manifest_hash: DatasetManifestDigest,
) -> None:
    group_size = store.group_size(group)
    if group_size == 0:
        return
    windows = (
        target_role_windows(config.datasets.primary.role_intervals)
        if group.normalized_label == TARGET_LABEL
        else supported_role_windows(config.datasets.primary.role_intervals)
    )
    cap = sampling_cap_for_secondary_role(
        config.datasets.primary.sampling_caps_per_domain,
        group.normalized_label,
        role,
    )
    if cap is None:
        batch: list[ArtifactDigest] = []
        for group_index, stable_row_id in enumerate(store.group_stable_ids(group)):
            normalized_position: RolePosition = group_index / group_size
            assigned_role = role_for_normalized_position(normalized_position, windows)
            if assigned_role is role:
                batch.append(stable_row_id)
                if len(batch) >= WRITE_BATCH_ROWS:
                    store.add_role_assignments(group, role, tuple(batch))
                    batch.clear()
        if batch:
            store.add_role_assignments(group, role, tuple(batch))
        return
    if cap == 0:
        return
    heap: list[tuple[DeterministicInteger, DeterministicInteger, ArtifactDigest]] = []
    for group_index, stable_row_id in enumerate(store.group_stable_ids(group)):
        normalized_position: RolePosition = group_index / group_size
        assigned_role = role_for_normalized_position(normalized_position, windows)
        if assigned_role is not role:
            continue
        rank_digest, ranked_stable_id = secondary_sampling_selection_key(
            dataset_manifest_hash,
            group.normalized_label,
            group.pseudo_domain,
            role,
            stable_row_id,
        )
        candidate = (
            -int.from_bytes(rank_digest, byteorder="big"),
            -int(ranked_stable_id, 16),
            stable_row_id,
        )
        if len(heap) < cap:
            heapq.heappush(heap, candidate)
        elif candidate > heap[0]:
            heapq.heapreplace(heap, candidate)
    selected_ids = tuple(
        sorted(
            (entry[2] for entry in heap),
            key=lambda stable_row_id: secondary_sampling_selection_key(
                dataset_manifest_hash,
                group.normalized_label,
                group.pseudo_domain,
                role,
                stable_row_id,
            ),
        )
    )
    store.add_role_assignments(group, role, selected_ids)


def _assign_roles(
    store: _SecondaryPreparationStore,
    config: ScientificConfig,
    dataset_manifest_hash: DatasetManifestDigest,
) -> None:
    for group in store.groups():
        ordered_roles = (
            TARGET_ROLE_ORDER
            if group.normalized_label == TARGET_LABEL
            else SUPPORTED_ROLE_ORDER
        )
        for role in ordered_roles:
            _assign_group_role(store, group, role, config, dataset_manifest_hash)


def _fit_secondary_scaler(
    store: _SecondaryPreparationStore,
    predictor_columns: tuple[DatasetColumnName, ...],
    config: ScientificConfig,
) -> FeatureMoments:
    statistics = accumulate_feature_statistics(
        predictor_columns,
        store.iter_anchor_train_features(),
    )
    return fit_feature_moments(
        predictor_columns,
        statistics,
        config.datasets.primary.scaling,
    )


def _arrow_modules() -> tuple[_ArrowModule, _ParquetModule]:
    return (
        cast(_ArrowModule, import_module("pyarrow")),
        cast(_ParquetModule, import_module("pyarrow.parquet")),
    )


def _arrow_type(
    arrow: _ArrowModule,
    kind: _ParquetScalarKind,
) -> _ArrowDataType:
    if kind is _ParquetScalarKind.STRING:
        return arrow.string()
    if kind is _ParquetScalarKind.INT64:
        return arrow.int64()
    return arrow.float64()


def _append_columns(
    path: Path,
    names: tuple[DatasetColumnName, ...],
    kinds: tuple[_ParquetScalarKind, ...],
    columns: tuple[tuple[ParquetScalar, ...], ...],
    writer: _ParquetWriter | None,
) -> _ParquetWriter:
    if not (len(names) == len(kinds) == len(columns)):
        raise ValueError("Parquet column metadata lengths must match")
    arrow, parquet = _arrow_modules()
    arrays = tuple(
        arrow.array(values, _arrow_type(arrow, kind))
        for values, kind in zip(columns, kinds, strict=True)
    )
    table = arrow.table(arrays, names)
    active_writer = writer or parquet.ParquetWriter(str(path), table.schema)
    active_writer.write_table(table)
    return active_writer


def _append_prepared_batch(
    path: Path,
    predictor_columns: tuple[DatasetColumnName, ...],
    batch: tuple[_PreparedParquetRow, ...],
    writer: _ParquetWriter | None,
) -> _ParquetWriter:
    names: tuple[DatasetColumnName, ...] = ("sample_id", "label", *predictor_columns)
    kinds = (
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.STRING,
        *(_ParquetScalarKind.FLOAT64 for _ in predictor_columns),
    )
    feature_columns = tuple(
        tuple(row.features[index] for row in batch)
        for index in range(len(predictor_columns))
    )
    columns: tuple[tuple[ParquetScalar, ...], ...] = (
        tuple(row.stable_row_id for row in batch),
        tuple(row.normalized_label for row in batch),
        *feature_columns,
    )
    return _append_columns(path, names, kinds, columns, writer)


def _write_prepared_views(
    store: _SecondaryPreparationStore,
    predictor_columns: tuple[DatasetColumnName, ...],
    scaler: FeatureMoments,
    config: ScientificConfig,
    prepared_root: Path,
) -> tuple[SecondaryPreparedViewSummary, ...]:
    prepared_root.mkdir(parents=True, exist_ok=True)
    summaries: list[SecondaryPreparedViewSummary] = []
    for identity in store.assigned_views():
        view_key = _view_key(identity.pseudo_domain, identity.normalized_label, identity.role)
        parquet_path = prepared_root / f"{view_key}.parquet"
        writer: _ParquetWriter | None = None
        batch: list[_PreparedParquetRow] = []
        try:
            for stored_row in store.iter_view_rows(identity):
                batch.append(
                    _PreparedParquetRow(
                        stable_row_id=stored_row.stable_row_id,
                        normalized_label=identity.normalized_label,
                        features=standardize_row(
                            stored_row.features,
                            scaler,
                            config.datasets.primary.scaling,
                        ),
                    )
                )
                if len(batch) >= WRITE_BATCH_ROWS:
                    writer = _append_prepared_batch(
                        parquet_path,
                        predictor_columns,
                        tuple(batch),
                        writer,
                    )
                    batch.clear()
            if batch:
                writer = _append_prepared_batch(
                    parquet_path,
                    predictor_columns,
                    tuple(batch),
                    writer,
                )
        finally:
            if writer is not None:
                writer.close()
        metadata = _PreparedViewMetadata(
            schema_version=PREPARED_VIEW_SCHEMA_VERSION,
            pseudo_domain=identity.pseudo_domain,
            normalized_label=identity.normalized_label,
            role=identity.role,
            row_count=identity.row_count,
        )
        (prepared_root / f"{view_key}.json").write_text(
            metadata.model_dump_json(indent=2),
            encoding="utf-8",
        )
        summaries.append(
            SecondaryPreparedViewSummary(
                pseudo_domain=identity.pseudo_domain,
                normalized_label=identity.normalized_label,
                role=identity.role,
                row_count=identity.row_count,
                parquet_path=parquet_path,
            )
        )
    return tuple(summaries)


def _write_empty_columns(
    path: Path,
    names: tuple[DatasetColumnName, ...],
    kinds: tuple[_ParquetScalarKind, ...],
) -> None:
    writer = _append_columns(
        path,
        names,
        kinds,
        tuple(() for _ in names),
        None,
    )
    writer.close()


def _append_exclusion_batch(
    path: Path,
    batch: tuple[SecondaryExcludedRow, ...],
    writer: _ParquetWriter | None,
) -> _ParquetWriter:
    names: tuple[DatasetColumnName, ...] = (
        "schema_version",
        "stable_row_id",
        "file_sha256",
        "relative_path",
        "original_row_index",
        "reason",
    )
    kinds = (
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.INT64,
        _ParquetScalarKind.STRING,
    )
    columns: tuple[tuple[ParquetScalar, ...], ...] = (
        tuple(EXCLUSION_SCHEMA_VERSION for _ in batch),
        tuple(row.stable_row_id for row in batch),
        tuple(row.file_sha256 for row in batch),
        tuple(row.relative_path for row in batch),
        tuple(row.original_row_index for row in batch),
        tuple(row.reason.value for row in batch),
    )
    return _append_columns(path, names, kinds, columns, writer)


def _write_exclusions(store: _SecondaryPreparationStore, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer: _ParquetWriter | None = None
    batch: list[SecondaryExcludedRow] = []
    try:
        for row in store.iter_exclusions():
            batch.append(row)
            if len(batch) >= WRITE_BATCH_ROWS:
                writer = _append_exclusion_batch(path, tuple(batch), writer)
                batch.clear()
        if batch:
            writer = _append_exclusion_batch(path, tuple(batch), writer)
        elif writer is None:
            _write_empty_columns(
                path,
                (
                    "schema_version",
                    "stable_row_id",
                    "file_sha256",
                    "relative_path",
                    "original_row_index",
                    "reason",
                ),
                (
                    _ParquetScalarKind.STRING,
                    _ParquetScalarKind.STRING,
                    _ParquetScalarKind.STRING,
                    _ParquetScalarKind.STRING,
                    _ParquetScalarKind.INT64,
                    _ParquetScalarKind.STRING,
                ),
            )
    finally:
        if writer is not None:
            writer.close()


def _append_role_batch(
    path: Path,
    batch: tuple[SecondaryRoleAssignment, ...],
    writer: _ParquetWriter | None,
) -> _ParquetWriter:
    names: tuple[DatasetColumnName, ...] = (
        "schema_version",
        "stable_row_id",
        "normalized_label",
        "pseudo_domain",
        "role",
    )
    kinds = (
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.STRING,
        _ParquetScalarKind.STRING,
    )
    columns: tuple[tuple[ParquetScalar, ...], ...] = (
        tuple(ROLE_MANIFEST_SCHEMA_VERSION for _ in batch),
        tuple(row.stable_row_id for row in batch),
        tuple(row.normalized_label for row in batch),
        tuple(row.pseudo_domain.display_token for row in batch),
        tuple(role_hash_token(row.role) for row in batch),
    )
    return _append_columns(path, names, kinds, columns, writer)


def _write_role_manifest(store: _SecondaryPreparationStore, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer: _ParquetWriter | None = None
    batch: list[SecondaryRoleAssignment] = []
    try:
        for row in store.iter_role_manifest():
            batch.append(row)
            if len(batch) >= WRITE_BATCH_ROWS:
                writer = _append_role_batch(path, tuple(batch), writer)
                batch.clear()
        if batch:
            writer = _append_role_batch(path, tuple(batch), writer)
        elif writer is None:
            _write_empty_columns(
                path,
                ("schema_version", "stable_row_id", "normalized_label", "pseudo_domain", "role"),
                (
                    _ParquetScalarKind.STRING,
                    _ParquetScalarKind.STRING,
                    _ParquetScalarKind.STRING,
                    _ParquetScalarKind.STRING,
                    _ParquetScalarKind.STRING,
                ),
            )
    finally:
        if writer is not None:
            writer.close()


def _write_scaler(scaler_root: Path, scaler: FeatureMoments) -> None:
    scaler_root.mkdir(parents=True, exist_ok=True)
    metadata = _ScalerMetadata(
        schema_version=SCALER_SCHEMA_VERSION,
        feature_names=scaler.feature_names,
        means=scaler.means,
        standard_deviations=scaler.standard_deviations,
        training_row_count=scaler.training_row_count,
    )
    (scaler_root / "ciciot2023_scaler.json").write_text(
        metadata.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _view_key(
    pseudo_domain: CICIoT2023PseudoDomain,
    normalized_label: DatasetClassToken,
    role: Role,
) -> PreparedViewKey:
    return f"{pseudo_domain.display_token}_{normalized_label}_{role_hash_token(role)}"


def _persist_complete_case_batch(
    store: _SecondaryPreparationStore,
    raw_batch: tuple[SecondaryRawRow, ...],
    item: SecondaryCsvFile,
    header: tuple[DatasetColumnName, ...],
    label_column: DatasetColumnName,
    predictor_columns: tuple[DatasetColumnName, ...],
    dataset_manifest_hash: DatasetManifestDigest,
    config: ScientificConfig,
) -> None:
    retained, exclusions = parse_complete_case_rows(
        raw_batch,
        header=header,
        relative_path=item.relative_path,
        file_sha256=item.file_sha256,
        label_column=label_column,
        predictor_columns=predictor_columns,
        dataset_manifest_hash=dataset_manifest_hash,
        pseudo_domain_partition_salt=config.datasets.secondary.pseudo_domain_partition_salt,
    )
    store.add_rows(retained, exclusions)


def _is_physical_row_identifier(
    path: Path,
    column_index: NonNegativeInt,
) -> BooleanValue:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return False
        base: NonNegativeInt | None = None
        row_count: RowCount = 0
        for physical_row_index, values in enumerate(reader):
            if column_index >= len(values):
                return False
            try:
                numeric = float(values[column_index])
            except ValueError:
                return False
            if not math.isfinite(numeric) or not numeric.is_integer():
                return False
            observed = int(numeric)
            if base is None:
                if observed not in (0, 1):
                    return False
                base = observed
            if observed != physical_row_index + base:
                return False
            row_count += 1
        return row_count > 0


def _resolve_row_identifier_columns(
    discovered: tuple[SecondaryCsvFile, ...],
    header: tuple[DatasetColumnName, ...],
    label_column: DatasetColumnName,
) -> frozenset[DatasetColumnName]:
    identifiers: set[DatasetColumnName] = set()
    for column_index, column in enumerate(header):
        if column == label_column or normalize_label_token(column) not in ROW_IDENTIFIER_TOKENS:
            continue
        if all(
            _is_physical_row_identifier(item.absolute_path, column_index) for item in discovered
        ):
            identifiers.add(column)
    return frozenset(identifiers)


def materialize_ciciot2023_prepared_views(
    discovered: tuple[SecondaryCsvFile, ...],
    config: ScientificConfig,
    prepared_root: Path,
    scaler_root: Path,
    metadata_root: Path,
    cache_root: Path,
    overwrite: OverwriteExisting = False,
) -> SecondaryMaterializationSummary:
    if not discovered:
        raise ValueError("CICIoT2023 materialization requires discovered CSV shards")
    dataset_manifest_hash = compute_dataset_manifest_hash(discovered)
    reference_header = read_csv_header(discovered[0].absolute_path)
    if len(set(reference_header)) != len(reference_header):
        raise ValueError("CICIoT2023 fixed header contains duplicate names")
    label_column = resolve_label_column(reference_header)
    for item in discovered[1:]:
        validate_consistent_header(reference_header, read_csv_header(item.absolute_path))
    row_identifier_columns = _resolve_row_identifier_columns(
        discovered,
        reference_header,
        label_column,
    )
    predictor_columns = resolve_predictor_columns(
        reference_header,
        label_column,
        row_identifier_columns,
    )
    database_path = cache_root / "ciciot2023_preparation.sqlite3"
    if overwrite and database_path.exists():
        database_path.unlink()
    store = _SecondaryPreparationStore(database_path)
    store.reset()
    raw_labels: set[ClassLabel] = set()
    raw_row_count: RowCount = 0
    try:
        label_index = _column_index(reference_header, label_column)
        for item in discovered:
            with item.absolute_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                try:
                    observed_header = tuple(next(reader))
                except StopIteration as error:
                    raise ValueError(f"CICIoT2023 CSV shard is empty: {item.relative_path}") from error
                validate_consistent_header(
                    reference_header,
                    tuple(column.strip(" \t\r\n\f\v") for column in observed_header),
                )
                raw_batch: list[SecondaryRawRow] = []
                for physical_row_index, values in enumerate(reader):
                    raw_row_count += 1
                    row_values: tuple[RawCsvValue, ...] = tuple(values)
                    if len(row_values) != len(reference_header):
                        raise ValueError(
                            "CICIoT2023 row width does not match validated header: "
                            f"file={item.relative_path}, row={physical_row_index}, "
                            f"expected={len(reference_header)}, observed={len(row_values)}"
                        )
                    raw_labels.add(row_values[label_index])
                    raw_batch.append(
                        SecondaryRawRow(
                            original_row_index=physical_row_index,
                            values=row_values,
                        )
                    )
                    if len(raw_batch) >= READ_BATCH_ROWS:
                        _persist_complete_case_batch(
                            store,
                            tuple(raw_batch),
                            item,
                            reference_header,
                            label_column,
                            predictor_columns,
                            dataset_manifest_hash,
                            config,
                        )
                        raw_batch.clear()
                if raw_batch:
                    _persist_complete_case_batch(
                        store,
                        tuple(raw_batch),
                        item,
                        reference_header,
                        label_column,
                        predictor_columns,
                        dataset_manifest_hash,
                        config,
                    )
        validate_label_collisions(frozenset(raw_labels))
        normalized_labels = frozenset(normalize_label(label) for label in raw_labels)
        validate_target_label_present(normalized_labels)
        class_registry = build_class_registry(normalized_labels)
        _assign_roles(store, config, dataset_manifest_hash)
        scaler = _fit_secondary_scaler(store, predictor_columns, config)
        views = _write_prepared_views(store, predictor_columns, scaler, config, prepared_root)
        metadata_root.mkdir(parents=True, exist_ok=True)
        _write_exclusions(store, metadata_root / "dataset_exclusions.parquet")
        _write_role_manifest(store, metadata_root / "ciciot2023_role_manifest.parquet")
        _write_scaler(scaler_root, scaler)
        retained_count, excluded_count = store.counts()
        return SecondaryMaterializationSummary(
            dataset_manifest_hash=dataset_manifest_hash,
            class_registry=class_registry,
            predictor_columns=predictor_columns,
            predictor_count_matches_official=(
                len(predictor_columns) == OFFICIAL_EXPECTED_PREDICTOR_COUNT
            ),
            raw_row_count=raw_row_count,
            retained_row_count=retained_count,
            excluded_row_count=excluded_count,
            views=views,
            scaler=scaler,
        )
    finally:
        store.close()
