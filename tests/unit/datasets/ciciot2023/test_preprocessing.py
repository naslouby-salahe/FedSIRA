import hashlib
from pathlib import Path

import duckdb

from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.ciciot2023.prepare import (
    CICIoTPreparedViewMetadata,
    SecondaryCsvFile,
    assign_secondary_roles,
    framed_sha256_sql,
    materialize_ciciot2023_prepared_views,
    pseudo_domain_sql,
    resolve_predictor_columns,
    resolve_row_identifier_columns,
    sampling_digest_sql,
)
from fedsira.datasets.ciciot2023.schema import (
    BENIGN_LABEL,
    PSEUDO_DOMAIN_COUNT,
    TARGET_LABEL,
    CICIoT2023PseudoDomain,
)
from fedsira.datasets.common import (
    PREPROCESSING_SAMPLE_ORDER_SEED,
    DatasetExclusionReason,
    Role,
    compute_file_checksum,
    sql_string,
)
from fedsira.domain.enums import SeedDerivationLabel
from fedsira.runtime import framed_bytes

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def _query_scalar(sql: str) -> object:
    connection = duckdb.connect()
    try:
        row = connection.execute(sql).fetchone()
        assert row is not None
        return row[0]
    finally:
        connection.close()


def _seed_retained(
    database_path: Path,
    label: str,
    domain: CICIoT2023PseudoDomain,
    row_count: int,
) -> None:
    connection = duckdb.connect(str(database_path))
    connection.execute(
        "CREATE TABLE retained ("
        "stable_row_id VARCHAR, normalized_label VARCHAR, pseudo_domain INTEGER)"
    )
    connection.executemany(
        "INSERT INTO retained VALUES (?, ?, ?)",
        [(f"{index:064x}", label, int(domain)) for index in range(row_count)],
    )
    connection.close()


def _roles_by_stable_row_id(database_path: Path) -> dict[str, Role]:
    connection = duckdb.connect(str(database_path))
    rows = connection.execute("SELECT stable_row_id, role FROM role_assignments").fetchall()
    connection.close()
    return {str(stable_row_id): Role[str(role_token)] for stable_row_id, role_token in rows}


def test_native_sql_framed_sha256_matches_python() -> None:
    fields = ("CICIOT2023_SAMPLE_ID_V1", "a/b.csv", "a" * 64, "928")
    sql = framed_sha256_sql(tuple(sql_string(field) for field in fields))
    actual = _query_scalar(f"SELECT {sql}")
    expected = hashlib.sha256(framed_bytes(*fields)).hexdigest()
    assert actual == expected


def test_native_sql_pseudo_domain_matches_python() -> None:
    manifest = "f" * 64
    label = "MIRAI_GREETH_FLOOD"
    row_id = "a" * 64
    salt = 730201
    sql = pseudo_domain_sql(sql_string(label), sql_string(row_id), manifest, salt)
    actual = _query_scalar(f"SELECT {sql}")
    expected_hash = hashlib.sha256(
        framed_bytes(SeedDerivationLabel.PSEUDO_DOMAIN_HASH, manifest, label, row_id, salt)
    ).digest()
    expected_domain = int.from_bytes(expected_hash[:8], byteorder="big") % PSEUDO_DOMAIN_COUNT
    assert actual == expected_domain


def test_native_sql_pseudo_domain_is_deterministic_and_in_range() -> None:
    sql = pseudo_domain_sql(sql_string("BACKDOOR_MALWARE"), sql_string("b" * 64), "a" * 64, 730201)
    first = _query_scalar(f"SELECT {sql}")
    second = _query_scalar(f"SELECT {sql}")
    assert isinstance(first, int)
    assert isinstance(second, int)
    assert first == second
    assert 0 <= first < PSEUDO_DOMAIN_COUNT


def test_native_sql_sampling_digest_matches_python() -> None:
    manifest = "f" * 64
    label = "MIRAI_GREETH_FLOOD"
    domain = CICIoT2023PseudoDomain.PSEUDO_DOMAIN_4
    row_id = "a" * 64
    expected = hashlib.sha256(
        framed_bytes(
            manifest,
            domain.display_token,
            label,
            Role.REPORT_TEST.name,
            row_id,
            PREPROCESSING_SAMPLE_ORDER_SEED,
        )
    ).digest()
    sql = sampling_digest_sql(
        manifest,
        sql_string(label),
        str(int(domain)),
        sql_string(Role.REPORT_TEST.name),
        sql_string(row_id),
    )
    actual = _query_scalar(f"SELECT {sql}")
    assert actual == expected


def test_resolve_predictor_columns_excludes_validated_row_identifier() -> None:
    header = ("index", "feature_a", "feature_b", "Label")
    predictors = resolve_predictor_columns(header, "Label", frozenset({"index"}))
    assert predictors == ("feature_a", "feature_b")


def test_resolve_predictor_columns_keeps_identifier_like_predictor_when_not_validated() -> None:
    header = ("index", "feature_a", "Label")
    predictors = resolve_predictor_columns(header, "Label")
    assert predictors == ("index", "feature_a")


def _write_csv(path: Path, header: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> None:
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _secondary_csv_file(path: Path, label_column: str = "Label") -> SecondaryCsvFile:
    return SecondaryCsvFile(
        absolute_path=path,
        relative_path=path.name,
        file_sha256=compute_file_checksum(path),
        label_column=label_column,
    )


def _per_attack_csv_file(path: Path, shard_class: str) -> SecondaryCsvFile:
    return SecondaryCsvFile(
        absolute_path=path,
        relative_path=f"{path.parent.name}/{path.name}",
        file_sha256=compute_file_checksum(path),
        shard_class=shard_class,
    )


def test_complete_case_parsing_records_unparseable_and_nonfinite_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "part.csv"
    _write_csv(
        csv_path,
        ("feature_a", "feature_b", "Label"),
        (
            ("1.0", "2.0", "BenignTraffic"),
            ("bad", "3.0", "Backdoor_Malware"),
            ("inf", "4.0", "Backdoor_Malware"),
        ),
    )
    summary = materialize_ciciot2023_prepared_views(
        (_secondary_csv_file(csv_path),),
        tmp_path / "prepared",
        tmp_path / "scaler",
        tmp_path / "metadata",
        tmp_path / "cache",
        overwrite=True,
    )
    assert summary.raw_row_count == 3
    assert summary.retained_row_count == 1
    assert summary.excluded_row_count == 2
    connection = duckdb.connect()
    exclusion_path = tmp_path / "metadata" / "dataset_exclusions.parquet"
    exclusions = connection.execute(
        "SELECT original_row_index, reason FROM read_parquet(?) ORDER BY original_row_index",
        [exclusion_path.as_posix()],
    ).fetchall()
    assert tuple(int(row[0]) for row in exclusions) == (1, 2)
    assert tuple(str(row[1]) for row in exclusions) == (
        DatasetExclusionReason.UNPARSEABLE_PREDICTOR,
        DatasetExclusionReason.NON_FINITE_PREDICTOR,
    )
    staging = duckdb.connect(str(tmp_path / "cache" / "ciciot2023_preparation.duckdb"))
    constraints = staging.execute(
        "SELECT table_name, constraint_type FROM duckdb_constraints() "
        "WHERE table_name IN ('retained', 'exclusions', 'role_assignments')"
    ).fetchall()
    staging.close()
    assert not any(str(row[1]) == "PRIMARY KEY" for row in constraints)


def test_materialization_replaces_interrupted_staging_database(tmp_path: Path) -> None:
    csv_path = tmp_path / "part.csv"
    _write_csv(
        csv_path,
        ("feature_a", "feature_b", "Label"),
        (
            ("1.0", "2.0", "BenignTraffic"),
            ("3.0", "4.0", "Backdoor_Malware"),
        ),
    )
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    interrupted_database = cache_root / "ciciot2023_preparation.duckdb"
    interrupted = duckdb.connect(str(interrupted_database))
    interrupted.execute("CREATE TABLE retained (stable_row_id VARCHAR)")
    interrupted.close()

    summary = materialize_ciciot2023_prepared_views(
        (_secondary_csv_file(csv_path),),
        tmp_path / "prepared",
        tmp_path / "scaler",
        tmp_path / "metadata",
        cache_root,
    )

    assert summary.retained_row_count == 2


def test_per_attack_shard_takes_its_class_from_the_directory_token(tmp_path: Path) -> None:
    target_directory = tmp_path / "Backdoor_Malware"
    benign_directory = tmp_path / "Benign_Final"
    target_directory.mkdir()
    benign_directory.mkdir()
    target_csv = target_directory / "part.csv"
    benign_csv = benign_directory / "part.csv"
    _write_csv(
        target_csv,
        ("feature_a", "feature_b"),
        (("1.0", "2.0"), ("3.0", "4.0"), ("5.0", "6.0"), ("7.0", "8.0")),
    )
    _write_csv(
        benign_csv,
        ("feature_a", "feature_b"),
        tuple((f"{index}.0", f"{index + 1}.0") for index in range(200)),
    )
    summary = materialize_ciciot2023_prepared_views(
        (
            _per_attack_csv_file(target_csv, TARGET_LABEL),
            _per_attack_csv_file(benign_csv, "BENIGN"),
        ),
        tmp_path / "prepared",
        tmp_path / "scaler",
        tmp_path / "metadata",
        tmp_path / "cache",
        overwrite=True,
    )
    assert summary.raw_row_count == 204
    assert summary.retained_row_count == 204
    assert summary.class_registry == (BENIGN_LABEL, TARGET_LABEL)
    assert summary.predictor_columns == ("feature_a", "feature_b")
    anchor_train_rows = sum(
        view.row_count
        for view in summary.views
        if view.role is Role.ANCHOR_TRAIN and view.normalized_label != TARGET_LABEL
    )
    assert summary.scaler.training_row_count == anchor_train_rows


def test_shard_without_any_class_label_source_is_rejected(tmp_path: Path) -> None:
    csv_path = tmp_path / "part.csv"
    _write_csv(csv_path, ("feature_a", "Label"), (("1.0", "BENIGN"),))
    try:
        materialize_ciciot2023_prepared_views(
            (
                SecondaryCsvFile(
                    absolute_path=csv_path,
                    relative_path=csv_path.name,
                    file_sha256="a" * 64,
                ),
            ),
            tmp_path / "prepared",
            tmp_path / "scaler",
            tmp_path / "metadata",
            tmp_path / "cache",
            overwrite=True,
        )
    except ValueError as error:
        assert "no class label source" in str(error)
    else:
        raise AssertionError("a CIC shard without a class label source was accepted")


def test_complete_case_parsing_rejects_mismatched_row_width(tmp_path: Path) -> None:
    csv_path = tmp_path / "part.csv"
    _write_csv(
        csv_path,
        ("feature_a", "feature_b", "Label"),
        (
            ("1.0", "2.0", "BenignTraffic"),
            ("1.0",),
            ("3.0", "4.0", "Backdoor_Malware"),
        ),
    )
    try:
        materialize_ciciot2023_prepared_views(
            (_secondary_csv_file(csv_path),),
            tmp_path / "prepared",
            tmp_path / "scaler",
            tmp_path / "metadata",
            tmp_path / "cache",
            overwrite=True,
        )
    except ValueError as error:
        assert "row width" in str(error)
    else:
        raise AssertionError("mismatched CIC row width was accepted")


def test_assign_roles_uses_target_windows_for_the_target_label(tmp_path: Path) -> None:
    database_path = tmp_path / "target.duckdb"
    _seed_retained(database_path, TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 1000)
    assign_secondary_roles(database_path, "b" * 64)
    roles_seen = frozenset(_roles_by_stable_row_id(database_path).values())
    assert roles_seen.issubset(
        frozenset(
            (
                Role.SOURCE_PROPOSAL,
                Role.CANDIDATE_SCREEN,
                Role.REPRODUCTION,
                Role.ROW_VERIFICATION,
                Role.FINAL_GATE,
                Role.REPORT_TEST,
            )
        )
    )
    assert Role.ANCHOR_TRAIN not in roles_seen


def test_assign_roles_uses_supported_windows_for_other_labels(tmp_path: Path) -> None:
    database_path = tmp_path / "supported.duckdb"
    _seed_retained(database_path, "DDOS_SYN_FLOOD", CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 1000)
    assign_secondary_roles(database_path, "b" * 64)
    roles_seen = frozenset(_roles_by_stable_row_id(database_path).values())
    assert roles_seen.issubset(
        frozenset(
            (
                Role.ANCHOR_TRAIN,
                Role.ANCHOR_VALIDATION,
                Role.POST_REFERENCE_REPLAY,
                Role.ROW_VERIFICATION,
                Role.FINAL_GATE,
                Role.REPORT_TEST,
            )
        )
    )
    assert Role.SOURCE_PROPOSAL not in roles_seen


def test_assign_roles_has_guard_gap_at_boundary(tmp_path: Path) -> None:
    database_path = tmp_path / "guard-gap.duckdb"
    _seed_retained(database_path, TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 1000)
    assign_secondary_roles(database_path, "b" * 64)
    roles = _roles_by_stable_row_id(database_path)
    assert f"{145:064x}" not in roles
    assert roles[f"{144:064x}"] is Role.SOURCE_PROPOSAL
    assert roles[f"{150:064x}"] is Role.CANDIDATE_SCREEN


def test_assign_roles_is_deterministic(tmp_path: Path) -> None:
    first_path = tmp_path / "first.duckdb"
    second_path = tmp_path / "second.duckdb"
    _seed_retained(first_path, TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 200)
    _seed_retained(second_path, TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 200)
    assign_secondary_roles(first_path, "b" * 64)
    assign_secondary_roles(second_path, "b" * 64)
    assert _roles_by_stable_row_id(first_path) == _roles_by_stable_row_id(second_path)


def test_assign_roles_respects_sampling_cap_and_assigns_each_row_at_most_once(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "capped.duckdb"
    _seed_retained(database_path, TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 20000)
    assign_secondary_roles(database_path, "b" * 64)
    roles = _roles_by_stable_row_id(database_path)
    candidate_screen_ids = tuple(
        stable_row_id for stable_row_id, role in roles.items() if role is Role.CANDIDATE_SCREEN
    )
    expected_cap = CONFIG.datasets.primary.sampling_caps_per_domain.candidate_screen_target
    assert len(candidate_screen_ids) == expected_cap
    assert len(set(candidate_screen_ids)) == len(candidate_screen_ids)
    assert len(roles) == len(set(roles))


def test_resolve_row_identifier_columns_accepts_zero_based_sequence(tmp_path: Path) -> None:
    path = tmp_path / "part.csv"
    _write_csv(
        path,
        ("INDEX", "feature_a", "Label"),
        (("0", "1.0", "BenignTraffic"), ("1", "2.0", "BenignTraffic")),
    )
    identifiers = resolve_row_identifier_columns(
        (_secondary_csv_file(path),), ("INDEX", "feature_a", "Label"), "Label"
    )
    assert identifiers == frozenset({"INDEX"})


def test_resolve_row_identifier_columns_accepts_one_based_sequence(tmp_path: Path) -> None:
    path = tmp_path / "part.csv"
    _write_csv(
        path,
        ("ROW_ID", "feature_a", "Label"),
        (("1", "1.0", "BenignTraffic"), ("2", "2.0", "BenignTraffic")),
    )
    identifiers = resolve_row_identifier_columns(
        (_secondary_csv_file(path),), ("ROW_ID", "feature_a", "Label"), "Label"
    )
    assert identifiers == frozenset({"ROW_ID"})


def test_resolve_row_identifier_columns_rejects_non_identifier_names(tmp_path: Path) -> None:
    path = tmp_path / "part.csv"
    _write_csv(
        path,
        ("PROTOCOL", "feature_a", "Label"),
        (("0", "1.0", "BenignTraffic"), ("1", "2.0", "BenignTraffic")),
    )
    identifiers = resolve_row_identifier_columns(
        (_secondary_csv_file(path),), ("PROTOCOL", "feature_a", "Label"), "Label"
    )
    assert identifiers == frozenset()


def test_resolve_row_identifier_columns_rejects_non_sequential_values(tmp_path: Path) -> None:
    path = tmp_path / "part.csv"
    _write_csv(
        path,
        ("INDEX", "feature_a", "Label"),
        (("0", "1.0", "BenignTraffic"), ("2", "2.0", "BenignTraffic")),
    )
    identifiers = resolve_row_identifier_columns(
        (_secondary_csv_file(path),), ("INDEX", "feature_a", "Label"), "Label"
    )
    assert identifiers == frozenset()


def test_resolve_row_identifier_columns_rejects_duplicate_values(tmp_path: Path) -> None:
    path = tmp_path / "part.csv"
    _write_csv(
        path,
        ("INDEX", "feature_a", "Label"),
        (("0", "1.0", "BenignTraffic"), ("0", "2.0", "BenignTraffic")),
    )
    identifiers = resolve_row_identifier_columns(
        (_secondary_csv_file(path),), ("INDEX", "feature_a", "Label"), "Label"
    )
    assert identifiers == frozenset()


def test_truncated_final_line_is_excluded_with_a_recorded_reason(tmp_path: Path) -> None:
    target_directory = tmp_path / "Backdoor_Malware"
    benign_directory = tmp_path / "Benign_Final"
    target_directory.mkdir()
    benign_directory.mkdir()
    target_csv = target_directory / "part.csv"
    benign_csv = benign_directory / "part.csv"
    _write_csv(
        target_csv,
        ("feature_a", "feature_b"),
        (("1.0", "2.0"), ("3.0", "4.0"), ("5.0", "6.0"), ("7.0", "8.0")),
    )
    with target_csv.open("a", encoding="utf-8") as handle:
        handle.write("9.0,10.0,11.0\n")
    with target_csv.open("a", encoding="utf-8") as handle:
        handle.write("truncated\n")
    _write_csv(
        benign_csv,
        ("feature_a", "feature_b"),
        tuple((f"{index}.0", f"{index + 1}.0") for index in range(200)),
    )
    summary = materialize_ciciot2023_prepared_views(
        (
            _per_attack_csv_file(target_csv, TARGET_LABEL),
            _per_attack_csv_file(benign_csv, "BENIGN"),
        ),
        tmp_path / "prepared",
        tmp_path / "scaler",
        tmp_path / "metadata",
        tmp_path / "cache",
        overwrite=True,
    )
    assert summary.raw_row_count == 206
    assert summary.retained_row_count == 204
    exclusions = (
        duckdb.connect()
        .execute(
            "SELECT original_row_index, reason FROM read_parquet(?) ORDER BY original_row_index",
            [(tmp_path / "metadata" / "dataset_exclusions.parquet").as_posix()],
        )
        .fetchall()
    )
    assert tuple((int(row[0]), str(row[1])) for row in exclusions) == (
        (4, DatasetExclusionReason.ROW_WIDTH_MISMATCH),
        (5, DatasetExclusionReason.ROW_WIDTH_MISMATCH),
    )


def test_changed_raw_manifest_rebuilds_existing_prepared_views(tmp_path: Path) -> None:
    benign_directory = tmp_path / "Benign_Final"
    benign_directory.mkdir()
    target_directory = tmp_path / "Backdoor_Malware"
    target_directory.mkdir()
    benign_csv = benign_directory / "part.csv"
    rows = tuple((f"{index}.0", f"{index + 1}.0") for index in range(2000))
    _write_csv(benign_csv, ("feature_a", "feature_b"), rows)
    target_csv = target_directory / "part.csv"
    _write_csv(target_csv, ("feature_a", "feature_b"), rows)
    prepared_root = tmp_path / "prepared"
    scaler_root = tmp_path / "scaler"
    metadata_root = tmp_path / "metadata"
    cache_root = tmp_path / "cache"
    first = materialize_ciciot2023_prepared_views(
        (
            _per_attack_csv_file(target_csv, "BACKDOOR_MALWARE"),
            _per_attack_csv_file(benign_csv, "BENIGN"),
        ),
        prepared_root,
        scaler_root,
        metadata_root,
        cache_root,
        overwrite=True,
    )
    assert first.views
    first_view = first.views[0]
    sidecar_path = first_view.parquet_path.with_suffix(".json")
    first_metadata = CICIoTPreparedViewMetadata.model_validate_json(sidecar_path.read_text())

    changed_rows = (("9000.0", rows[0][1]), *rows[1:])
    _write_csv(benign_csv, ("feature_a", "feature_b"), changed_rows)
    second = materialize_ciciot2023_prepared_views(
        (
            _per_attack_csv_file(target_csv, "BACKDOOR_MALWARE"),
            _per_attack_csv_file(benign_csv, "BENIGN"),
        ),
        prepared_root,
        scaler_root,
        metadata_root,
        cache_root,
    )
    second_view = next(
        view
        for view in second.views
        if (view.pseudo_domain, view.normalized_label, view.role)
        == (first_view.pseudo_domain, first_view.normalized_label, first_view.role)
    )
    updated_metadata = CICIoTPreparedViewMetadata.model_validate_json(sidecar_path.read_text())
    assert second_view.parquet_path == first_view.parquet_path
    assert updated_metadata.cache_identity != first_metadata.cache_identity
    assert updated_metadata.parquet_sha256 != first_metadata.parquet_sha256
