from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import duckdb

from fedsira.config import SamplingCapsPerDomain
from fedsira.datasets.ciciot2023.schema import (
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    PSEUDO_DOMAIN_COUNT,
    TARGET_LABEL,
    CICIoT2023PseudoDomain,
    CICIoTRowIdentifierToken,
    CICIoTSpecialLabel,
    build_class_registry,
    normalize_label,
    normalize_label_token,
    target_family_collision_is_declared,
)
from fedsira.datasets.common import (
    PREPROCESSING_SAMPLE_ORDER_SEED,
    SUPPORTED_ROLE_ORDER,
    TARGET_ROLE_ORDER,
    DatasetExclusionReason,
    DatasetPreparationLogFields,
    FeatureMoments,
    Role,
    ScalerMetadata,
    compute_file_checksum,
    copy_query_to_parquet,
    fetch_feature_statistics,
    fit_feature_moments,
    open_tabular_engine,
    read_csv_relation,
    role_case_sql,
    sampling_cap_for_role,
    sql_ident,
    sql_string,
    standardized_feature_sql,
    supported_role_windows,
    target_role_windows,
    view_parquet_path,
    write_json_payload,
)
from fedsira.datasets.role_split import prepared_view_cache_identity
from fedsira.domain.enums import (
    CICIoT2023Acquisition,
    DatasetId,
    LogEvent,
    RuntimeComponentName,
    SeedDerivationLabel,
)
from fedsira.domain.types import (
    ArtifactDigest,
    BooleanValue,
    ClassLabel,
    DatasetClassToken,
    DatasetColumnCount,
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
    RowCount,
    SampleIdPrefix,
    SchemaVersion,
    SqlText,
)
from fedsira.runtime import (
    current_application_context,
    framed_bytes,
    get_structured_logger,
    log_structured_event,
)

_ASCII_HEADER_WHITESPACE = " \t\r\n\f\v"
CICIOT_PARALLEL_TRANSFORM_THREADS = 4
CICIOT_PREPARATION_CHECKPOINT_SHARDS = 16
STABLE_ROW_ID_PREFIX: SampleIdPrefix = "CICIOT2023_SAMPLE_ID_V1"
PREPARED_VIEW_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_prepared_view|2"
SCALER_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_scaler|1"
ROLE_MANIFEST_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_role_manifest|1"
EXCLUSION_SCHEMA_VERSION: SchemaVersion = "fedsira|ciciot2023_exclusions|1"
_WHITESPACE_HYPHEN_UNDERSCORE = re.compile(r"[\s\-_]+")

CICIOT_PREPARATION_LOGGER = get_structured_logger(RuntimeComponentName.DATASET_PREPARATION)


class SecondaryCsvFile(FrozenDomainModel):
    absolute_path: Path
    relative_path: RelativePathText
    file_sha256: DatasetFileDigest
    shard_class: ClassLabel | None = None
    label_column: DatasetColumnName | None = None


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


class CICIoTPreparedViewMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    cache_identity: ArtifactDigest
    parquet_sha256: ArtifactDigest
    pseudo_domain: CICIoT2023PseudoDomain
    normalized_label: DatasetClassToken
    role: Role
    row_count: RowCount


def _cached_view_is_reusable(
    parquet_path: Path,
    metadata_path: Path,
    cache_identity: ArtifactDigest,
    row_count: RowCount,
) -> BooleanValue:
    if not parquet_path.is_file() or not metadata_path.is_file():
        return False
    try:
        metadata = CICIoTPreparedViewMetadata.model_validate_json(metadata_path.read_text())
    except (OSError, ValueError):
        return False
    return (
        metadata.cache_identity == cache_identity
        and metadata.row_count == row_count
        and metadata.parquet_sha256 == compute_file_checksum(parquet_path)
    )


def resolve_label_column(header: tuple[DatasetColumnName, ...]) -> DatasetColumnName | None:
    label_columns = tuple(column for column in header if normalize_label_token(column) == "LABEL")
    if len(label_columns) > 1:
        raise ValueError(
            "expected at most one column named 'label' (case-insensitive), "
            f"found {len(label_columns)}: {label_columns}"
        )
    return label_columns[0] if label_columns else None


def discover_secondary_csv_files(
    csv_root: Path, acquisition: CICIoT2023Acquisition
) -> tuple[SecondaryCsvFile, ...]:
    paths = sorted(csv_root.rglob("*.csv"), key=lambda path: path.relative_to(csv_root).as_posix())
    if not paths:
        raise ValueError(f"no CICIoT2023 CSV shards found beneath {csv_root}")
    discovered: list[SecondaryCsvFile] = []
    for path in paths:
        label_column = resolve_label_column(read_csv_header(path))
        selected = (
            label_column is not None
            if acquisition is CICIoT2023Acquisition.LABELED_SHARDS
            else label_column is None
        )
        if not selected:
            continue
        shard_class = None if label_column is not None else normalize_label(path.parent.name)
        discovered.append(
            SecondaryCsvFile(
                absolute_path=path,
                relative_path=path.relative_to(csv_root).as_posix(),
                file_sha256=compute_file_checksum(path),
                shard_class=shard_class,
                label_column=label_column,
            )
        )
    if not discovered:
        raise ValueError(
            f"no CICIoT2023 CSV shards match the configured {acquisition} acquisition "
            f"beneath {csv_root}"
        )
    return tuple(discovered)


def compute_dataset_manifest_hash(
    discovered: tuple[SecondaryCsvFile, ...],
) -> DatasetManifestDigest:
    if not discovered:
        raise ValueError("secondary dataset manifest requires at least one CSV shard")
    fields: list[FramingField] = []
    for item in sorted(discovered, key=lambda discovered_file: discovered_file.relative_path):
        fields.extend((item.relative_path, item.file_sha256))
    return hashlib.sha256(framed_bytes(SeedDerivationLabel.DATASET_MANIFEST, *fields)).hexdigest()


def read_csv_header(path: Path) -> tuple[DatasetColumnName, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            raw_header = next(reader)
        except StopIteration as error:
            raise ValueError(f"CICIoT2023 CSV shard is empty: {path}") from error
    return tuple(name.strip(_ASCII_HEADER_WHITESPACE) for name in raw_header)


def validate_consistent_header(
    reference_header: tuple[DatasetColumnName, ...],
    observed_header: tuple[DatasetColumnName, ...],
) -> None:
    if observed_header != reference_header:
        raise ValueError("secondary CSV header does not match the fixed reference schema")


def resolve_predictor_columns(
    header: tuple[DatasetColumnName, ...],
    label_column: DatasetColumnName | None,
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
    label_column: DatasetColumnName | None,
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
            if target_family_collision_is_declared(first, second):
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


def framed_sha256_sql(fields: tuple[SqlText, ...]) -> SqlText:
    framed_fields: list[str] = []
    for field in fields:
        encoded = f"encode(CAST({field} AS VARCHAR))"
        length_prefix = f"from_hex(lpad(to_hex(octet_length({encoded})), 8, '0'))"
        framed_fields.append(f"({length_prefix} || {encoded})")
    return f"sha256({' || '.join(framed_fields)})"


def pseudo_domain_sql(
    normalized_label: SqlText,
    stable_row_id: SqlText,
    dataset_manifest_hash: DatasetManifestDigest,
    partition_salt: PartitionSalt,
) -> SqlText:
    digest = framed_sha256_sql(
        (
            sql_string(SeedDerivationLabel.PSEUDO_DOMAIN_HASH),
            sql_string(dataset_manifest_hash),
            normalized_label,
            stable_row_id,
            sql_string(str(partition_salt)),
        )
    )
    return f"(CAST('0x' || substr({digest}, 1, 16) AS UBIGINT) % {PSEUDO_DOMAIN_COUNT})"


def stable_row_id_sql(item: SecondaryCsvFile, original_row_index: SqlText) -> SqlText:
    return framed_sha256_sql(
        (
            sql_string(STABLE_ROW_ID_PREFIX),
            sql_string(item.relative_path),
            sql_string(item.file_sha256),
            original_row_index,
        )
    )


def sampling_digest_sql(
    dataset_manifest_hash: DatasetManifestDigest,
    normalized_label: SqlText,
    pseudo_domain: SqlText,
    role: SqlText,
    stable_row_id: SqlText,
) -> SqlText:
    fields = (
        sql_string(dataset_manifest_hash),
        f"('PSEUDO_DOMAIN_' || CAST(({pseudo_domain}) + 1 AS VARCHAR))",
        normalized_label,
        role,
        stable_row_id,
        sql_string(str(PREPROCESSING_SAMPLE_ORDER_SEED)),
    )
    return f"from_hex({framed_sha256_sql(fields)})"


def _create_preparation_tables(
    connection: duckdb.DuckDBPyConnection,
    predictor_columns: tuple[DatasetColumnName, ...],
) -> None:
    feature_schema = ", ".join(f"{sql_ident(name)} DOUBLE" for name in predictor_columns)
    connection.execute(
        "CREATE TABLE retained ("
        "stable_row_id VARCHAR, file_sha256 VARCHAR, relative_path VARCHAR, "
        "original_row_index BIGINT, normalized_label VARCHAR, pseudo_domain INTEGER, "
        f"{feature_schema})"
    )
    connection.execute(
        "CREATE TABLE exclusions ("
        "stable_row_id VARCHAR, file_sha256 VARCHAR, relative_path VARCHAR, "
        "original_row_index BIGINT, reason VARCHAR)"
    )
    connection.execute(
        "CREATE TABLE role_assignments ("
        "stable_row_id VARCHAR, normalized_label VARCHAR, "
        "pseudo_domain INTEGER, role VARCHAR)"
    )


def _exclusion_reason_sql(predictor_columns: tuple[DatasetColumnName, ...]) -> SqlText:
    unparseable = " OR ".join(f"{sql_ident(name)} IS NULL" for name in predictor_columns)
    nonfinite = " OR ".join(f"NOT isfinite({sql_ident(name)})" for name in predictor_columns)
    return (
        "CASE "
        f"WHEN {unparseable} THEN {sql_string(DatasetExclusionReason.UNPARSEABLE_PREDICTOR)} "
        f"WHEN {nonfinite} THEN {sql_string(DatasetExclusionReason.NON_FINITE_PREDICTOR)} "
        "END"
    )


def _trailing_width_mismatch_range(
    path: Path, column_count: DatasetColumnCount
) -> tuple[RowCount, RowCount] | None:
    malformed: list[RowCount] = []
    data_rows: RowCount = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for index, row in enumerate(reader):
            data_rows = index + 1
            if len(row) != column_count:
                malformed.append(index)
    if not malformed:
        return None
    first_excluded = data_rows - len(malformed)
    if tuple(malformed) != tuple(range(first_excluded, data_rows)):
        return None
    return (first_excluded, data_rows)


def _record_width_exclusions(
    connection: duckdb.DuckDBPyConnection,
    item: SecondaryCsvFile,
    malformed: tuple[RowCount, RowCount],
) -> None:
    first_excluded, data_rows = malformed
    stable_row_id = stable_row_id_sql(item, "original_row_index")
    connection.execute(
        "INSERT INTO exclusions "
        f"SELECT {stable_row_id}, "
        "file_sha256, relative_path, original_row_index, reason FROM ("
        f"SELECT {sql_string(item.relative_path)} AS relative_path, "
        f"{sql_string(item.file_sha256)} AS file_sha256, "
        "range AS original_row_index, "
        f"{sql_string(DatasetExclusionReason.ROW_WIDTH_MISMATCH)} AS reason "
        f"FROM range({first_excluded}, {data_rows}))"
    )


def _ingest_shard(
    connection: duckdb.DuckDBPyConnection,
    item: SecondaryCsvFile,
    header: tuple[DatasetColumnName, ...],
    predictor_columns: tuple[DatasetColumnName, ...],
    dataset_manifest_hash: DatasetManifestDigest,
    partition_salt: PartitionSalt,
) -> tuple[RowCount, tuple[ClassLabel, ...]]:
    log_structured_event(
        CICIOT_PREPARATION_LOGGER,
        LogEvent.DATASET_INGEST,
        DatasetPreparationLogFields(dataset=DatasetId.CICIOT2023, file=item.relative_path),
    )
    connection.execute("SET threads TO 1")
    physical_row_count: RowCount | None = None
    try:
        connection.execute(
            "CREATE OR REPLACE TABLE shard AS "
            "SELECT (row_number() OVER () - 1) AS original_row_index, * "
            f"FROM {read_csv_relation(item.absolute_path, header)}"
        )
    except duckdb.Error as error:
        malformed = _trailing_width_mismatch_range(item.absolute_path, len(header))
        if malformed is None:
            raise ValueError(
                f"CICIoT2023 row width does not match validated header: file={item.relative_path}"
            ) from error
        log_structured_event(
            CICIOT_PREPARATION_LOGGER,
            LogEvent.DATASET_SHARD_WIDTH_EXCLUDED,
            DatasetPreparationLogFields(
                dataset=DatasetId.CICIOT2023,
                file=item.relative_path,
                excluded_rows=len(malformed),
            ),
        )
        connection.execute(
            "CREATE OR REPLACE TABLE shard AS "
            "SELECT (row_number() OVER () - 1) AS original_row_index, * "
            f"FROM {read_csv_relation(item.absolute_path, header, True)}"
        )
        recorded = connection.execute("SELECT count(*) FROM shard").fetchone()
        if recorded is None or int(recorded[0]) != malformed[0]:
            raise ValueError(
                f"CICIoT2023 width-excluded rows are not a trailing run: file={item.relative_path}"
            ) from error
        _record_width_exclusions(connection, item, malformed)
        physical_row_count = malformed[1]
    count_row = connection.execute("SELECT count(*) FROM shard").fetchone()
    if count_row is None:
        raise ValueError(f"CICIoT2023 shard count query failed: {item.relative_path}")
    raw_count = count_row[0]
    if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count < 0:
        raise TypeError("CICIoT2023 shard row count must be a non-negative integer")
    if physical_row_count is not None:
        raw_count = physical_row_count
    connection.execute(f"SET threads TO {CICIOT_PARALLEL_TRANSFORM_THREADS}")
    reason_sql = _exclusion_reason_sql(predictor_columns)
    if item.label_column is not None:
        raw_label_sql: SqlText = sql_ident(item.label_column)
    elif item.shard_class is not None:
        raw_label_sql = sql_string(item.shard_class)
    else:
        raise ValueError(f"CICIoT2023 shard has no class label source: {item.relative_path}")
    casted_features = ", ".join(
        f"try_cast({sql_ident(name)} AS DOUBLE) AS {sql_ident(name)}" for name in predictor_columns
    )
    connection.execute(
        "CREATE OR REPLACE TABLE classified AS "
        "SELECT casted.*, "
        f"{reason_sql} AS reason FROM ("
        "SELECT original_row_index, "
        f"{raw_label_sql} AS raw_label, {casted_features} FROM shard"
        ") AS casted"
    )
    raw_labels = connection.execute("SELECT DISTINCT raw_label FROM classified").fetchall()
    normalized_labels: list[tuple[str, ClassLabel]] = []
    for row in raw_labels:
        raw_label = row[0]
        if not isinstance(raw_label, str):
            raise TypeError("CICIoT2023 class labels must be text")
        normalized_labels.append((raw_label, normalize_label(raw_label)))
    connection.execute(
        "CREATE OR REPLACE TABLE normalized_label_map (raw_label VARCHAR, normalized_label VARCHAR)"
    )
    connection.executemany("INSERT INTO normalized_label_map VALUES (?, ?)", normalized_labels)
    stable_row_id = stable_row_id_sql(item, "classified.original_row_index")
    pseudo_domain_expression = pseudo_domain_sql(
        "normalized_label", "stable_row_id", dataset_manifest_hash, partition_salt
    )
    feature_insert = ", ".join(f"identified.{sql_ident(name)}" for name in predictor_columns)
    connection.execute(
        "INSERT INTO exclusions "
        "SELECT stable_row_id, "
        f"{sql_string(item.file_sha256)}, {sql_string(item.relative_path)}, "
        "original_row_index, reason FROM ("
        "SELECT original_row_index, reason, "
        f"{stable_row_id} AS stable_row_id FROM classified "
        "WHERE reason IS NOT NULL) AS excluded"
    )
    connection.execute(
        "INSERT INTO retained "
        "SELECT stable_row_id, "
        f"{sql_string(item.file_sha256)}, {sql_string(item.relative_path)}, "
        "original_row_index, normalized_label, "
        f"{pseudo_domain_expression}, "
        f"{feature_insert} FROM ("
        "SELECT classified.original_row_index, "
        f"{stable_row_id} AS stable_row_id, normalized_label_map.normalized_label, "
        + ", ".join(f"classified.{sql_ident(name)}" for name in predictor_columns)
        + " FROM classified LEFT JOIN normalized_label_map USING (raw_label) "
        "WHERE reason IS NULL) AS identified"
    )
    labels = tuple(raw_label for raw_label, _ in normalized_labels)
    connection.execute("SET threads TO 1")
    return raw_count, labels


def _cap_case_sql(caps: SamplingCapsPerDomain) -> SqlText:
    target = sql_string(CICIoTSpecialLabel.BACKDOOR_MALWARE)
    benign = sql_string(CICIoTSpecialLabel.BENIGN)
    clauses: list[SqlText] = []
    for role in TARGET_ROLE_ORDER:
        cap = sampling_cap_for_role(caps, role, is_target=True, is_benign=False)
        if cap is None:
            continue
        clauses.append(
            f"WHEN normalized_label = {target} AND role = {sql_string(role.name)} THEN {cap}"
        )
    for role in SUPPORTED_ROLE_ORDER:
        if role is Role.REPORT_TEST:
            clauses.append(
                f"WHEN normalized_label != {target} AND role = {sql_string(role.name)} "
                f"AND normalized_label = {benign} THEN {caps.report_test_benign}"
            )
            other_cap = caps.report_test_other_supported_per_class
            clauses.append(
                f"WHEN normalized_label != {target} AND role = {sql_string(role.name)} "
                f"AND normalized_label != {benign} THEN {other_cap}"
            )
            continue
        cap = sampling_cap_for_role(caps, role, is_target=False, is_benign=False)
        if cap is None:
            continue
        clauses.append(
            f"WHEN normalized_label != {target} AND role = {sql_string(role.name)} THEN {cap}"
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
            "stable_row_id VARCHAR, normalized_label VARCHAR, "
            "pseudo_domain INTEGER, role VARCHAR)"
        )
        _assign_secondary_roles(connection, dataset_manifest_hash)
    finally:
        connection.close()


def _assign_secondary_roles(
    connection: duckdb.DuckDBPyConnection,
    dataset_manifest_hash: DatasetManifestDigest,
) -> None:
    connection.execute(f"SET threads TO {CICIOT_PARALLEL_TRANSFORM_THREADS}")
    config = current_application_context().scientific_config
    target = sql_string(CICIoTSpecialLabel.BACKDOOR_MALWARE)
    position_sql = "(group_index * 1.0) / group_size"
    target_role_sql = role_case_sql(
        position_sql, target_role_windows(config.datasets.primary.role_intervals)
    )
    supported_role_sql = role_case_sql(
        position_sql, supported_role_windows(config.datasets.primary.role_intervals)
    )
    cap_sql = _cap_case_sql(config.datasets.primary.sampling_caps_per_domain)
    digest_expression = sampling_digest_sql(
        dataset_manifest_hash, "normalized_label", "pseudo_domain", "role", "stable_row_id"
    )
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
        f"{digest_expression} "
        "AS digest "
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
    cache_identity: ArtifactDigest,
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
    for domain_index, label, stored_role_hash_token, row_count in identities:
        pseudo_domain = CICIoT2023PseudoDomain(int(domain_index))
        role = Role[str(stored_role_hash_token)]
        view_key: PreparedViewKey = f"{pseudo_domain.display_token}_{label}_{role.name}"
        parquet_path = view_parquet_path(prepared_root, view_key)
        metadata_path = (prepared_root / view_key).with_suffix(".json")
        query = (
            "SELECT retained.stable_row_id AS sample_id, retained.normalized_label AS label, "
            f"{standardized} FROM role_assignments JOIN retained USING (stable_row_id) "
            f"WHERE role_assignments.pseudo_domain = {int(pseudo_domain)} "
            f"AND role_assignments.normalized_label = {sql_string(str(label))} "
            f"AND role_assignments.role = {sql_string(role.name)} "
            "ORDER BY retained.stable_row_id"
        )
        reusable = not overwrite and _cached_view_is_reusable(
            parquet_path, metadata_path, cache_identity, int(row_count)
        )
        if not reusable:
            copy_query_to_parquet(connection, query, parquet_path)
            write_json_payload(
                metadata_path,
                CICIoTPreparedViewMetadata(
                    schema_version=PREPARED_VIEW_SCHEMA_VERSION,
                    pseudo_domain=pseudo_domain,
                    normalized_label=str(label),
                    role=role,
                    row_count=int(row_count),
                    cache_identity=cache_identity,
                    parquet_sha256=compute_file_checksum(parquet_path),
                ),
                True,
            )
        log_structured_event(
            CICIOT_PREPARATION_LOGGER,
            LogEvent.DATASET_VIEW_WRITTEN,
            DatasetPreparationLogFields(
                dataset=DatasetId.CICIOT2023, view=view_key, rows=row_count
            ),
        )
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
    cache_identity = prepared_view_cache_identity(DatasetId.CICIOT2023, dataset_manifest_hash)
    reference_header = read_csv_header(discovered[0].absolute_path)
    if len(set(reference_header)) != len(reference_header):
        raise ValueError("CICIoT2023 fixed header contains duplicate names")
    label_column = discovered[0].label_column
    for item in discovered[1:]:
        validate_consistent_header(reference_header, read_csv_header(item.absolute_path))
        if item.label_column != label_column:
            raise ValueError("CICIoT2023 shards disagree on the in-file class label column")
        if (item.shard_class is None) is not (discovered[0].shard_class is None):
            raise ValueError("CICIoT2023 shards disagree on the class label source")
    row_identifier_columns = resolve_row_identifier_columns(
        discovered, reference_header, label_column
    )
    predictor_columns = resolve_predictor_columns(
        reference_header, label_column, row_identifier_columns
    )
    cache_root.mkdir(parents=True, exist_ok=True)
    database_path = cache_root / "ciciot2023_preparation.duckdb"
    for stale_database in (database_path, database_path.with_name(f"{database_path.name}.wal")):
        if stale_database.exists():
            stale_database.unlink()
    connection = open_tabular_engine(database_path)
    raw_row_count: RowCount = 0
    try:
        _create_preparation_tables(connection, predictor_columns)
        observed_raw: list[ClassLabel] = []
        for shard_index, item in enumerate(discovered, start=1):
            shard_rows, shard_labels = _ingest_shard(
                connection,
                item,
                reference_header,
                predictor_columns,
                dataset_manifest_hash,
                config.datasets.secondary.pseudo_domain_partition_salt,
            )
            if shard_index % CICIOT_PREPARATION_CHECKPOINT_SHARDS == 0 or shard_index == len(
                discovered
            ):
                connection.execute("CHECKPOINT")
            raw_row_count += shard_rows
            observed_raw.extend(shard_labels)
            if shard_index % CICIOT_PREPARATION_CHECKPOINT_SHARDS == 0 or shard_index == len(
                discovered
            ):
                log_structured_event(
                    CICIOT_PREPARATION_LOGGER,
                    LogEvent.DATASET_INGEST_PROGRESS,
                    DatasetPreparationLogFields(
                        dataset=DatasetId.CICIOT2023,
                        file=item.relative_path,
                        raw_rows=raw_row_count,
                        completed_shards=shard_index,
                        total_shards=len(discovered),
                    ),
                )
        validate_label_collisions(frozenset(observed_raw))
        normalized_labels = frozenset(normalize_label(label) for label in observed_raw)
        validate_target_label_present(normalized_labels)
        class_registry = build_class_registry(normalized_labels)
        log_structured_event(
            CICIOT_PREPARATION_LOGGER,
            LogEvent.DATASET_INGEST_COMPLETED,
            DatasetPreparationLogFields(
                dataset=DatasetId.CICIOT2023,
                raw_rows=raw_row_count,
                class_count=len(class_registry),
            ),
        )
        connection.close()
        assign_secondary_roles(database_path, dataset_manifest_hash)
        connection = open_tabular_engine(database_path)
        train_sql = (
            "SELECT "
            + ", ".join(sql_ident(name) for name in predictor_columns)
            + " FROM retained JOIN role_assignments USING (stable_row_id) "
            f"WHERE role_assignments.role = {sql_string(Role.ANCHOR_TRAIN.name)} "
            f"AND retained.normalized_label != {sql_string(CICIoTSpecialLabel.BACKDOOR_MALWARE)}"
        )
        moments = fit_feature_moments(
            predictor_columns,
            fetch_feature_statistics(connection, train_sql, predictor_columns),
            config.datasets.primary.scaling,
        )
        log_structured_event(
            CICIOT_PREPARATION_LOGGER,
            LogEvent.DATASET_SCALER_FITTED,
            DatasetPreparationLogFields(
                dataset=DatasetId.CICIOT2023, training_rows=moments.training_row_count
            ),
        )
        views = _write_secondary_views(
            connection, predictor_columns, moments, prepared_root, cache_identity, overwrite
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
