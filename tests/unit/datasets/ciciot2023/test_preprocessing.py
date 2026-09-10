from pathlib import Path

import duckdb

from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.ciciot2023.prepare import (
    SecondaryCsvFile,
    assign_secondary_roles,
    compute_stable_row_id,
    materialize_ciciot2023_prepared_views,
    resolve_predictor_columns,
    resolve_row_identifier_columns,
)
from fedsira.datasets.ciciot2023.schema import TARGET_LABEL, CICIoT2023PseudoDomain
from fedsira.datasets.common import DatasetExclusionReason, Role

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


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


def test_compute_stable_row_id_is_a_sha256_hex_digest() -> None:
    digest = compute_stable_row_id("a/b.csv", "a" * 64, 0)
    assert len(digest) == 64
    bytes.fromhex(digest)


def test_compute_stable_row_id_changes_with_row_index() -> None:
    first = compute_stable_row_id("a/b.csv", "a" * 64, 0)
    second = compute_stable_row_id("a/b.csv", "a" * 64, 1)
    assert first != second


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


def _secondary_csv_file(path: Path) -> SecondaryCsvFile:
    return SecondaryCsvFile(absolute_path=path, relative_path=path.name, file_sha256="a" * 64)


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


def test_complete_case_parsing_rejects_mismatched_row_width(tmp_path: Path) -> None:
    csv_path = tmp_path / "part.csv"
    _write_csv(
        csv_path,
        ("feature_a", "feature_b", "Label"),
        (("1.0", "BenignTraffic"),),
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
