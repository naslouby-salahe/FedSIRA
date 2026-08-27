from __future__ import annotations

import csv
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

from fedsira.config.schema import ScientificConfig
from fedsira.datasets.ciciot2023.acquisition import (
    SecondaryCsvFile,
    compute_dataset_manifest_hash,
    read_csv_header,
    resolve_label_column,
    validate_consistent_header,
)
from fedsira.datasets.ciciot2023.preprocessing import (
    SecondaryExcludedRow,
    SecondaryRawRow,
    SecondaryRetainedRow,
    parse_complete_case_rows,
    sampling_cap_for_secondary_role,
    secondary_sampling_selection_key,
)
from fedsira.datasets.ciciot2023.schema import (
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    ROW_IDENTIFIER_CANONICAL_TOKENS,
    TARGET_LABEL,
    CICIoT2023PseudoDomain,
    canonical_class_registry,
    canonicalize_label,
    canonicalize_token,
)
from fedsira.datasets.ciciot2023.validation import (
    validate_label_collisions,
    validate_target_label_present,
)
from fedsira.datasets.common import ROLE_HASH_TOKEN, Role, role_for_normalized_position
from fedsira.datasets.roles import supported_role_windows, target_role_windows
from fedsira.datasets.scaling import (
    FeatureMoments,
    accumulate_feature_statistics,
    fit_feature_moments,
    standardize_row,
)
from fedsira.domain.records import ArtifactDigest, CanonicalToken, NonNegativeInt

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


class _ParquetModule(Protocol):
    def ParquetWriter(self, where: str, schema: object) -> _ParquetWriter: ...


@dataclass(frozen=True)
class SecondaryPreparedViewSummary:
    pseudo_domain: CICIoT2023PseudoDomain
    canonical_label: CanonicalToken
    role: Role
    row_count: NonNegativeInt
    parquet_path: Path


@dataclass(frozen=True)
class SecondaryMaterializationSummary:
    dataset_manifest_hash: ArtifactDigest
    class_registry: tuple[CanonicalToken, ...]
    predictor_columns: tuple[CanonicalToken, ...]
    predictor_count_matches_official: bool
    raw_row_count: NonNegativeInt
    retained_row_count: NonNegativeInt
    excluded_row_count: NonNegativeInt
    views: tuple[SecondaryPreparedViewSummary, ...]
    scaler: FeatureMoments


@dataclass(frozen=True)
class _GroupIdentity:
    canonical_label: CanonicalToken
    pseudo_domain: CICIoT2023PseudoDomain


@dataclass(frozen=True)
class _PreparedViewIdentity:
    pseudo_domain: CICIoT2023PseudoDomain
    canonical_label: CanonicalToken
    role: Role
    row_count: NonNegativeInt


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
                    canonical_label=str(row[0]),
                    pseudo_domain=CICIoT2023PseudoDomain(int(row[1])),
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
        return int(row[0])

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
            yield str(row[0])

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
        retained = int(cast(tuple[object], retained_row)[0])
        excluded = int(cast(tuple[object], excluded_row)[0])
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
                    pseudo_domain=CICIoT2023PseudoDomain(int(row[0])),
                    canonical_label=str(row[1]),
                    role=_role_from_hash_token(str(row[2])),
                    row_count=int(row[3]),
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
            yield str(row[0]), feature_blob

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
            yield str(row[0]), str(row[1]), str(row[2]), int(row[3]), str(row[4])

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
            yield str(row[0]), str(row[1]), int(row[2]), str(row[3])

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
    predictor_columns = tuple(
        column
        for column in reference_header
        if column != label_column and column not in row_identifier_columns
    )
    if not predictor_columns:
        raise ValueError("CICIoT2023 resolved no predictor columns")

    database_path = cache_root / "ciciot2023_preparation.sqlite3"
    if overwrite and database_path.exists():
        database_path.unlink()
    store = _SecondaryPreparationStore(database_path)
    store.reset()
    raw_labels: set[CanonicalToken] = set()
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
        canonical_labels = frozenset(canonicalize_label(label) for label in raw_labels)
        validate_target_label_present(canonical_labels)
        class_registry = canonical_class_registry(canonical_labels)

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
    header: tuple[CanonicalToken, ...],
    label_column: CanonicalToken,
    predictor_columns: tuple[CanonicalToken, ...],
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
    header: tuple[CanonicalToken, ...],
    label_column: CanonicalToken,
) -> frozenset[CanonicalToken]:
    identifiers: set[CanonicalToken] = set()
    for column_index, column in enumerate(header):
        if column == label_column:
            continue
        if canonicalize_token(column) not in ROW_IDENTIFIER_CANONICAL_TOKENS:
            continue
        if all(
            _is_physical_row_identifier(item.absolute_path, column_index)
            for item in discovered
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
            role = role_for_normalized_position(group_index / group_size, windows)
            if role is None:
                continue
            cap = sampling_cap_for_secondary_role(caps, group.canonical_label, role)
            if cap is None:
                batch = uncapped_batches.setdefault(role, [])
                batch.append(stable_row_id)
                if len(batch) >= WRITE_BATCH_ROWS:
                    store.add_role_assignments(group, role, batch)
                    batch.clear()
                continue
            if cap == 0:
                continue
            rank_digest, ranked_stable_id = secondary_sampling_selection_key(
                dataset_manifest_hash,
                group.canonical_label,
                group.pseudo_domain,
                role,
                stable_row_id,
            )
            candidate = (
                -int.from_bytes(rank_digest, byteorder="big"),
                -int(ranked_stable_id, 16),
                stable_row_id,
            )
            heap = capped_heaps.setdefault(role, [])
            if len(heap) < cap:
                heapq.heappush(heap, candidate)
            elif candidate > heap[0]:
                heapq.heapreplace(heap, candidate)

        for role, batch in uncapped_batches.items():
            store.add_role_assignments(group, role, batch)
        for role, heap in capped_heaps.items():
            selected_ids = tuple(
                sorted(
                    (entry[2] for entry in heap),
                    key=lambda stable_row_id: secondary_sampling_selection_key(
                        dataset_manifest_hash,
                        group.canonical_label,
                        group.pseudo_domain,
                        role,
                        stable_row_id,
                    ),
                )
            )
            store.add_role_assignments(group, role, selected_ids)


def _fit_secondary_scaler(
    store: _SecondaryPreparationStore,
    predictor_columns: tuple[CanonicalToken, ...],
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
    predictor_columns: tuple[CanonicalToken, ...],
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
    predictor_columns: tuple[CanonicalToken, ...],
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
    canonical_label: CanonicalToken,
    role: Role,
) -> CanonicalToken:
    return f"{pseudo_domain.display_token}_{canonical_label}_{ROLE_HASH_TOKEN[role]}"


def _pack_features(features: Sequence[float]) -> bytes:
    return struct.pack(f"!{len(features)}d", *features)


def _unpack_features(payload: bytes, feature_count: NonNegativeInt) -> tuple[float, ...]:
    return tuple(struct.unpack(f"!{feature_count}d", payload))


def _role_from_hash_token(token: CanonicalToken) -> Role:
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
