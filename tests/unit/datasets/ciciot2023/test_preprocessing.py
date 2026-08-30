from pathlib import Path

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.ciciot2023.acquisition import SecondaryCsvFile
from fedsira.datasets.ciciot2023.preprocessing import (
    SecondaryPreparationStore,
    SecondaryRawRow,
    SecondaryRetainedRow,
    assign_roles,
    compute_stable_row_id,
    parse_complete_case_rows,
    resolve_predictor_columns,
    resolve_row_identifier_columns,
)
from fedsira.datasets.ciciot2023.schema import (
    BENIGN_LABEL,
    TARGET_LABEL,
    CICIoT2023PseudoDomain,
)
from fedsira.datasets.common import DatasetExclusionReason, Role

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def _store_with_rows(
    database_path: Path,
    label: str,
    domain: CICIoT2023PseudoDomain,
    row_count: int,
) -> SecondaryPreparationStore:
    store = SecondaryPreparationStore(database_path)
    store.reset()
    rows = tuple(
        SecondaryRetainedRow(
            stable_row_id=f"{index:064x}",
            file_sha256="a" * 64,
            relative_path="part.csv",
            original_row_index=index,
            normalized_label=label,
            pseudo_domain=domain,
            features=(float(index),),
        )
        for index in range(row_count)
    )
    store.add_rows(rows, ())
    return store


def _roles_by_stable_row_id(
    store: SecondaryPreparationStore,
) -> dict[str, Role]:
    return {assignment.stable_row_id: assignment.role for assignment in store.iter_role_manifest()}


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


def test_complete_case_parsing_records_unparseable_and_nonfinite_rows() -> None:
    raw_rows = (
        SecondaryRawRow(original_row_index=0, values=("1.0", "2.0", "BenignTraffic")),
        SecondaryRawRow(
            original_row_index=1,
            values=("bad", "3.0", "Backdoor_Malware"),
        ),
        SecondaryRawRow(
            original_row_index=2,
            values=("inf", "4.0", "Backdoor_Malware"),
        ),
    )
    retained, exclusions = parse_complete_case_rows(
        raw_rows,
        header=("feature_a", "feature_b", "Label"),
        relative_path="part.csv",
        file_sha256="a" * 64,
        label_column="Label",
        predictor_columns=("feature_a", "feature_b"),
        dataset_manifest_hash="b" * 64,
        pseudo_domain_partition_salt=CONFIG.datasets.secondary.pseudo_domain_partition_salt,
    )
    assert len(retained) == 1
    assert retained[0].normalized_label == BENIGN_LABEL
    assert retained[0].original_row_index == 0
    assert tuple(row.original_row_index for row in exclusions) == (1, 2)
    assert tuple(row.reason for row in exclusions) == (
        DatasetExclusionReason.UNPARSEABLE_PREDICTOR,
        DatasetExclusionReason.NON_FINITE_PREDICTOR,
    )


def test_complete_case_parsing_rejects_mismatched_row_width() -> None:
    raw_rows = (
        SecondaryRawRow(
            original_row_index=7,
            values=("1.0", "BenignTraffic"),
        ),
    )
    try:
        parse_complete_case_rows(
            raw_rows,
            header=("feature_a", "feature_b", "Label"),
            relative_path="part.csv",
            file_sha256="a" * 64,
            label_column="Label",
            predictor_columns=("feature_a", "feature_b"),
            dataset_manifest_hash="b" * 64,
            pseudo_domain_partition_salt=CONFIG.datasets.secondary.pseudo_domain_partition_salt,
        )
    except ValueError as error:
        assert "row width" in str(error)
    else:
        raise AssertionError("mismatched CIC row width was accepted")


def test_assign_roles_uses_target_windows_for_the_target_label(tmp_path: Path) -> None:
    store = _store_with_rows(
        tmp_path / "target.sqlite3", TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 1000
    )
    assign_roles(store, CONFIG, "b" * 64)
    roles_seen = frozenset(_roles_by_stable_row_id(store).values())
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
    store = _store_with_rows(
        tmp_path / "supported.sqlite3",
        "DDOS_SYN_FLOOD",
        CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1,
        1000,
    )
    assign_roles(store, CONFIG, "b" * 64)
    roles_seen = frozenset(_roles_by_stable_row_id(store).values())
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
    store = _store_with_rows(
        tmp_path / "guard-gap.sqlite3", TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 1000
    )
    assign_roles(store, CONFIG, "b" * 64)
    roles = _roles_by_stable_row_id(store)
    assert f"{145:064x}" not in roles
    assert roles[f"{144:064x}"] is Role.SOURCE_PROPOSAL
    assert roles[f"{150:064x}"] is Role.CANDIDATE_SCREEN


def test_assign_roles_is_deterministic(tmp_path: Path) -> None:
    first_store = _store_with_rows(
        tmp_path / "first.sqlite3", TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 200
    )
    second_store = _store_with_rows(
        tmp_path / "second.sqlite3", TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 200
    )
    assign_roles(first_store, CONFIG, "b" * 64)
    assign_roles(second_store, CONFIG, "b" * 64)
    assert _roles_by_stable_row_id(first_store) == _roles_by_stable_row_id(second_store)


def test_assign_roles_respects_sampling_cap_and_assigns_each_row_at_most_once(
    tmp_path: Path,
) -> None:
    store = _store_with_rows(
        tmp_path / "capped.sqlite3", TARGET_LABEL, CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1, 20000
    )
    assign_roles(store, CONFIG, "b" * 64)
    roles = _roles_by_stable_row_id(store)
    candidate_screen_ids = tuple(
        stable_row_id for stable_row_id, role in roles.items() if role is Role.CANDIDATE_SCREEN
    )
    expected_cap = CONFIG.datasets.primary.sampling_caps_per_domain.candidate_screen_target
    assert len(candidate_screen_ids) == expected_cap
    assert len(set(candidate_screen_ids)) == len(candidate_screen_ids)
    assert len(roles) == len(set(roles))


def _write_csv(path: Path, header: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> None:
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _secondary_csv_file(path: Path) -> SecondaryCsvFile:
    return SecondaryCsvFile(absolute_path=path, relative_path=path.name, file_sha256="a" * 64)


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
