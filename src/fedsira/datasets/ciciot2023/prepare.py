from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import duckdb

from fedsira.config import SamplingCapsPerDomain
from fedsira.datasets.ciciot2023.schema import (
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    TARGET_LABEL,
    CICIoT2023PseudoDomain,
    CICIoTRowIdentifierToken,
    CICIoTSpecialLabel,
    build_class_registry,
    hash_to_pseudo_domain,
    normalize_label,
    normalize_label_token,
)
from fedsira.datasets.common import (
    PREPROCESSING_SAMPLE_ORDER_SEED,
    SUPPORTED_ROLE_ORDER,
    TARGET_ROLE_ORDER,
    DatasetExclusionReason,
    FeatureMoments,
    Role,
    ScalerMetadata,
    compute_file_checksum,
    compute_sample_id,
    copy_query_to_parquet,
    fetch_feature_statistics,
    fit_feature_moments,
    open_tabular_engine,
    read_csv_relation,
    role_case_sql,
    role_from_hash_token,
    role_hash_token,
    sampling_cap_for_role,
    sql_ident,
    sql_string,
    standardized_feature_sql,
    supported_role_windows,
    target_role_windows,
    view_parquet_path,
    write_json_payload,
)
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    ClassLabel,
    DatasetClassToken,
    DatasetColumnName,
    DatasetFileDigest,
    DatasetManifestDigest,
    FramingField,
    FrozenDomainModel,
    OverwriteExisting,
    PartitionSalt,
    PredictorCountMatchesOfficial,
    PreparedViewKey,
    RelativePathText,
    RoleToken,
    RowCount,
    SampleIdPrefix,
    SamplingSelectionDigest,
    SchemaVersion,
    SeedDerivationLabel,
    SourceRowIndex,
    TextValue,
)
from fedsira.runtime import current_application_context, framed_bytes

_ASCII_HEADER_WHITESPACE = " \t\r\n\f\v"
DATASET_MANIFEST_SEPARATOR: SeedDerivationLabel = "CICIOT2023_DATASET_MANIFEST_V1"
STABLE_ROW_ID_PREFIX: SampleIdPrefix = "CICIOT2023_SAMPLE_ID_V1"
PREPARED_VIEW_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_prepared_view|1"
SCALER_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_scaler|1"
ROLE_MANIFEST_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_role_manifest|1"
EXCLUSION_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_exclusions|1"
_WHITESPACE_HYPHEN_UNDERSCORE = re.compile(r"[\s\-_]+")


class SecondaryCsvFile(FrozenDomainModel):
    absolute_path: Path
    relative_path: RelativePathText
    file_sha256: DatasetFileDigest


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


class SecondaryRoleAssignment(FrozenDomainModel):
    stable_row_id: ArtifactDigest
    normalized_label: DatasetClassToken
    pseudo_domain: CICIoT2023PseudoDomain
    role: Role


class _PreparedViewMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    pseudo_domain: CICIoT2023PseudoDomain
    normalized_label: DatasetClassToken
    role: Role
    row_count: RowCount


def compute_stable_row_id(
    normalized_relative_csv_path: RelativePathText,
    file_sha256: ArtifactDigest,
    zero_based_original_row_index: SourceRowIndex,
) -> ArtifactDigest:
    return compute_sample_id(
        STABLE_ROW_ID_PREFIX,
        normalized_relative_csv_path,
        file_sha256,
        zero_based_original_row_index,
    )


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


def discover_secondary_csv_files(csv_root: Path) -> tuple[SecondaryCsvFile, ...]:
    paths = sorted(csv_root.rglob("*.csv"), key=lambda path: path.relative_to(csv_root).as_posix())
    if not paths:
        raise ValueError(f"no CICIoT2023 CSV shards found beneath {csv_root}")
    return tuple(
        SecondaryCsvFile(
            absolute_path=path,
            relative_path=path.relative_to(csv_root).as_posix(),
            file_sha256=compute_file_checksum(path),
        )
        for path in paths
    )


def compute_dataset_manifest_hash(
    discovered: tuple[SecondaryCsvFile, ...],
) -> DatasetManifestDigest:
    if not discovered:
        raise ValueError("secondary dataset manifest requires at least one CSV shard")
    fields: list[FramingField] = []
    for item in sorted(discovered, key=lambda discovered_file: discovered_file.relative_path):
        fields.extend((item.relative_path, item.file_sha256))
    return hashlib.sha256(framed_bytes(DATASET_MANIFEST_SEPARATOR, *fields)).hexdigest()


def read_csv_header(path: Path) -> tuple[DatasetColumnName, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            raw_header = next(reader)
        except StopIteration as error:
            raise ValueError(f"CICIoT2023 CSV shard is empty: {path}") from error
    return tuple(name.strip(_ASCII_HEADER_WHITESPACE) for name in raw_header)


def resolve_label_column(header: tuple[DatasetColumnName, ...]) -> DatasetColumnName:
    label_columns = tuple(column for column in header if normalize_label_token(column) == "LABEL")
    if len(label_columns) != 1:
        raise ValueError(
            "expected exactly one column named 'label' (case-insensitive), "
            f"found {len(label_columns)}: {label_columns}"
        )
    return label_columns[0]


def validate_consistent_header(
    reference_header: tuple[DatasetColumnName, ...],
    observed_header: tuple[DatasetColumnName, ...],
) -> None:
    if observed_header != reference_header:
        raise ValueError("secondary CSV header does not match the fixed reference schema")


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


def _is_row_identifier_name(column: DatasetColumnName) -> BooleanValue:
    try:
        CICIoTRowIdentifierToken[normalize_label_token(column)]
    except KeyError:
        return False
    return True


def _is_physical_row_identifier(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    header: tuple[DatasetColumnName, ...],
    column: DatasetColumnName,
) -> BooleanValue:
    query = (
        "WITH numbered AS ("
        f"SELECT try_cast({sql_ident(column)} AS DOUBLE) AS v, "
        "row_number() OVER () - 1 AS i "
        f"FROM {read_csv_relation(path, header)}"
        "), stats AS (SELECT min(v) AS base, count(*) AS n FROM numbered) "
        "SELECT (SELECT n FROM stats) > 0 AND (SELECT base FROM stats) IN (0, 1) "
        "AND bool_and("
        "v IS NOT NULL AND isfinite(v) AND v = round(v) AND v = i + (SELECT base FROM stats)) "
        "FROM numbered"
    )
    row = connection.execute(query).fetchone()
    return bool(row is not None and row[0])


def resolve_row_identifier_columns(
    discovered: tuple[SecondaryCsvFile, ...],
    header: tuple[DatasetColumnName, ...],
    label_column: DatasetColumnName,
) -> frozenset[DatasetColumnName]:
    connection = open_tabular_engine()
    try:
        identifiers: list[DatasetColumnName] = []
        for column in header:
            if column == label_column or not _is_row_identifier_name(column):
                continue
            if all(
                _is_physical_row_identifier(connection, item.absolute_path, header, column)
                for item in discovered
            ):
                identifiers.append(column)
        return frozenset(identifiers)
    finally:
        connection.close()


def _comparison_token(value: ClassLabel) -> ClassLabel:
    return _WHITESPACE_HYPHEN_UNDERSCORE.sub("", value).lower()


def validate_label_collisions(raw_labels: frozenset[ClassLabel]) -> None:
    ordered = tuple(sorted(raw_labels))
    for first_index, first in enumerate(ordered):
        for second in ordered[first_index + 1 :]:
            normalized = normalize_label(first)
            if normalize_label(second) != normalized:
                continue
            if _comparison_token(first) != _comparison_token(second):
                raise ValueError(
                    f"raw labels {first!r} and {second!r} collide on normalized label "
                    f"{normalized!r} but differ by more than case/whitespace/hyphen/underscore"
                )


def validate_target_label_present(normalized_labels: frozenset[ClassLabel]) -> None:
    if TARGET_LABEL not in normalized_labels:
        raise ValueError(
            f"required target label {TARGET_LABEL} was not observed after normalization"
        )


def _ciciot_stable_row_id(
    relative_path: RelativePathText,
    file_sha256: ArtifactDigest,
    original_row_index: SourceRowIndex,
) -> ArtifactDigest:
    return compute_stable_row_id(relative_path, file_sha256, original_row_index)


def _ciciot_normalized_label(raw_label: ClassLabel) -> ClassLabel:
    return normalize_label(raw_label)


def _ciciot_pseudo_domain(
    label: ClassLabel,
    row_id: ArtifactDigest,
    dataset_manifest_hash: DatasetManifestDigest,
    partition_salt: PartitionSalt,
) -> CICIoT2023PseudoDomain:
    return hash_to_pseudo_domain(dataset_manifest_hash, label, row_id, partition_salt)


def _ciciot_sampling_digest(
    label: DatasetClassToken,
    domain_index: CICIoT2023PseudoDomain,
    role_token: RoleToken,
    row_id: ArtifactDigest,
    dataset_manifest_hash: DatasetManifestDigest,
) -> SamplingSelectionDigest:
    digest, _ranked = secondary_sampling_selection_key(
        dataset_manifest_hash,
        label,
        CICIoT2023PseudoDomain(domain_index),
        role_from_hash_token(role_token),
        row_id,
    )
    return digest


def _register_ciciot_functions(connection: duckdb.DuckDBPyConnection) -> None:
    connection.create_function("ciciot_stable_row_id", _ciciot_stable_row_id, return_type="VARCHAR")
    connection.create_function(
        "ciciot_normalized_label", _ciciot_normalized_label, return_type="VARCHAR"
    )
    connection.create_function("ciciot_pseudo_domain", _ciciot_pseudo_domain, return_type="INTEGER")
    connection.create_function(
        "ciciot_sampling_digest", _ciciot_sampling_digest, return_type="BLOB"
    )


def _create_preparation_tables(
    connection: duckdb.DuckDBPyConnection,
    predictor_columns: tuple[DatasetColumnName, ...],
) -> None:
    feature_schema = ", ".join(f"{sql_ident(name)} DOUBLE" for name in predictor_columns)
    connection.execute(
        "CREATE TABLE retained ("
        "stable_row_id VARCHAR PRIMARY KEY, file_sha256 VARCHAR, relative_path VARCHAR, "
        "original_row_index BIGINT, normalized_label VARCHAR, pseudo_domain INTEGER, "
        f"{feature_schema})"
    )
    connection.execute(
        "CREATE TABLE exclusions ("
        "stable_row_id VARCHAR PRIMARY KEY, file_sha256 VARCHAR, relative_path VARCHAR, "
        "original_row_index BIGINT, reason VARCHAR)"
    )
    connection.execute(
        "CREATE TABLE role_assignments ("
        "stable_row_id VARCHAR PRIMARY KEY, normalized_label VARCHAR, "
        "pseudo_domain INTEGER, role VARCHAR)"
    )


def _exclusion_reason_sql(predictor_columns: tuple[DatasetColumnName, ...]) -> TextValue:
    unparseable = " OR ".join(
        f"try_cast({sql_ident(name)} AS DOUBLE) IS NULL" for name in predictor_columns
    )
    nonfinite = " OR ".join(
        f"NOT isfinite(try_cast({sql_ident(name)} AS DOUBLE))" for name in predictor_columns
    )
    return (
        "CASE "
        f"WHEN {unparseable} THEN {sql_string(DatasetExclusionReason.UNPARSEABLE_PREDICTOR)} "
        f"WHEN {nonfinite} THEN {sql_string(DatasetExclusionReason.NON_FINITE_PREDICTOR)} "
        "END"
    )


def _ingest_shard(
    connection: duckdb.DuckDBPyConnection,
    item: SecondaryCsvFile,
    header: tuple[DatasetColumnName, ...],
    label_column: DatasetColumnName,
    predictor_columns: tuple[DatasetColumnName, ...],
    dataset_manifest_hash: DatasetManifestDigest,
    partition_salt: PartitionSalt,
) -> tuple[RowCount, tuple[ClassLabel, ...]]:
    print(f"CICIoT2023 ingest: file={item.relative_path}")
    try:
        connection.execute(
            "CREATE OR REPLACE TABLE shard AS "
            "SELECT (row_number() OVER () - 1) AS original_row_index, * "
            f"FROM {read_csv_relation(item.absolute_path, header)}"
        )
    except duckdb.Error as error:
        raise ValueError(
            f"CICIoT2023 row width does not match validated header: file={item.relative_path}"
        ) from error
    count_row = connection.execute("SELECT count(*) FROM shard").fetchone()
    if count_row is None:
        raise ValueError(f"CICIoT2023 shard count query failed: {item.relative_path}")
    raw_count = count_row[0]
    if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count < 0:
        raise TypeError("CICIoT2023 shard row count must be a non-negative integer")
    reason_sql = _exclusion_reason_sql(predictor_columns)
    connection.execute(
        "CREATE OR REPLACE TABLE classified AS "
        "SELECT original_row_index, "
        f"{sql_ident(label_column)} AS raw_label, "
        f"{reason_sql} AS reason, "
        + ", ".join(
            f"try_cast({sql_ident(name)} AS DOUBLE) AS {sql_ident(name)}"
            for name in predictor_columns
        )
        + " FROM shard"
    )
    feature_insert = ", ".join(sql_ident(name) for name in predictor_columns)
    connection.execute(
        "INSERT INTO exclusions "
        "SELECT ciciot_stable_row_id(relative_path, file_sha256, original_row_index), "
        "file_sha256, relative_path, original_row_index, reason FROM ("
        f"SELECT {sql_string(item.relative_path)} AS relative_path, "
        f"{sql_string(item.file_sha256)} AS file_sha256, original_row_index, reason "
        "FROM classified WHERE reason IS NOT NULL)"
    )
    connection.execute(
        "INSERT INTO retained "
        "SELECT ciciot_stable_row_id(relative_path, file_sha256, original_row_index), "
        "file_sha256, relative_path, original_row_index, "
        "ciciot_normalized_label(raw_label), "
        "ciciot_pseudo_domain(ciciot_normalized_label(raw_label), "
        "ciciot_stable_row_id(relative_path, file_sha256, original_row_index), "
        f"{sql_string(dataset_manifest_hash)}, {partition_salt}), "
        f"{feature_insert} FROM ("
        f"SELECT {sql_string(item.relative_path)} AS relative_path, "
        f"{sql_string(item.file_sha256)} AS file_sha256, original_row_index, raw_label, "
        f"{feature_insert} FROM classified WHERE reason IS NULL)"
    )
    labels = tuple(
        str(row[0])
        for row in connection.execute("SELECT DISTINCT raw_label FROM classified").fetchall()
    )
    return raw_count, labels


def _cap_case_sql(caps: SamplingCapsPerDomain) -> TextValue:
    target = sql_string(CICIoTSpecialLabel.BACKDOOR_MALWARE)
    benign = sql_string(CICIoTSpecialLabel.BENIGN)
    clauses: list[TextValue] = []
    for role in TARGET_ROLE_ORDER:
        cap = sampling_cap_for_role(caps, role, is_target=True, is_benign=False)
        if cap is None:
            continue
        clauses.append(
            f"WHEN normalized_label = {target} AND role = {sql_string(role_hash_token(role))} "
            f"THEN {cap}"
        )
    for role in SUPPORTED_ROLE_ORDER:
        if role is Role.REPORT_TEST:
            clauses.append(
                f"WHEN normalized_label != {target} AND role = {sql_string(role_hash_token(role))} "
                f"AND normalized_label = {benign} THEN {caps.report_test_benign}"
            )
            other_cap = caps.report_test_other_supported_per_class
            clauses.append(
                f"WHEN normalized_label != {target} AND role = {sql_string(role_hash_token(role))} "
                f"AND normalized_label != {benign} THEN {other_cap}"
            )
            continue
        cap = sampling_cap_for_role(caps, role, is_target=False, is_benign=False)
        if cap is None:
            continue
        clauses.append(
            f"WHEN normalized_label != {target} AND role = {sql_string(role_hash_token(role))} "
            f"THEN {cap}"
        )
    return "CASE " + " ".join(clauses) + " END"


def assign_secondary_roles(
    database_path: Path,
    dataset_manifest_hash: DatasetManifestDigest,
) -> None:
    connection = open_tabular_engine(database_path)
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS role_assignments ("
            "stable_row_id VARCHAR PRIMARY KEY, normalized_label VARCHAR, "
            "pseudo_domain INTEGER, role VARCHAR)"
        )
        _assign_secondary_roles(connection, dataset_manifest_hash, True)
    finally:
        connection.close()


def _assign_secondary_roles(
    connection: duckdb.DuckDBPyConnection,
    dataset_manifest_hash: DatasetManifestDigest,
    register_functions: BooleanValue,
) -> None:
    config = current_application_context().scientific_config
    if register_functions:
        _register_ciciot_functions(connection)
    target = sql_string(CICIoTSpecialLabel.BACKDOOR_MALWARE)
    position_sql = "(group_index * 1.0) / group_size"
    target_role_sql = role_case_sql(
        position_sql, target_role_windows(config.datasets.primary.role_intervals)
    )
    supported_role_sql = role_case_sql(
        position_sql, supported_role_windows(config.datasets.primary.role_intervals)
    )
    cap_sql = _cap_case_sql(config.datasets.primary.sampling_caps_per_domain)
    connection.execute(
        "INSERT INTO role_assignments "
        "WITH ordered AS ("
        "SELECT stable_row_id, normalized_label, pseudo_domain, "
        "(row_number() OVER (PARTITION BY normalized_label, pseudo_domain "
        "ORDER BY stable_row_id) - 1) AS group_index, "
        "count(*) OVER (PARTITION BY normalized_label, pseudo_domain) AS group_size "
        "FROM retained"
        "), positioned AS ("
        "SELECT ordered.*, "
        f"CASE WHEN normalized_label = {target} THEN {target_role_sql} "
        f"ELSE {supported_role_sql} END AS role FROM ordered"
        "), eligible AS ("
        "SELECT * FROM positioned WHERE role IS NOT NULL"
        "), ranked AS ("
        "SELECT eligible.*, "
        f"{cap_sql} AS cap, "
        "ciciot_sampling_digest(normalized_label, pseudo_domain, role, stable_row_id, "
        f"{sql_string(dataset_manifest_hash)}) AS digest "
        "FROM eligible"
        ") SELECT stable_row_id, normalized_label, pseudo_domain, role FROM ranked "
        "QUALIFY cap IS NULL OR row_number() OVER ("
        "PARTITION BY normalized_label, pseudo_domain, role "
        "ORDER BY digest, stable_row_id) <= cap"
    )


def _write_secondary_views(
    connection: duckdb.DuckDBPyConnection,
    predictor_columns: tuple[DatasetColumnName, ...],
    moments: FeatureMoments,
    prepared_root: Path,
    overwrite: OverwriteExisting,
) -> tuple[SecondaryPreparedViewSummary, ...]:
    config = current_application_context().scientific_config
    prepared_root.mkdir(parents=True, exist_ok=True)
    standardized = ", ".join(
        standardized_feature_sql(
            name,
            moments.means[index],
            moments.standard_deviations[index],
            config.datasets.primary.scaling,
        )
        for index, name in enumerate(predictor_columns)
    )
    identities = connection.execute(
        "SELECT pseudo_domain, normalized_label, role, count(*) "
        "FROM role_assignments GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"
    ).fetchall()
    summaries: list[SecondaryPreparedViewSummary] = []
    for domain_index, label, role_token, row_count in identities:
        pseudo_domain = CICIoT2023PseudoDomain(int(domain_index))
        role = role_from_hash_token(str(role_token))
        view_key: PreparedViewKey = f"{pseudo_domain.display_token}_{label}_{role_hash_token(role)}"
        parquet_path = view_parquet_path(prepared_root, view_key)
        query = (
            "SELECT retained.stable_row_id AS sample_id, retained.normalized_label AS label, "
            f"{standardized} FROM role_assignments JOIN retained USING (stable_row_id) "
            f"WHERE role_assignments.pseudo_domain = {int(pseudo_domain)} "
            f"AND role_assignments.normalized_label = {sql_string(str(label))} "
            f"AND role_assignments.role = {sql_string(role_hash_token(role))} "
            "ORDER BY retained.stable_row_id"
        )
        if overwrite or not parquet_path.exists():
            copy_query_to_parquet(connection, query, parquet_path)
        write_json_payload(
            (prepared_root / view_key).with_suffix(".json"),
            _PreparedViewMetadata(
                schema_version=PREPARED_VIEW_SCHEMA_VERSION,
                pseudo_domain=pseudo_domain,
                normalized_label=str(label),
                role=role,
                row_count=int(row_count),
            ),
            overwrite,
        )
        print(f"CICIoT2023 view written: {view_key} rows={row_count}")
        summaries.append(
            SecondaryPreparedViewSummary(
                pseudo_domain=pseudo_domain,
                normalized_label=str(label),
                role=role,
                row_count=int(row_count),
                parquet_path=parquet_path,
            )
        )
    return tuple(summaries)


def materialize_ciciot2023_prepared_views(
    discovered: tuple[SecondaryCsvFile, ...],
    prepared_root: Path,
    scaler_root: Path,
    metadata_root: Path,
    cache_root: Path,
    overwrite: OverwriteExisting = False,
) -> SecondaryMaterializationSummary:
    if not discovered:
        raise ValueError("CICIoT2023 materialization requires discovered CSV shards")
    config = current_application_context().scientific_config
    dataset_manifest_hash = compute_dataset_manifest_hash(discovered)
    reference_header = read_csv_header(discovered[0].absolute_path)
    if len(set(reference_header)) != len(reference_header):
        raise ValueError("CICIoT2023 fixed header contains duplicate names")
    label_column = resolve_label_column(reference_header)
    for item in discovered[1:]:
        validate_consistent_header(reference_header, read_csv_header(item.absolute_path))
    row_identifier_columns = resolve_row_identifier_columns(
        discovered, reference_header, label_column
    )
    predictor_columns = resolve_predictor_columns(
        reference_header, label_column, row_identifier_columns
    )
    cache_root.mkdir(parents=True, exist_ok=True)
    database_path = cache_root / "ciciot2023_preparation.duckdb"
    if overwrite and database_path.exists():
        database_path.unlink()
    connection = open_tabular_engine(database_path)
    raw_row_count: RowCount = 0
    try:
        _register_ciciot_functions(connection)
        _create_preparation_tables(connection, predictor_columns)
        observed_raw: list[ClassLabel] = []
        for item in discovered:
            shard_rows, shard_labels = _ingest_shard(
                connection,
                item,
                reference_header,
                label_column,
                predictor_columns,
                dataset_manifest_hash,
                config.datasets.secondary.pseudo_domain_partition_salt,
            )
            raw_row_count += shard_rows
            observed_raw.extend(shard_labels)
        validate_label_collisions(frozenset(observed_raw))
        normalized_labels = frozenset(normalize_label(label) for label in observed_raw)
        validate_target_label_present(normalized_labels)
        class_registry = build_class_registry(normalized_labels)
        print(f"CICIoT2023 ingest complete: raw_rows={raw_row_count} classes={len(class_registry)}")
        connection.close()
        assign_secondary_roles(database_path, dataset_manifest_hash)
        connection = open_tabular_engine(database_path)
        train_sql = (
            "SELECT "
            + ", ".join(sql_ident(name) for name in predictor_columns)
            + " FROM retained JOIN role_assignments USING (stable_row_id) "
            f"WHERE role_assignments.role = {sql_string(role_hash_token(Role.ANCHOR_TRAIN))} "
            f"AND retained.normalized_label != {sql_string(CICIoTSpecialLabel.BACKDOOR_MALWARE)}"
        )
        moments = fit_feature_moments(
            predictor_columns,
            fetch_feature_statistics(connection, train_sql, predictor_columns),
            config.datasets.primary.scaling,
        )
        print(f"CICIoT2023 scaler fitted on {moments.training_row_count} anchor-train rows")
        views = _write_secondary_views(
            connection, predictor_columns, moments, prepared_root, overwrite
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        copy_query_to_parquet(
            connection,
            "SELECT "
            f"{sql_string(EXCLUSION_SCHEMA_VERSION)} AS schema_version, "
            "stable_row_id, file_sha256, relative_path, original_row_index, reason "
            "FROM exclusions ORDER BY relative_path, original_row_index",
            metadata_root / "dataset_exclusions.parquet",
        )
        copy_query_to_parquet(
            connection,
            "SELECT "
            f"{sql_string(ROLE_MANIFEST_SCHEMA_VERSION)} AS schema_version, "
            "stable_row_id, normalized_label, "
            "('PSEUDO_DOMAIN_' || CAST(pseudo_domain + 1 AS VARCHAR)) AS pseudo_domain, "
            "role FROM role_assignments "
            "ORDER BY normalized_label, pseudo_domain, stable_row_id",
            metadata_root / "ciciot2023_role_manifest.parquet",
        )
        write_json_payload(
            scaler_root / "ciciot2023_scaler.json",
            ScalerMetadata(
                schema_version=SCALER_SCHEMA_VERSION,
                feature_names=predictor_columns,
                means=moments.means,
                standard_deviations=moments.standard_deviations,
                training_row_count=moments.training_row_count,
            ),
            overwrite,
        )
        counts = connection.execute(
            "SELECT (SELECT count(*) FROM retained), (SELECT count(*) FROM exclusions)"
        ).fetchone()
        if counts is None:
            raise RuntimeError("CIC preprocessing count query returned no row")
        retained_count, excluded_count = counts
        print(
            "CICIoT2023 materialization complete: "
            f"retained={retained_count} excluded={excluded_count} views={len(views)}"
        )
        return SecondaryMaterializationSummary(
            dataset_manifest_hash=dataset_manifest_hash,
            class_registry=class_registry,
            predictor_columns=predictor_columns,
            predictor_count_matches_official=(
                len(predictor_columns) == OFFICIAL_EXPECTED_PREDICTOR_COUNT
            ),
            raw_row_count=raw_row_count,
            retained_row_count=int(retained_count),
            excluded_row_count=int(excluded_count),
            views=views,
            scaler=moments,
        )
    finally:
        connection.close()
