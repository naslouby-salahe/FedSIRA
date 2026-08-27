from __future__ import annotations

import heapq
import json
import sqlite3
import struct
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import numpy
import pandas
import pyarrow as pa
import pyarrow.parquet as pq

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
    SecondaryRetainedRow,
    apply_secondary_sampling_cap,
    parse_complete_case_rows,
    sampling_cap_for_secondary_role,
)
from fedsira.datasets.ciciot2023.schema import (
    PSEUDO_DOMAIN_COUNT,
    ROW_IDENTIFIER_CANONICAL_TOKENS,
    TARGET_LABEL,
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
READ_CHUNK_ROWS = 100_000
WRITE_BATCH_ROWS = 25_000


@dataclass(frozen=True)
class SecondaryPreparedViewSummary:
    pseudo_domain: NonNegativeInt
    canonical_label: CanonicalToken
    role: Role
    row_count: NonNegativeInt
    parquet_path: Path


@dataclass(frozen=True)
class SecondaryMaterializationSummary:
    dataset_manifest_hash: ArtifactDigest
    class_registry: tuple[CanonicalToken, ...]
    predictor_columns: tuple[CanonicalToken, ...]
    raw_row_count: NonNegativeInt
    retained_row_count: NonNegativeInt
    excluded_row_count: NonNegativeInt
    views: tuple[SecondaryPreparedViewSummary, ...]
    scaler: FeatureMoments


@dataclass(frozen=True)
class _GroupIdentity:
    canonical_label: CanonicalToken
    pseudo_domain: NonNegativeInt


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
                    row.pseudo_domain,
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
        return tuple(_GroupIdentity(str(label), int(domain)) for label, domain in cursor)

    def group_stable_ids(self, group: _GroupIdentity) -> Iterator[ArtifactDigest]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id
            FROM retained
            WHERE canonical_label = ? AND pseudo_domain = ?
            ORDER BY stable_row_id
            """,
            (group.canonical_label, group.pseudo_domain),
        )
        for (stable_row_id,) in cursor:
            yield str(stable_row_id)

    def add_role_assignments(
        self,
        group: _GroupIdentity,
        role: Role,
        stable_row_ids: Sequence[ArtifactDigest],
    ) -> None:
        self._connection.executemany(
            """
            INSERT INTO role_assignments(stable_row_id, canonical_label, pseudo_domain, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                (stable_row_id, group.canonical_label, group.pseudo_domain, ROLE_HASH_TOKEN[role])
                for stable_row_id in stable_row_ids
            ),
        )
        self._connection.commit()

    def counts(self) -> tuple[NonNegativeInt, NonNegativeInt]:
        retained = int(self._connection.execute("SELECT COUNT(*) FROM retained").fetchone()[0])
        excluded = int(self._connection.execute("SELECT COUNT(*) FROM exclusions").fetchone()[0])
        return retained, excluded

    def assigned_views(self) -> tuple[tuple[NonNegativeInt, CanonicalToken, Role, NonNegativeInt], ...]:
        cursor = self._connection.execute(
            """
            SELECT pseudo_domain, canonical_label, role, COUNT(*)
            FROM role_assignments
            GROUP BY pseudo_domain, canonical_label, role
            ORDER BY pseudo_domain, canonical_label, role
            """
        )
        return tuple(
            (int(domain), str(label), _role_from_hash_token(str(role_token)), int(count))
            for domain, label, role_token, count in cursor
        )

    def iter_view_rows(
        self,
        pseudo_domain: NonNegativeInt,
        canonical_label: CanonicalToken,
        role: Role,
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
            (pseudo_domain, canonical_label, ROLE_HASH_TOKEN[role]),
        )
        for stable_row_id, features in cursor:
            yield str(stable_row_id), bytes(features)

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
        for (features,) in cursor:
            yield bytes(features)

    def iter_exclusions(self) -> Iterator[tuple[str, str, str, int, str]]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id, file_sha256, relative_path, original_row_index, reason
            FROM exclusions
            ORDER BY relative_path, original_row_index
            """
        )
        for row in cursor:
            yield str(row[0]), str(row[1]), str(row[2]), int(row[3]), str(row[4])

    def iter_role_manifest(self) -> Iterator[tuple[str, str, int, str]]:
        cursor = self._connection.execute(
            """
            SELECT stable_row_id, canonical_label, pseudo_domain, role
            FROM role_assignments
            ORDER BY canonical_label, pseudo_domain, stable_row_id
            """
        )
        for row in cursor:
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
    label_column = resolve_label_column(reference_header)
    for item in discovered[1:]:
        validate_consistent_header(reference_header, read_csv_header(item.absolute_path))

    predictor_columns = _resolve_predictors_for_all_shards(discovered, reference_header, label_column)
    database_path = cache_root / "ciciot2023_preparation.sqlite3"
    if overwrite and database_path.exists():
        database_path.unlink()
    store = _SecondaryPreparationStore(database_path)
    store.reset()
    raw_labels: set[CanonicalToken] = set()
    raw_row_count = 0
    try:
        for item in discovered:
            for chunk in pandas.read_csv(item.absolute_path, chunksize=READ_CHUNK_ROWS):
                chunk = chunk.reset_index(drop=True)
                chunk_start = raw_row_count_for_file = raw_row_count
                raw_row_count += len(chunk)
                raw_labels.update(str(value) for value in chunk[label_column].unique())
                retained, exclusions = _parse_chunk_with_physical_indices(
                    chunk,
                    relative_path=item.relative_path,
                    file_sha256=item.file_sha256,
                    file_row_offset=_file_row_offset(item, chunk_start, raw_row_count_for_file),
                    label_column=label_column,
                    predictor_columns=predictor_columns,
                    dataset_manifest_hash=dataset_manifest_hash,
                    pseudo_domain_partition_salt=config.datasets.secondary.pseudo_domain_partition_salt,
                )
                store.add_rows(retained, exclusions)

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
            raw_row_count=raw_row_count,
            retained_row_count=retained_count,
            excluded_row_count=excluded_count,
            views=views,
            scaler=scaler,
        )
    finally:
        store.close()


def _resolve_predictors_for_all_shards(
    discovered: Sequence[SecondaryCsvFile],
    header: tuple[CanonicalToken, ...],
    label_column: CanonicalToken,
) -> tuple[CanonicalToken, ...]:
    candidate_predictors = tuple(column for column in header if column != label_column)
    excluded_identifiers: set[CanonicalToken] = set()
    for column in candidate_predictors:
        if canonicalize_token(column) not in ROW_IDENTIFIER_CANONICAL_TOKENS:
            continue
        if all(_is_physical_row_identifier(item.absolute_path, column) for item in discovered):
            excluded_identifiers.add(column)
    predictors = tuple(column for column in candidate_predictors if column not in excluded_identifiers)
    if not predictors:
        raise ValueError("CICIoT2023 resolved no predictor columns")
    if len(set(predictors)) != len(predictors):
        raise ValueError("CICIoT2023 predictor names must be unique after header trimming")
    return predictors


def _is_physical_row_identifier(path: Path, column: CanonicalToken) -> bool:
    mode: NonNegativeInt | None = None
    offset = 0
    for chunk in pandas.read_csv(path, usecols=[column], chunksize=READ_CHUNK_ROWS):
        numeric = pandas.to_numeric(chunk[column], errors="coerce")
        if numeric.isna().any():
            return False
        values = numeric.to_numpy(dtype=float)
        if not numpy.equal(values, numpy.floor(values)).all():
            return False
        integer_values = values.astype(numpy.int64)
        if mode is None:
            zero_based = numpy.arange(offset, offset + len(chunk), dtype=numpy.int64)
            one_based = zero_based + 1
            if numpy.array_equal(integer_values, zero_based):
                mode = 0
            elif numpy.array_equal(integer_values, one_based):
                mode = 1
            else:
                return False
        else:
            expected = numpy.arange(offset + mode, offset + mode + len(chunk), dtype=numpy.int64)
            if not numpy.array_equal(integer_values, expected):
                return False
        offset += len(chunk)
    return offset > 0


def _parse_chunk_with_physical_indices(
    chunk: pandas.DataFrame,
    *,
    relative_path: CanonicalToken,
    file_sha256: ArtifactDigest,
    file_row_offset: NonNegativeInt,
    label_column: CanonicalToken,
    predictor_columns: tuple[CanonicalToken, ...],
    dataset_manifest_hash: ArtifactDigest,
    pseudo_domain_partition_salt: int,
) -> tuple[tuple[SecondaryRetainedRow, ...], tuple[SecondaryExcludedRow, ...]]:
    chunk.index = pandas.RangeIndex(file_row_offset, file_row_offset + len(chunk))
    return parse_complete_case_rows(
        chunk,
        relative_path=relative_path,
        file_sha256=file_sha256,
        label_column=label_column,
        predictor_columns=predictor_columns,
        dataset_manifest_hash=dataset_manifest_hash,
        pseudo_domain_partition_salt=pseudo_domain_partition_salt,
    )


def _file_row_offset(
    item: SecondaryCsvFile,
    global_chunk_start: NonNegativeInt,
    _global_rows_before_chunk: NonNegativeInt,
) -> NonNegativeInt:
    del item, global_chunk_start, _global_rows_before_chunk
    return 0


def _assign_roles(
    store: _SecondaryPreparationStore,
    config: ScientificConfig,
    dataset_manifest_hash: ArtifactDigest,
) -> None:
    for group in store.groups():
        stable_row_ids = tuple(store.group_stable_ids(group))
        windows = (
            target_role_windows(config.datasets.primary.role_intervals)
            if group.canonical_label == TARGET_LABEL
            else supported_role_windows(config.datasets.primary.role_intervals)
        )
        group_size = len(stable_row_ids)
        ids_by_role: dict[Role, list[ArtifactDigest]] = {}
        for group_index, stable_row_id in enumerate(stable_row_ids):
            role = role_for_normalized_position(group_index / group_size, windows)
            if role is not None:
                ids_by_role.setdefault(role, []).append(stable_row_id)
        for role, candidate_ids in ids_by_role.items():
            cap = sampling_cap_for_secondary_role(
                config.datasets.primary.sampling_caps_per_domain,
                group.canonical_label,
                role,
            )
            selected_ids = apply_secondary_sampling_cap(
                dataset_manifest_hash,
                group.canonical_label,
                group.pseudo_domain,
                role,
                tuple(candidate_ids),
                cap,
            )
            store.add_role_assignments(group, role, selected_ids)


def _fit_secondary_scaler(
    store: _SecondaryPreparationStore,
    predictor_columns: tuple[CanonicalToken, ...],
    config: ScientificConfig,
) -> FeatureMoments:
    statistics = None
    batch: list[tuple[float, ...]] = []
    for packed_features in store.iter_anchor_train_features():
        batch.append(_unpack_features(packed_features, len(predictor_columns)))
        if len(batch) >= WRITE_BATCH_ROWS:
            statistics = accumulate_feature_statistics(predictor_columns, batch, statistics)
            batch.clear()
    if batch:
        statistics = accumulate_feature_statistics(predictor_columns, batch, statistics)
    if statistics is None:
        raise ValueError("CICIoT2023 has no supported Anchor Train rows for scaler fitting")
    return fit_feature_moments(predictor_columns, statistics, config.datasets.primary.scaling)


def _write_prepared_views(
    store: _SecondaryPreparationStore,
    predictor_columns: tuple[CanonicalToken, ...],
    scaler: FeatureMoments,
    config: ScientificConfig,
    prepared_root: Path,
) -> tuple[SecondaryPreparedViewSummary, ...]:
    prepared_root.mkdir(parents=True, exist_ok=True)
    summaries: list[SecondaryPreparedViewSummary] = []
    for pseudo_domain, label, role, row_count in store.assigned_views():
        view_key = _view_key(pseudo_domain, label, role)
        parquet_path = prepared_root / f"{view_key}.parquet"
        writer: pq.ParquetWriter | None = None
        try:
            rows: list[dict[str, str | float]] = []
            for stable_row_id, packed_features in store.iter_view_rows(pseudo_domain, label, role):
                standardized = standardize_row(
                    _unpack_features(packed_features, len(predictor_columns)),
                    scaler,
                    config.datasets.primary.scaling,
                )
                row: dict[str, str | float] = {"sample_id": stable_row_id, "label": label}
                row.update(zip(predictor_columns, standardized, strict=True))
                rows.append(row)
                if len(rows) >= WRITE_BATCH_ROWS:
                    writer = _append_parquet_rows(parquet_path, rows, writer)
                    rows.clear()
            if rows:
                writer = _append_parquet_rows(parquet_path, rows, writer)
        finally:
            if writer is not None:
                writer.close()
        payload = {
            "schema_version": PREPARED_VIEW_SCHEMA_VERSION,
            "pseudo_domain": pseudo_domain + 1,
            "canonical_label": label,
            "role": role.value,
            "row_count": row_count,
        }
        (prepared_root / f"{view_key}.json").write_text(_stable_json(payload), encoding="utf-8")
        summaries.append(
            SecondaryPreparedViewSummary(
                pseudo_domain=pseudo_domain,
                canonical_label=label,
                role=role,
                row_count=row_count,
                parquet_path=parquet_path,
            )
        )
    return tuple(summaries)


def _append_parquet_rows(
    path: Path,
    rows: Sequence[Mapping[str, str | float]],
    writer: pq.ParquetWriter | None,
) -> pq.ParquetWriter:
    table = pa.Table.from_pylist(list(rows))
    active_writer = writer or pq.ParquetWriter(path, table.schema)
    active_writer.write_table(table)
    return active_writer


def _write_exclusions(store: _SecondaryPreparationStore, path: Path) -> None:
    schema = pa.schema(
        [
            ("schema_version", pa.string()),
            ("stable_row_id", pa.string()),
            ("file_sha256", pa.string()),
            ("relative_path", pa.string()),
            ("original_row_index", pa.int64()),
            ("reason", pa.string()),
        ]
    )
    _write_tuple_rows(
        path,
        schema,
        (
            (EXCLUSION_SCHEMA_VERSION, stable_id, file_hash, relative_path, row_index, reason)
            for stable_id, file_hash, relative_path, row_index, reason in store.iter_exclusions()
        ),
    )


def _write_role_manifest(store: _SecondaryPreparationStore, path: Path) -> None:
    schema = pa.schema(
        [
            ("schema_version", pa.string()),
            ("stable_row_id", pa.string()),
            ("canonical_label", pa.string()),
            ("pseudo_domain", pa.int64()),
            ("role", pa.string()),
        ]
    )
    _write_tuple_rows(
        path,
        schema,
        (
            (ROLE_MANIFEST_SCHEMA_VERSION, stable_id, label, pseudo_domain + 1, role_token)
            for stable_id, label, pseudo_domain, role_token in store.iter_role_manifest()
        ),
    )


def _write_tuple_rows(path: Path, schema: pa.Schema, rows: Iterator[tuple[object, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    batch: list[tuple[object, ...]] = []
    try:
        for row in rows:
            batch.append(row)
            if len(batch) >= WRITE_BATCH_ROWS:
                table = pa.Table.from_pylist(
                    [dict(zip(schema.names, values, strict=True)) for values in batch], schema=schema
                )
                writer = writer or pq.ParquetWriter(path, schema)
                writer.write_table(table)
                batch.clear()
        if batch or writer is None:
            table = pa.Table.from_pylist(
                [dict(zip(schema.names, values, strict=True)) for values in batch], schema=schema
            )
            writer = writer or pq.ParquetWriter(path, schema)
            writer.write_table(table)
    finally:
        if writer is not None:
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
    (scaler_root / "ciciot2023_scaler.json").write_text(_stable_json(payload), encoding="utf-8")


def _view_key(
    pseudo_domain: NonNegativeInt,
    canonical_label: CanonicalToken,
    role: Role,
) -> CanonicalToken:
    return f"PSEUDO_DOMAIN_{pseudo_domain + 1}_{canonical_label}_{ROLE_HASH_TOKEN[role]}"


def _pack_features(features: Sequence[float]) -> bytes:
    return struct.pack(f"!{len(features)}d", *features)


def _unpack_features(payload: bytes, feature_count: NonNegativeInt) -> tuple[float, ...]:
    return tuple(struct.unpack(f"!{feature_count}d", payload))


def _role_from_hash_token(token: CanonicalToken) -> Role:
    for role, role_token in ROLE_HASH_TOKEN.items():
        if role_token == token:
            return role
    raise ValueError(f"unknown role hash token: {token}")


def _stable_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2)
