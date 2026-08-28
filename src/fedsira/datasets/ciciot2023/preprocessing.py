from __future__ import annotations

import csv
import hashlib
import heapq
import json
import math
import sqlite3
import struct
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast

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
    ROLE_HASH_TOKEN,
    DatasetExclusionReason,
    Role,
    role_for_normalized_position,
)
from fedsira.datasets.roles import supported_role_windows, target_role_windows
from fedsira.datasets.sampling import PREPROCESSING_SAMPLE_ORDER_SEED
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
    PositiveInt,
    PredictorCountMatchesOfficial,
    PredictorValue,
    PreparedViewKey,
    RelativePathText,
    RoleHashToken,
)
from fedsira.runtime.determinism import framed_bytes

STABLE_ROW_ID_PREFIX = "CICIOT2023_SAMPLE_ID_V1"
PREPARED_VIEW_SCHEMA_VERSION = "fedsira|ciciot2023_prepared_view|1"
SCALER_SCHEMA_VERSION = "fedsira|ciciot2023_scaler|1"
ROLE_MANIFEST_SCHEMA_VERSION = "fedsira|ciciot2023_role_manifest|1"
EXCLUSION_SCHEMA_VERSION = "fedsira|ciciot2023_exclusions|1"
READ_BATCH_ROWS = 25_000
WRITE_BATCH_ROWS = 25_000


class _ParquetScalarKind(StrEnum):
    STRING = "string"
    INT64 = "int64"
    FLOAT64 = "float64"


class _ArrowTable(Protocol):
    @property
    def schema(self) -> object: ...


class _ArrowModule(Protocol):
    def table(self, data: Mapping[str, object]) -> _ArrowTable: ...

    def array(self, values: Sequence[object], type: object | None = None) -> object: ...

    def string(self) -> object: ...

    def int64(self) -> object: ...

    def float64(self) -> object: ...


class _ParquetWriter(Protocol):
    def write_table(self, table: _ArrowTable) -> None: ...

    def close(self) -> None: ...


class _ParquetWriterFactory(Protocol):
    def __call__(self, where: str, schema: object) -> _ParquetWriter: ...


class _ParquetModule(Protocol):
    ParquetWriter: _ParquetWriterFactory


@dataclass(frozen=True)
class SecondaryRawRow:
    original_row_index: NonNegativeInt
    values: tuple[str, ...]


@dataclass(frozen=True)
class SecondaryRetainedRow:
    stable_row_id: ArtifactDigest
    file_sha256: ArtifactDigest
    relative_path: RelativePathText
    original_row_index: NonNegativeInt
    canonical_label: DatasetClassToken
    pseudo_domain: CICIoT2023PseudoDomain
    features: tuple[PredictorValue, ...]


@dataclass(frozen=True)
class SecondaryExcludedRow:
    stable_row_id: ArtifactDigest
    file_sha256: ArtifactDigest
    relative_path: RelativePathText
    original_row_index: NonNegativeInt
    reason: DatasetExclusionReason


@dataclass(frozen=True)
class SecondaryRoleAssignment:
    stable_row_id: ArtifactDigest
    canonical_label: DatasetClassToken
    pseudo_domain: CICIoT2023PseudoDomain
    role: Role


@dataclass(frozen=True)
class SecondaryPreparedViewSummary:
    pseudo_domain: CICIoT2023PseudoDomain
    canonical_label: DatasetClassToken
    role: Role
    row_count: NonNegativeInt
    parquet_path: Path


@dataclass(frozen=True)
class SecondaryMaterializationSummary:
    dataset_manifest_hash: ArtifactDigest
    class_registry: tuple[DatasetClassToken, ...]
    predictor_columns: tuple[DatasetColumnName, ...]
    predictor_count_matches_official: PredictorCountMatchesOfficial
    raw_row_count: NonNegativeInt
    retained_row_count: NonNegativeInt
    excluded_row_count: NonNegativeInt
    views: tuple[SecondaryPreparedViewSummary, ...]
    scaler: FeatureMoments


@dataclass(frozen=True)
class _GroupIdentity:
    canonical_label: DatasetClassToken
    pseudo_domain: CICIoT2023PseudoDomain


@dataclass(frozen=True)
class _PreparedViewIdentity:
    pseudo_domain: CICIoT2023PseudoDomain
    canonical_label: DatasetClassToken
    role: Role
    row_count: NonNegativeInt


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
    raw_rows: Sequence[SecondaryRawRow],
    *,
    header: tuple[DatasetColumnName, ...],
    relative_path: RelativePathText,
    file_sha256: ArtifactDigest,
    label_column: DatasetColumnName,
    predictor_columns: tuple[DatasetColumnName, ...],
    dataset_manifest_hash: ArtifactDigest,
    pseudo_domain_partition_salt: PositiveInt,
) -> tuple[tuple[SecondaryRetainedRow, ...], tuple[SecondaryExcludedRow, ...]]:
    column_index = {column: index for index, column in enumerate(header)}
    if len(column_index) != len(header):
        raise ValueError("CICIoT2023 header contains duplicate column names")
    try:
        label_index = column_index[label_column]
        predictor_indices = tuple(column_index[column] for column in predictor_columns)
    except KeyError as error:
        raise ValueError(
            f"CICIoT2023 column missing from validated header: {error.args[0]}"
        ) from error

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
            features = tuple(float(raw_row.values[index]) for index in predictor_indices)
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
        canonical_label = normalize_label(raw_row.values[label_index])
        pseudo_domain = hash_to_pseudo_domain(
            dataset_manifest_hash,
            canonical_label,
            stable_row_id,
            pseudo_domain_partition_salt,
        )
        retained.append(
            SecondaryRetainedRow(
                stable_row_id=stable_row_id,
                file_sha256=file_sha256,
                relative_path=relative_path,
                original_row_index=raw_row.original_row_index,
                canonical_label=canonical_label,
                pseudo_domain=pseudo_domain,
                features=features,
            )
        )
    return tuple(retained), tuple(excluded)


def assign_pseudo_domains(
    dataset_manifest_hash: ArtifactDigest,
    canonical_label: DatasetClassToken,
    stable_row_ids: tuple[ArtifactDigest, ...],
    pseudo_domain_partition_salt: PositiveInt,
) -> tuple[CICIoT2023PseudoDomain, ...]:
    return tuple(
        hash_to_pseudo_domain(
            dataset_manifest_hash,
            canonical_label,
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
    canonical_label: DatasetClassToken,
    stable_row_ids_ascending: tuple[ArtifactDigest, ...],
    role_intervals: RoleIntervals,
) -> tuple[Role | None, ...]:
    if tuple(stable_row_ids_ascending) != order_group_by_stable_row_id(stable_row_ids_ascending):
        raise ValueError(
            "CICIoT2023 group rows must be ordered by stable_row_id before role assignment"
        )
    windows = (
        target_role_windows(role_intervals)
        if canonical_label == TARGET_LABEL
        else supported_role_windows(role_intervals)
    )
    group_size = len(stable_row_ids_ascending)
    if group_size == 0:
        return ()
    return tuple(
        role_for_normalized_position(group_local_index / group_size, windows)
        for group_local_index in range(group_size)
    )


def sampling_cap_for_secondary_role(
    caps: SamplingCapsPerDomain,
    canonical_label: DatasetClassToken,
    role: Role,
) -> NonNegativeInt | None:
    if canonical_label == TARGET_LABEL:
        target_caps: dict[Role, NonNegativeInt | None] = {
            Role.SOURCE_PROPOSAL: caps.source_proposal_target,
            Role.CANDIDATE_SCREEN: caps.candidate_screen_target,
            Role.REPRODUCTION: caps.reproduction_target,
            Role.ROW_VERIFICATION: caps.row_verification_target,
            Role.FINAL_GATE: caps.final_gate_target,
            Role.REPORT_TEST: caps.report_test_target,
        }
        return target_caps.get(role)
    report_cap = (
        caps.report_test_benign
        if canonical_label == BENIGN_LABEL
        else caps.report_test_other_supported_per_class
    )
    supported_caps: dict[Role, NonNegativeInt | None] = {
        Role.ANCHOR_TRAIN: caps.anchor_train_per_supported_class,
        Role.ANCHOR_VALIDATION: caps.anchor_validation_per_supported_class,
        Role.POST_REFERENCE_REPLAY: None,
        Role.ROW_VERIFICATION: caps.row_verification_supported_per_supported_class,
        Role.FINAL_GATE: caps.final_gate_supported_per_supported_class,
        Role.REPORT_TEST: report_cap,
    }
    return supported_caps.get(role)


def secondary_sampling_selection_key(
    dataset_manifest_hash: ArtifactDigest,
    canonical_label: DatasetClassToken,
    pseudo_domain: CICIoT2023PseudoDomain,
    role: Role,
    stable_row_id: ArtifactDigest,
) -> tuple[bytes, ArtifactDigest]:
    digest = hashlib.sha256(
        framed_bytes(
            dataset_manifest_hash,
            pseudo_domain.display_token,
            canonical_label,
            ROLE_HASH_TOKEN[role],
            stable_row_id,
            PREPROCESSING_SAMPLE_ORDER_SEED,
        )
    ).digest()
    return digest, stable_row_id


def apply_secondary_sampling_cap(
    dataset_manifest_hash: ArtifactDigest,
    canonical_label: DatasetClassToken,
    pseudo_domain: CICIoT2023PseudoDomain,
    role: Role,
    stable_row_ids: tuple[ArtifactDigest, ...],
    cap: NonNegativeInt | None,
) -> tuple[ArtifactDigest, ...]:
    if cap is None or len(stable_row_ids) <= cap:
        return stable_row_ids
    return tuple(
        sorted(
            stable_row_ids,
            key=lambda stable_row_id: secondary_sampling_selection_key(
                dataset_manifest_hash,
                canonical_label,
                pseudo_domain,
                role,
                stable_row_id,
            ),
        )[:cap]
    )


def assign_secondary_roles(
    rows: Sequence[SecondaryRetainedRow],
    role_intervals: RoleIntervals,
    sampling_caps: SamplingCapsPerDomain,
    dataset_manifest_hash: ArtifactDigest,
) -> tuple[SecondaryRoleAssignment, ...]:
    rows_by_group: dict[
        tuple[DatasetClassToken, CICIoT2023PseudoDomain], list[SecondaryRetainedRow]
    ] = {}
    for row in rows:
        rows_by_group.setdefault((row.canonical_label, row.pseudo_domain), []).append(row)

    assignments: list[SecondaryRoleAssignment] = []
    for (canonical_label, pseudo_domain), group_rows in sorted(
        rows_by_group.items(),
        key=lambda item: (item[0][0], int(item[0][1])),
    ):
        ordered_rows = sorted(group_rows, key=lambda row: bytes.fromhex(row.stable_row_id))
        stable_row_ids = tuple(row.stable_row_id for row in ordered_rows)
        roles = assign_group_local_roles(canonical_label, stable_row_ids, role_intervals)
        ids_by_role: dict[Role, list[ArtifactDigest]] = {}
        for stable_row_id, role in zip(stable_row_ids, roles, strict=True):
            if role is not None:
                ids_by_role.setdefault(role, []).append(stable_row_id)
        for role, role_ids in ids_by_role.items():
            selected_ids = apply_secondary_sampling_cap(
                dataset_manifest_hash,
                canonical_label,
                pseudo_domain,
                role,
                tuple(role_ids),
                sampling_cap_for_secondary_role(sampling_caps, canonical_label, role),
            )
            assignments.extend(
                SecondaryRoleAssignment(
                    stable_row_id=stable_row_id,
                    canonical_label=canonical_label,
                    pseudo_domain=pseudo_domain,
                    role=role,
                )
                for stable_row_id in selected_ids
            )
    return tuple(assignments)


def _sqlite_int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"expected SQLite integer, received {type(value).__name__}")
    return value


def _sqlite_text(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"expected SQLite text, received {type(value).__name__}")
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
                canonical_label TEXT NOT NULL,
                pseudo_domain INTEGER NOT NULL,
                features BLOB NOT NULL
            );
            CREATE INDEX IF NOT EXISTS retained_group_order
                ON retained(canonical_label, pseudo_domain, stable_row_id);
            CREATE TABLE IF NOT EXISTS exclusions (
                stable_row_id TEXT PRIMARY KEY,
                file_sha256 TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                original_row_index INTEGER NOT NULL,
                reason TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS role_assignments (
                stable_row_id TEXT PRIMARY KEY,
                canonical_label TEXT NOT NULL,
                pseudo_domain INTEGER NOT NULL,
                role TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS role_view_order
                ON role_assignments(pseudo_domain, canonical_label, role, stable_row_id);
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
        retained: Sequence[SecondaryRetainedRow],
        exclusions: Sequence[SecondaryExcludedRow],
    ) -> None:
        self._connection.executemany(
            """
            INSERT INTO retained(
                stable_row_id, file_sha256, relative_path, original_row_index,
                canonical_label, pseudo_domain, features
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    row.stable_row_id,
                    row.file_sha256,
                    row.relative_path,
                    row.original_row_index,
                    row.canonical_label,
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
            SELECT canonical_label, pseudo_domain
            FROM retained
            GROUP BY canonical_label, pseudo_domain
            ORDER BY canonical_label, pseudo_domain
            """
        )
        groups: list[_GroupIdentity] = []
        for raw_row in cursor:
            row = cast(tuple[object, object], raw_row)
            groups.append(
                _GroupIdentity(
                    canonical_label=_sqlite_text(row[0]),
                    pseudo_domain=CICIoT2023PseudoDomain(_sqlite_int(row[1])),
                )
            )
        return tuple(groups)

    def group_size(self, group: _GroupIdentity) -> NonNegativeInt:
        raw_row = self._connection.execute(
            """
            SELECT COUNT(*)
            FROM retained
            WHERE canonical_label = ? AND pseudo_domain = ?
            """,
            (group.canonical_label, int(group.pseudo_domain)),
        ).fetchone()
        if raw_row is None:
            return 0
        row = cast(tuple[object], raw_row)
        return _sqlite_int(row[0])

    def group_stable_ids(self, group: _GroupIdentity) -> Iterator[ArtifactDigest]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id
            FROM retained
            WHERE canonical_label = ? AND pseudo_domain = ?
            ORDER BY stable_row_id
            """,
            (group.canonical_label, int(group.pseudo_domain)),
        )
        for raw_row in cursor:
            row = cast(tuple[object], raw_row)
            yield _sqlite_text(row[0])

    def add_role_assignments(
        self,
        group: _GroupIdentity,
        role: Role,
        stable_row_ids: Sequence[ArtifactDigest],
    ) -> None:
        if not stable_row_ids:
            return
        self._connection.executemany(
            """
            INSERT INTO role_assignments(stable_row_id, canonical_label, pseudo_domain, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                (
                    stable_row_id,
                    group.canonical_label,
                    int(group.pseudo_domain),
                    ROLE_HASH_TOKEN[role],
                )
                for stable_row_id in stable_row_ids
            ),
        )
        self._connection.commit()

    def counts(self) -> tuple[NonNegativeInt, NonNegativeInt]:
        retained_row = self._connection.execute("SELECT COUNT(*) FROM retained").fetchone()
        excluded_row = self._connection.execute("SELECT COUNT(*) FROM exclusions").fetchone()
        if retained_row is None or excluded_row is None:
            raise RuntimeError("CIC preprocessing store count query returned no row")
        retained = _sqlite_int(cast(tuple[object], retained_row)[0])
        excluded = _sqlite_int(cast(tuple[object], excluded_row)[0])
        return retained, excluded

    def assigned_views(self) -> tuple[_PreparedViewIdentity, ...]:
        cursor = self._connection.execute(
            """
            SELECT pseudo_domain, canonical_label, role, COUNT(*)
            FROM role_assignments
            GROUP BY pseudo_domain, canonical_label, role
            ORDER BY pseudo_domain, canonical_label, role
            """
        )
        identities: list[_PreparedViewIdentity] = []
        for raw_row in cursor:
            row = cast(tuple[object, object, object, object], raw_row)
            identities.append(
                _PreparedViewIdentity(
                    pseudo_domain=CICIoT2023PseudoDomain(_sqlite_int(row[0])),
                    canonical_label=_sqlite_text(row[1]),
                    role=_role_from_hash_token(_sqlite_text(row[2])),
                    row_count=_sqlite_int(row[3]),
                )
            )
        return tuple(identities)

    def iter_view_rows(
        self,
        identity: _PreparedViewIdentity,
    ) -> Iterator[tuple[ArtifactDigest, bytes]]:
        cursor = self._connection.execute(
            """
            SELECT retained.stable_row_id, retained.features
            FROM role_assignments
            JOIN retained USING(stable_row_id)
            WHERE role_assignments.pseudo_domain = ?
              AND role_assignments.canonical_label = ?
              AND role_assignments.role = ?
            ORDER BY retained.stable_row_id
            """,
            (
                int(identity.pseudo_domain),
                identity.canonical_label,
                ROLE_HASH_TOKEN[identity.role],
            ),
        )
        for raw_row in cursor:
            row = cast(tuple[object, object], raw_row)
            feature_blob = row[1]
            if not isinstance(feature_blob, bytes):
                raise TypeError("CIC prepared feature payload must be bytes")
            yield _sqlite_text(row[0]), feature_blob

    def iter_anchor_train_features(self) -> Iterator[bytes]:
        cursor = self._connection.execute(
            """
            SELECT retained.features
            FROM role_assignments
            JOIN retained USING(stable_row_id)
            WHERE role_assignments.role = ?
              AND retained.canonical_label != ?
            ORDER BY retained.canonical_label, retained.pseudo_domain, retained.stable_row_id
            """,
            (ROLE_HASH_TOKEN[Role.ANCHOR_TRAIN], TARGET_LABEL),
        )
        for raw_row in cursor:
            row = cast(tuple[object], raw_row)
            feature_blob = row[0]
            if not isinstance(feature_blob, bytes):
                raise TypeError("CIC anchor-train feature payload must be bytes")
            yield feature_blob

    def iter_exclusions(self) -> Iterator[tuple[str, str, str, int, str]]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id, file_sha256, relative_path, original_row_index, reason
            FROM exclusions
            ORDER BY relative_path, original_row_index
            """
        )
        for raw_row in cursor:
            row = cast(tuple[object, object, object, object, object], raw_row)
            yield (
                _sqlite_text(row[0]),
                _sqlite_text(row[1]),
                _sqlite_text(row[2]),
                _sqlite_int(row[3]),
                _sqlite_text(row[4]),
            )

    def iter_role_manifest(self) -> Iterator[tuple[str, str, int, str]]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id, canonical_label, pseudo_domain, role
            FROM role_assignments
            ORDER BY canonical_label, pseudo_domain, stable_row_id
            """
        )
        for raw_row in cursor:
            row = cast(tuple[object, object, object, object], raw_row)
            yield (
                _sqlite_text(row[0]),
                _sqlite_text(row[1]),
                _sqlite_int(row[2]),
                _sqlite_text(row[3]),
            )

    def close(self) -> None:
        self._connection.close()


def materialize_ciciot2023_prepared_views(
    discovered: Sequence[SecondaryCsvFile],
    config: ScientificConfig,
    prepared_root: Path,
    scaler_root: Path,
    metadata_root: Path,
    cache_root: Path,
    overwrite: bool = False,
) -> SecondaryMaterializationSummary:
    if not discovered:
        raise ValueError("CICIoT2023 materialization requires discovered CSV shards")

    dataset_manifest_hash = compute_dataset_manifest_hash(discovered)
    reference_header = read_csv_header(discovered[0].absolute_path)
    if len(set(reference_header)) != len(reference_header):
        raise ValueError("CICIoT2023 canonical header contains duplicate names")
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
    raw_labels: set[DatasetClassToken] = set()
    raw_row_count = 0
    try:
        label_index = reference_header.index(label_column)
        for item in discovered:
            with item.absolute_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                observed_header = tuple(next(reader))
                validate_consistent_header(
                    reference_header,
                    tuple(column.strip(" \t\r\n\f\v") for column in observed_header),
                )
                raw_batch: list[SecondaryRawRow] = []
                for physical_row_index, values in enumerate(reader):
                    raw_row_count += 1
                    row_values = tuple(values)
                    if len(row_values) != len(reference_header):
                        raise ValueError(
                            "CICIoT2023 row width does not match validated header: "
                            f"file={item.relative_path}, row={physical_row_index}, "
                            f"expected={len(reference_header)}, observed={len(row_values)}"
                        )
                    raw_labels.add(row_values[label_index])
                    raw_batch.append(SecondaryRawRow(physical_row_index, row_values))
                    if len(raw_batch) >= READ_BATCH_ROWS:
                        _persist_complete_case_batch(
                            store,
                            raw_batch,
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
                        raw_batch,
                        item,
                        reference_header,
                        label_column,
                        predictor_columns,
                        dataset_manifest_hash,
                        config,
                    )

        validate_label_collisions(frozenset(raw_labels))
        canonical_labels = frozenset(normalize_label(label) for label in raw_labels)
        validate_target_label_present(canonical_labels)
        class_registry = build_class_registry(canonical_labels)

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


def _persist_complete_case_batch(
    store: _SecondaryPreparationStore,
    raw_batch: Sequence[SecondaryRawRow],
    item: SecondaryCsvFile,
    header: tuple[DatasetColumnName, ...],
    label_column: DatasetColumnName,
    predictor_columns: tuple[DatasetColumnName, ...],
    dataset_manifest_hash: ArtifactDigest,
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


def _resolve_row_identifier_columns(
    discovered: Sequence[SecondaryCsvFile],
    header: tuple[DatasetColumnName, ...],
    label_column: DatasetColumnName,
) -> frozenset[DatasetClassToken]:
    identifiers: set[DatasetClassToken] = set()
    for column_index, column in enumerate(header):
        if column == label_column:
            continue
        if normalize_label_token(column) not in ROW_IDENTIFIER_TOKENS:
            continue
        if all(
            _is_physical_row_identifier(item.absolute_path, column_index) for item in discovered
        ):
            identifiers.add(column)
    return frozenset(identifiers)


def _is_physical_row_identifier(path: Path, column_index: NonNegativeInt) -> bool:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return False
        base: int | None = None
        row_count = 0
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


def _assign_roles(
    store: _SecondaryPreparationStore,
    config: ScientificConfig,
    dataset_manifest_hash: ArtifactDigest,
) -> None:
    role_intervals = config.datasets.primary.role_intervals
    caps = config.datasets.primary.sampling_caps_per_domain
    for group in store.groups():
        group_size = store.group_size(group)
        if group_size == 0:
            continue
        windows = (
            target_role_windows(role_intervals)
            if group.canonical_label == TARGET_LABEL
            else supported_role_windows(role_intervals)
        )
        uncapped_batches: dict[Role, list[ArtifactDigest]] = {}
        capped_heaps: dict[Role, list[tuple[int, int, ArtifactDigest]]] = {}
        for group_index, stable_row_id in enumerate(store.group_stable_ids(group)):
            assigned_role = role_for_normalized_position(group_index / group_size, windows)
            if assigned_role is None:
                continue
            cap = sampling_cap_for_secondary_role(caps, group.canonical_label, assigned_role)
            if cap is None:
                batch = uncapped_batches.setdefault(assigned_role, [])
                batch.append(stable_row_id)
                if len(batch) >= WRITE_BATCH_ROWS:
                    store.add_role_assignments(group, assigned_role, batch)
                    batch.clear()
                continue
            if cap == 0:
                continue
            rank_digest, ranked_stable_id = secondary_sampling_selection_key(
                dataset_manifest_hash,
                group.canonical_label,
                group.pseudo_domain,
                assigned_role,
                stable_row_id,
            )
            candidate = (
                -int.from_bytes(rank_digest, byteorder="big"),
                -int(ranked_stable_id, 16),
                stable_row_id,
            )
            heap = capped_heaps.setdefault(assigned_role, [])
            if len(heap) < cap:
                heapq.heappush(heap, candidate)
            elif candidate > heap[0]:
                heapq.heapreplace(heap, candidate)

        for uncapped_role, batch in uncapped_batches.items():
            store.add_role_assignments(group, uncapped_role, batch)
        for capped_role, heap in capped_heaps.items():
            ranked_ids: list[ArtifactDigest] = [entry[2] for entry in heap]
            selected_ids: tuple[ArtifactDigest, ...] = tuple(
                sorted(
                    ranked_ids,
                    key=lambda stable_row_id: secondary_sampling_selection_key(
                        dataset_manifest_hash,
                        group.canonical_label,
                        group.pseudo_domain,
                        capped_role,
                        stable_row_id,
                    ),
                )
            )
            store.add_role_assignments(group, capped_role, selected_ids)


def _fit_secondary_scaler(
    store: _SecondaryPreparationStore,
    predictor_columns: tuple[DatasetColumnName, ...],
    config: ScientificConfig,
) -> FeatureMoments:
    statistics = accumulate_feature_statistics(
        predictor_columns,
        (
            _unpack_features(payload, len(predictor_columns))
            for payload in store.iter_anchor_train_features()
        ),
    )
    return fit_feature_moments(
        predictor_columns,
        statistics,
        config.datasets.primary.scaling,
    )


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
        view_key = _view_key(identity.pseudo_domain, identity.canonical_label, identity.role)
        parquet_path = prepared_root / f"{view_key}.parquet"
        writer: _ParquetWriter | None = None
        columns = _new_prepared_columns(predictor_columns)
        try:
            for stable_row_id, packed_features in store.iter_view_rows(identity):
                standardized = standardize_row(
                    _unpack_features(packed_features, len(predictor_columns)),
                    scaler,
                    config.datasets.primary.scaling,
                )
                cast(list[object], columns["sample_id"]).append(stable_row_id)
                cast(list[object], columns["label"]).append(identity.canonical_label)
                for feature_index, feature_name in enumerate(predictor_columns):
                    cast(list[object], columns[feature_name]).append(standardized[feature_index])
                if len(cast(list[object], columns["sample_id"])) >= WRITE_BATCH_ROWS:
                    writer = _append_parquet_columns(parquet_path, columns, writer)
                    columns = _new_prepared_columns(predictor_columns)
            if cast(list[object], columns["sample_id"]):
                writer = _append_parquet_columns(parquet_path, columns, writer)
        finally:
            if writer is not None:
                writer.close()
        metadata = {
            "schema_version": PREPARED_VIEW_SCHEMA_VERSION,
            "domain": identity.pseudo_domain.display_token,
            "class_id": identity.canonical_label,
            "role": identity.role.value,
            "row_count": identity.row_count,
        }
        (prepared_root / f"{view_key}.json").write_text(
            _stable_json(metadata),
            encoding="utf-8",
        )
        summaries.append(
            SecondaryPreparedViewSummary(
                pseudo_domain=identity.pseudo_domain,
                canonical_label=identity.canonical_label,
                role=identity.role,
                row_count=identity.row_count,
                parquet_path=parquet_path,
            )
        )
    return tuple(summaries)


def _new_prepared_columns(
    predictor_columns: tuple[DatasetColumnName, ...],
) -> dict[str, object]:
    columns: dict[str, object] = {"sample_id": [], "label": []}
    for feature_name in predictor_columns:
        columns[feature_name] = []
    return columns


def _append_parquet_columns(
    path: Path,
    columns: Mapping[str, object],
    writer: _ParquetWriter | None,
) -> _ParquetWriter:
    arrow, parquet = _arrow_modules()
    table = arrow.table(columns)
    active_writer = writer or parquet.ParquetWriter(str(path), table.schema)
    active_writer.write_table(table)
    return active_writer


def _write_exclusions(store: _SecondaryPreparationStore, path: Path) -> None:
    column_kinds = {
        "schema_version": _ParquetScalarKind.STRING,
        "stable_row_id": _ParquetScalarKind.STRING,
        "file_sha256": _ParquetScalarKind.STRING,
        "relative_path": _ParquetScalarKind.STRING,
        "original_row_index": _ParquetScalarKind.INT64,
        "reason": _ParquetScalarKind.STRING,
    }
    rows = (
        {
            "schema_version": EXCLUSION_SCHEMA_VERSION,
            "stable_row_id": stable_id,
            "file_sha256": file_hash,
            "relative_path": relative_path,
            "original_row_index": row_index,
            "reason": reason,
        }
        for stable_id, file_hash, relative_path, row_index, reason in store.iter_exclusions()
    )
    _write_mapping_rows(path, column_kinds, rows)


def _write_role_manifest(store: _SecondaryPreparationStore, path: Path) -> None:
    column_kinds = {
        "schema_version": _ParquetScalarKind.STRING,
        "stable_row_id": _ParquetScalarKind.STRING,
        "canonical_label": _ParquetScalarKind.STRING,
        "pseudo_domain": _ParquetScalarKind.STRING,
        "role": _ParquetScalarKind.STRING,
    }
    rows = (
        {
            "schema_version": ROLE_MANIFEST_SCHEMA_VERSION,
            "stable_row_id": stable_id,
            "canonical_label": label,
            "pseudo_domain": CICIoT2023PseudoDomain(pseudo_domain).display_token,
            "role": role_token,
        }
        for stable_id, label, pseudo_domain, role_token in store.iter_role_manifest()
    )
    _write_mapping_rows(path, column_kinds, rows)


def _write_mapping_rows(
    path: Path,
    column_kinds: Mapping[str, _ParquetScalarKind],
    rows: Iterator[Mapping[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer: _ParquetWriter | None = None
    columns: dict[str, list[object]] = {name: [] for name in column_kinds}
    try:
        for row in rows:
            for name in column_kinds:
                columns[name].append(row[name])
            if len(next(iter(columns.values()))) >= WRITE_BATCH_ROWS:
                writer = _append_parquet_columns(path, columns, writer)
                columns = {name: [] for name in column_kinds}
        if next(iter(columns.values())):
            writer = _append_parquet_columns(path, columns, writer)
        elif writer is None:
            _write_empty_typed_parquet(path, column_kinds)
    finally:
        if writer is not None:
            writer.close()


def _write_empty_typed_parquet(
    path: Path,
    column_kinds: Mapping[str, _ParquetScalarKind],
) -> None:
    arrow, parquet = _arrow_modules()
    arrays: dict[str, object] = {}
    for name, kind in column_kinds.items():
        if kind is _ParquetScalarKind.STRING:
            arrow_type = arrow.string()
        elif kind is _ParquetScalarKind.INT64:
            arrow_type = arrow.int64()
        else:
            arrow_type = arrow.float64()
        arrays[name] = arrow.array((), type=arrow_type)
    table = arrow.table(arrays)
    writer = parquet.ParquetWriter(str(path), table.schema)
    try:
        writer.write_table(table)
    finally:
        writer.close()


def _write_scaler(scaler_root: Path, scaler: FeatureMoments) -> None:
    scaler_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCALER_SCHEMA_VERSION,
        "feature_names": list(scaler.feature_names),
        "means": list(scaler.means),
        "standard_deviations": list(scaler.standard_deviations),
        "training_row_count": scaler.training_row_count,
    }
    (scaler_root / "ciciot2023_scaler.json").write_text(
        _stable_json(payload),
        encoding="utf-8",
    )


def _view_key(
    pseudo_domain: CICIoT2023PseudoDomain,
    canonical_label: DatasetClassToken,
    role: Role,
) -> PreparedViewKey:
    return f"{pseudo_domain.display_token}_{canonical_label}_{ROLE_HASH_TOKEN[role]}"


def _pack_features(features: Sequence[float]) -> bytes:
    return struct.pack(f"!{len(features)}d", *features)


def _unpack_features(payload: bytes, feature_count: NonNegativeInt) -> tuple[float, ...]:
    return tuple(struct.unpack(f"!{feature_count}d", payload))


def _role_from_hash_token(token: RoleHashToken) -> Role:
    for role, role_token in ROLE_HASH_TOKEN.items():
        if role_token == token:
            return role
    raise ValueError(f"unknown role hash token: {token}")


def _arrow_modules() -> tuple[_ArrowModule, _ParquetModule]:
    return (
        cast(_ArrowModule, import_module("pyarrow")),
        cast(_ParquetModule, import_module("pyarrow.parquet")),
    )


def _stable_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2)
