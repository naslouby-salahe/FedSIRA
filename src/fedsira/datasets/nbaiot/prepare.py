from __future__ import annotations

import csv
import hashlib
import subprocess
from pathlib import Path

import duckdb

from fedsira.config import RoleIntervals, SamplingCapsPerDomain
from fedsira.datasets.common import (
    SUPPORTED_ROLE_ORDER,
    TARGET_ROLE_ORDER,
    DatasetExclusionReason,
    DatasetPreparationLogFields,
    FeatureMoments,
    Role,
    RoleSamplingCap,
    ScalerMetadata,
    apply_sampling_cap,
    compute_file_checksum,
    compute_sample_id,
    copy_query_to_parquet,
    fetch_feature_statistics,
    fit_feature_moments,
    open_tabular_engine,
    read_csv_relation,
    role_for_normalized_position,
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
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_PRIMARY_PREDICTOR_COUNT,
    NBAIOT_TARGET_CLASS,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotAttackFamily,
    NBaiotClass,
    NBaiotDomain,
    nbaiot_domain_hash_token,
    normalize_path_token,
    resolve_attack_class,
    resolve_domain,
)
from fedsira.domain.enums import DatasetId
from fedsira.domain.types import (
    ArtifactDigest,
    DatasetClassToken,
    DatasetColumnName,
    DatasetFileDigest,
    DatasetManifestDigest,
    DomainCount,
    DomainId,
    FrozenDomainModel,
    OverwriteExisting,
    PreparedViewKey,
    RelativePathText,
    RetainMaterializedViews,
    RowCount,
    SampleIdPrefix,
    SamplingCap,
    SchemaVersion,
    SourceRowIndex,
    TextValue,
)
from fedsira.runtime import (
    current_application_context,
    framed_bytes,
    get_structured_logger,
    log_structured_event,
)

NBAIOT_SAMPLE_ID_PREFIX: SampleIdPrefix = "NBAIOT_SAMPLE_ID_V1"
PREPARED_VIEW_SCHEMA_VERSION: SchemaVersion = "fedsira|nbaiot_prepared_view|1"
SCALER_SCHEMA_VERSION: SchemaVersion = "fedsira|nbaiot_scaler|1"
BENIGN_FILENAME: RelativePathText = "benign_traffic.csv"

NBAIOT_PREPARATION_LOGGER = get_structured_logger("dataset_preparation")


class DiscoveredCsvFile(FrozenDomainModel):
    domain: NBaiotDomain
    class_id: NBaiotClass
    relative_path: RelativePathText
    file_sha256: DatasetFileDigest
    absolute_path: Path
    source_archive_digest: DatasetFileDigest | None = None


class RoleAssignment(FrozenDomainModel):
    sample_id: ArtifactDigest
    role: Role
    original_row_index: SourceRowIndex


class PreparedView(FrozenDomainModel):
    domain: NBaiotDomain
    class_id: NBaiotClass
    role: Role
    sample_ids: tuple[ArtifactDigest, ...]
    labels: tuple[DatasetClassToken, ...]
    parquet_path: Path

    @property
    def row_count(self) -> RowCount:
        return len(self.sample_ids)


class PreparedViewMetadata(FrozenDomainModel):
    schema_version: SchemaVersion
    domain: NBaiotDomain
    class_id: NBaiotClass
    role: Role
    row_count: RowCount


def extract_rar_archive(archive_path: Path, destination_directory: Path) -> None:
    destination_directory.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["unrar", "x", "-o-", str(archive_path), f"{destination_directory}/"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            f"unrar failed to extract {archive_path} (exit {result.returncode}): {result.stderr}"
        )


def _discover_attack_csv_files(
    device_directory: Path,
    domain: NBaiotDomain,
    family: NBaiotAttackFamily,
    extraction_cache_root: Path,
) -> tuple[DiscoveredCsvFile, ...]:
    extracted_directory = device_directory / f"{family}_attacks"
    archive_digest: DatasetFileDigest | None = None
    if not extracted_directory.is_dir():
        archive_path = device_directory / f"{family}_attacks.rar"
        if not archive_path.exists():
            return ()
        extracted_directory = extraction_cache_root / domain.name / f"{family}_attacks"
        archive_digest = compute_file_checksum(archive_path)
        extract_rar_archive(archive_path, extracted_directory)
    discovered: list[DiscoveredCsvFile] = []
    for csv_path in extracted_directory.glob("*.csv"):
        class_id = resolve_attack_class(family, csv_path.stem)
        if class_id is None:
            raise ValueError(
                f"unrecognized {family} attack basename {csv_path.stem!r} in {csv_path}"
            )
        try:
            layout_relative_path = csv_path.relative_to(device_directory).as_posix()
        except ValueError:
            layout_relative_path = f"{csv_path.parent.name}/{csv_path.name}"
        discovered.append(
            DiscoveredCsvFile(
                domain=domain,
                class_id=class_id,
                relative_path=layout_relative_path,
                file_sha256=compute_file_checksum(csv_path),
                absolute_path=csv_path,
                source_archive_digest=archive_digest,
            )
        )
    return tuple(discovered)


def discover_primary_csv_files(
    raw_root: Path,
    extraction_cache_root: Path,
) -> tuple[DiscoveredCsvFile, ...]:
    discovered: list[DiscoveredCsvFile] = []
    for device_directory in sorted(raw_root.iterdir(), key=lambda entry: entry.name):
        if not device_directory.is_dir():
            continue
        domain = resolve_domain(device_directory.name)
        if domain is None:
            raise ValueError(f"unrecognized N-BaIoT device directory: {device_directory.name}")
        benign_csv = device_directory / BENIGN_FILENAME
        if benign_csv.exists():
            discovered.append(
                DiscoveredCsvFile(
                    domain=domain,
                    class_id=NBaiotClass.BENIGN,
                    relative_path=benign_csv.relative_to(device_directory).as_posix(),
                    file_sha256=compute_file_checksum(benign_csv),
                    absolute_path=benign_csv,
                )
            )
        for family in NBaiotAttackFamily:
            discovered.extend(
                _discover_attack_csv_files(device_directory, domain, family, extraction_cache_root)
            )
    return tuple(
        sorted(
            discovered,
            key=lambda item: (item.domain, normalize_path_token(item.relative_path)),
        )
    )


def compute_dataset_manifest_hash(
    discovered: tuple[DiscoveredCsvFile, ...],
) -> DatasetManifestDigest:
    ordered = sorted(discovered, key=lambda item: (item.domain, item.relative_path))
    hasher = hashlib.sha256()
    for item in ordered:
        hasher.update(
            framed_bytes(
                nbaiot_domain_hash_token(item.domain),
                item.relative_path,
                item.file_sha256,
                item.source_archive_digest or "",
            )
        )
    return hasher.hexdigest()


def domains_with_target_stream(
    discovered: tuple[DiscoveredCsvFile, ...],
) -> frozenset[NBaiotDomain]:
    return frozenset(item.domain for item in discovered if item.class_id is NBAIOT_TARGET_CLASS)


def domains_missing_target_stream(
    discovered: tuple[DiscoveredCsvFile, ...],
) -> tuple[NBaiotDomain, ...]:
    holders = domains_with_target_stream(discovered)
    return tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain not in holders)


def classes_structurally_unavailable(
    discovered: tuple[DiscoveredCsvFile, ...],
) -> tuple[NBaiotClass, ...]:
    observed = frozenset(item.class_id for item in discovered)
    return tuple(class_id for class_id in NBAIOT_CLASS_ORDER if class_id not in observed)


def validate_target_holder_feasibility(
    discovered: tuple[DiscoveredCsvFile, ...],
    minimum_target_holding_domains: DomainCount,
) -> None:
    holder_count = len(domains_with_target_stream(discovered))
    if holder_count < minimum_target_holding_domains:
        missing = ", ".join(str(domain) for domain in domains_missing_target_stream(discovered))
        raise ValueError(
            f"only {holder_count} of {len(NBAIOT_DOMAIN_ORDER)} device proxies hold the "
            f"{NBAIOT_TARGET_CLASS} target stream; at least "
            f"{minimum_target_holding_domains} are required (missing: {missing})"
        )


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


def read_predictor_header(path: Path) -> tuple[DatasetColumnName, ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError(f"primary CSV is empty: {path}") from error
    return tuple(name.strip() for name in header)


def supported_class_sampling_caps(
    caps: SamplingCapsPerDomain,
    class_id: NBaiotClass,
) -> tuple[RoleSamplingCap, ...]:
    return tuple(
        RoleSamplingCap(
            role=role,
            cap=sampling_cap_for_role(
                caps, role, is_target=False, is_benign=class_id is NBaiotClass.BENIGN
            ),
        )
        for role in SUPPORTED_ROLE_ORDER
    )


def target_class_sampling_caps(caps: SamplingCapsPerDomain) -> tuple[RoleSamplingCap, ...]:
    return tuple(
        RoleSamplingCap(
            role=role,
            cap=sampling_cap_for_role(caps, role, is_target=True, is_benign=False),
        )
        for role in TARGET_ROLE_ORDER
    )


def _sampling_cap_for_role(
    sampling_caps: tuple[RoleSamplingCap, ...], role: Role
) -> SamplingCap | None:
    for role_cap in sampling_caps:
        if role_cap.role is role:
            return role_cap.cap
    raise ValueError(f"sampling cap missing for role {role.name}")


def assign_stream_roles_and_sample_ids(
    dataset_file_sha256: ArtifactDigest,
    domain_hash_token: DomainId,
    class_id: NBaiotClass,
    normalized_relative_csv_path: RelativePathText,
    stream_row_count: RowCount,
    role_intervals: RoleIntervals,
    sampling_caps_per_domain: SamplingCapsPerDomain,
) -> tuple[RoleAssignment, ...]:
    is_target = class_id is NBAIOT_TARGET_CLASS
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
                role_for_normalized_position(original_row_index / stream_row_count, windows),
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
                class_id,
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


def _nonfinite_predicate(feature_names: tuple[DatasetColumnName, ...]) -> TextValue:
    return " OR ".join(
        f"({sql_ident(name)} IS NULL OR NOT isfinite({sql_ident(name)}))" for name in feature_names
    )


def _unparseable_predicate(feature_names: tuple[DatasetColumnName, ...]) -> TextValue:
    return " OR ".join(f"{sql_ident(name)} IS NULL" for name in feature_names)


def _cast_feature_select(feature_names: tuple[DatasetColumnName, ...]) -> TextValue:
    casts = ", ".join(
        f"try_cast({sql_ident(name)} AS DOUBLE) AS {sql_ident(name)}" for name in feature_names
    )
    return casts


def ingest_primary_numeric_csv(
    connection: duckdb.DuckDBPyConnection,
    path: Path,
    ordered_header: tuple[DatasetColumnName, ...],
) -> None:
    try:
        connection.execute(
            "CREATE OR REPLACE TABLE current_raw AS "
            "SELECT (row_number() OVER () - 1) AS original_row_index, * "
            f"FROM {read_csv_relation(path, ordered_header)}"
        )
    except duckdb.Error as error:
        raise ValueError(f"primary CSV is unreadable: {path}") from error
    connection.execute(
        "CREATE OR REPLACE TABLE current_numeric AS "
        f"SELECT original_row_index, {_cast_feature_select(ordered_header)} FROM current_raw"
    )
    unparseable = connection.execute(
        "SELECT original_row_index FROM current_numeric "
        f"WHERE {_unparseable_predicate(ordered_header)} LIMIT 1"
    ).fetchone()
    if unparseable is not None:
        raise ValueError(
            f"{DatasetExclusionReason.UNPARSEABLE_PREDICTOR} in {path} at row {unparseable[0]}"
        )
    nonfinite = connection.execute(
        "SELECT original_row_index FROM current_numeric "
        f"WHERE {_nonfinite_predicate(ordered_header)} LIMIT 1"
    ).fetchone()
    if nonfinite is not None:
        raise ValueError(
            f"non-finite primary predictor value in {path} at row {nonfinite[0]}: "
            f"{DatasetExclusionReason.NON_FINITE_PREDICTOR}"
        )


def _view_key(domain: NBaiotDomain, class_id: NBaiotClass, role: Role) -> PreparedViewKey:
    return f"{nbaiot_domain_hash_token(domain)}_{class_id}_{role_hash_token(role)}"


def _ensure_all_rows(
    connection: duckdb.DuckDBPyConnection,
    item: DiscoveredCsvFile,
    feature_names: tuple[DatasetColumnName, ...],
) -> None:
    identity_select = (
        f"{sql_string(item.file_sha256)} AS file_sha256, "
        f"{sql_string(item.relative_path)} AS relative_path, "
        f"{sql_string(item.domain.name)} AS domain, "
        f"{sql_string(item.class_id)} AS class_id, "
        "original_row_index, " + ", ".join(sql_ident(name) for name in feature_names)
    )
    exists = connection.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'all_rows'"
    ).fetchone()
    if exists is None:
        connection.execute(
            f"CREATE TABLE all_rows AS SELECT {identity_select} FROM current_numeric LIMIT 0"
        )
        connection.execute(
            "CREATE TABLE selected ("
            "file_sha256 VARCHAR, original_row_index BIGINT, role VARCHAR, "
            "sample_id VARCHAR, assignment_order BIGINT)"
        )
    connection.execute(f"INSERT INTO all_rows SELECT {identity_select} FROM current_numeric")


def materialize_nbaiot_prepared_views(
    discovered: tuple[DiscoveredCsvFile, ...],
    prepared_root: Path,
    scaler_root: Path,
    overwrite: OverwriteExisting = False,
    retain_materialized_views: RetainMaterializedViews = True,
) -> tuple[tuple[PreparedView, ...], FeatureMoments]:
    config = current_application_context().scientific_config
    if not discovered:
        raise ValueError("N-BaIoT discovery produced no CSV files")
    feature_names = read_predictor_header(discovered[0].absolute_path)
    validate_predictor_schema(feature_names)
    connection = open_tabular_engine()
    try:
        for item in discovered:
            log_structured_event(
                NBAIOT_PREPARATION_LOGGER,
                "dataset.ingest",
                DatasetPreparationLogFields(
                    dataset=DatasetId.N_BAIOT,
                    domain=item.domain.name,
                    class_id=item.class_id,
                    file=item.relative_path,
                ),
            )
            observed_header = read_predictor_header(item.absolute_path)
            validate_consistent_predictor_schema(feature_names, observed_header)
            ingest_primary_numeric_csv(connection, item.absolute_path, feature_names)
            _ensure_all_rows(connection, item, feature_names)
            row_count_row = connection.execute("SELECT count(*) FROM current_numeric").fetchone()
            if row_count_row is None:
                raise ValueError(f"N-BaIoT row count query failed for {item.relative_path}")
            row_count = row_count_row[0]
            if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
                raise TypeError("N-BaIoT row count must be a non-negative integer")
            assignments = assign_stream_roles_and_sample_ids(
                dataset_file_sha256=item.file_sha256,
                domain_hash_token=nbaiot_domain_hash_token(item.domain),
                class_id=item.class_id,
                normalized_relative_csv_path=f"{item.domain}/{item.relative_path}",
                stream_row_count=row_count,
                role_intervals=config.datasets.primary.role_intervals,
                sampling_caps_per_domain=config.datasets.primary.sampling_caps_per_domain,
            )
            log_structured_event(
                NBAIOT_PREPARATION_LOGGER,
                "dataset.roles",
                DatasetPreparationLogFields(
                    dataset=DatasetId.N_BAIOT,
                    file=item.relative_path,
                    rows=row_count,
                    selected=len(assignments),
                ),
            )
            connection.executemany(
                "INSERT INTO selected VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        item.file_sha256,
                        assignment.original_row_index,
                        role_hash_token(assignment.role),
                        assignment.sample_id,
                        order,
                    )
                    for order, assignment in enumerate(assignments)
                ],
            )
        train_sql = (
            "SELECT "
            + ", ".join(sql_ident(name) for name in feature_names)
            + " FROM all_rows JOIN selected USING (file_sha256, original_row_index) "
            f"WHERE selected.role = {sql_string(role_hash_token(Role.ANCHOR_TRAIN))} "
            f"AND all_rows.class_id != {sql_string(NBAIOT_TARGET_CLASS)}"
        )
        moments = fit_feature_moments(
            feature_names,
            fetch_feature_statistics(connection, train_sql, feature_names),
            config.datasets.primary.scaling,
        )
        log_structured_event(
            NBAIOT_PREPARATION_LOGGER,
            "dataset.scaler.fitted",
            DatasetPreparationLogFields(
                dataset=DatasetId.N_BAIOT,
                training_rows=moments.training_row_count,
            ),
        )
        prepared_root.mkdir(parents=True, exist_ok=True)
        scaler_root.mkdir(parents=True, exist_ok=True)
        views: list[PreparedView] = []
        identities = connection.execute(
            "SELECT domain, class_id, role, count(*) "
            "FROM selected JOIN all_rows USING (file_sha256, original_row_index) "
            "GROUP BY domain, class_id, role "
            "ORDER BY domain, class_id, role"
        ).fetchall()
        standardized = ", ".join(
            standardized_feature_sql(
                name,
                moments.means[index],
                moments.standard_deviations[index],
                config.datasets.primary.scaling,
            )
            for index, name in enumerate(feature_names)
        )
        for domain_token, class_token, role_token, view_row_count in identities:
            domain = NBaiotDomain[str(domain_token)]
            class_id = NBaiotClass[str(class_token)]
            role = role_from_hash_token(str(role_token))
            view_key = _view_key(domain, class_id, role)
            parquet_path = view_parquet_path(prepared_root, view_key)
            query = (
                "SELECT selected.sample_id AS sample_id, all_rows.class_id AS label, "
                f"{standardized} "
                "FROM all_rows JOIN selected USING (file_sha256, original_row_index) "
                f"WHERE all_rows.domain = {sql_string(domain.name)} "
                f"AND all_rows.class_id = {sql_string(class_id)} "
                f"AND selected.role = {sql_string(role_hash_token(role))} "
                "ORDER BY selected.assignment_order"
            )
            if overwrite or not parquet_path.exists():
                copy_query_to_parquet(connection, query, parquet_path)
            write_json_payload(
                (prepared_root / view_key).with_suffix(".json"),
                PreparedViewMetadata(
                    schema_version=PREPARED_VIEW_SCHEMA_VERSION,
                    domain=domain,
                    class_id=class_id,
                    role=role,
                    row_count=int(view_row_count),
                ),
                overwrite,
            )
            log_structured_event(
                NBAIOT_PREPARATION_LOGGER,
                "dataset.view.written",
                DatasetPreparationLogFields(
                    dataset=DatasetId.N_BAIOT,
                    view=view_key,
                    rows=view_row_count,
                    path=parquet_path.name,
                ),
            )
            if retain_materialized_views:
                rows = connection.execute(
                    "SELECT selected.sample_id, all_rows.class_id "
                    "FROM all_rows JOIN selected USING (file_sha256, original_row_index) "
                    f"WHERE all_rows.domain = {sql_string(domain.name)} "
                    f"AND all_rows.class_id = {sql_string(class_id)} "
                    f"AND selected.role = {sql_string(role_hash_token(role))} "
                    "ORDER BY selected.assignment_order"
                ).fetchall()
                views.append(
                    PreparedView(
                        domain=domain,
                        class_id=class_id,
                        role=role,
                        sample_ids=tuple(str(row[0]) for row in rows),
                        labels=tuple(str(row[1]) for row in rows),
                        parquet_path=parquet_path,
                    )
                )
        write_json_payload(
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
    finally:
        connection.close()
