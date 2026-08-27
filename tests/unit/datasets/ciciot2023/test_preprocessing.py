from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.ciciot2023.preprocessing import (
    SecondaryRawRow,
    SecondaryRetainedRow,
    apply_secondary_sampling_cap,
    assign_group_local_roles,
    assign_pseudo_domains,
    assign_secondary_roles,
    compute_stable_row_id,
    order_group_by_stable_row_id,
    parse_complete_case_rows,
    resolve_predictor_columns,
)
from fedsira.datasets.ciciot2023.schema import (
    BENIGN_LABEL,
    PSEUDO_DOMAIN_COUNT,
    TARGET_LABEL,
    CICIoT2023PseudoDomain,
)
from fedsira.datasets.common import DatasetExclusionReason, Role

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
ROLE_INTERVALS = CONFIG.datasets.primary.role_intervals


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
        SecondaryRawRow(0, ("1.0", "2.0", "BenignTraffic")),
        SecondaryRawRow(1, ("bad", "3.0", "Backdoor_Malware")),
        SecondaryRawRow(2, ("inf", "4.0", "Backdoor_Malware")),
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
    assert retained[0].canonical_label == BENIGN_LABEL
    assert retained[0].original_row_index == 0
    assert [row.original_row_index for row in exclusions] == [1, 2]
    assert [row.reason for row in exclusions] == [
        DatasetExclusionReason.UNPARSEABLE_PREDICTOR,
        DatasetExclusionReason.NON_FINITE_PREDICTOR,
    ]


def test_complete_case_parsing_rejects_mismatched_row_width() -> None:
    raw_rows = (SecondaryRawRow(7, ("1.0", "BenignTraffic")),)
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


def test_assign_pseudo_domains_returns_closed_domain_values() -> None:
    domains = assign_pseudo_domains(
        "a" * 64,
        TARGET_LABEL,
        ("b" * 64, "c" * 64),
        CONFIG.datasets.secondary.pseudo_domain_partition_salt,
    )
    assert len(domains) == 2
    assert all(isinstance(domain, CICIoT2023PseudoDomain) for domain in domains)
    assert all(0 <= int(domain) < PSEUDO_DOMAIN_COUNT for domain in domains)


def test_assign_pseudo_domains_is_deterministic() -> None:
    args = (
        "a" * 64,
        TARGET_LABEL,
        ("b" * 64,),
        CONFIG.datasets.secondary.pseudo_domain_partition_salt,
    )
    assert assign_pseudo_domains(*args) == assign_pseudo_domains(*args)


def test_order_group_by_stable_row_id_sorts_ascending_by_byte_value() -> None:
    ids = ("c" * 64, "a" * 64, "b" * 64)
    assert order_group_by_stable_row_id(ids) == ("a" * 64, "b" * 64, "c" * 64)


def test_assign_group_local_roles_uses_target_windows_for_the_target_label() -> None:
    ids = tuple(f"{i:064d}" for i in range(1000))
    roles = assign_group_local_roles(TARGET_LABEL, ids, ROLE_INTERVALS)
    roles_seen = {role for role in roles if role is not None}
    assert roles_seen.issubset(
        {
            Role.SOURCE_PROPOSAL,
            Role.CANDIDATE_SCREEN,
            Role.REPRODUCTION,
            Role.ROW_VERIFICATION,
            Role.FINAL_GATE,
            Role.REPORT_TEST,
        }
    )
    assert Role.ANCHOR_TRAIN not in roles_seen


def test_assign_group_local_roles_uses_supported_windows_for_other_labels() -> None:
    ids = tuple(f"{i:064d}" for i in range(1000))
    roles = assign_group_local_roles("DDOS_SYN_FLOOD", ids, ROLE_INTERVALS)
    roles_seen = {role for role in roles if role is not None}
    assert roles_seen.issubset(
        {
            Role.ANCHOR_TRAIN,
            Role.ANCHOR_VALIDATION,
            Role.POST_REFERENCE_REPLAY,
            Role.ROW_VERIFICATION,
            Role.FINAL_GATE,
            Role.REPORT_TEST,
        }
    )
    assert Role.SOURCE_PROPOSAL not in roles_seen


def test_assign_group_local_roles_has_guard_gap_at_boundary() -> None:
    ids = tuple(f"{i:064d}" for i in range(1000))
    roles = assign_group_local_roles(TARGET_LABEL, ids, ROLE_INTERVALS)
    assert roles[145] is None
    assert roles[144] is Role.SOURCE_PROPOSAL
    assert roles[150] is Role.CANDIDATE_SCREEN


def test_assign_group_local_roles_is_deterministic() -> None:
    ids = tuple(f"{i:064d}" for i in range(200))
    first = assign_group_local_roles(TARGET_LABEL, ids, ROLE_INTERVALS)
    second = assign_group_local_roles(TARGET_LABEL, ids, ROLE_INTERVALS)
    assert first == second


def test_secondary_sampling_cap_is_deterministic_and_exact() -> None:
    stable_row_ids = tuple(f"{index:064x}" for index in range(2000))
    first = apply_secondary_sampling_cap(
        "a" * 64,
        TARGET_LABEL,
        CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1,
        Role.CANDIDATE_SCREEN,
        stable_row_ids,
        1000,
    )
    second = apply_secondary_sampling_cap(
        "a" * 64,
        TARGET_LABEL,
        CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1,
        Role.CANDIDATE_SCREEN,
        stable_row_ids,
        1000,
    )
    assert len(first) == 1000
    assert first == second
    assert len(set(first)) == len(first)


def test_secondary_role_assignment_never_assigns_one_row_to_multiple_roles() -> None:
    rows = tuple(
        SecondaryRetainedRow(
            stable_row_id=f"{index:064x}",
            file_sha256="a" * 64,
            relative_path="part.csv",
            original_row_index=index,
            canonical_label=TARGET_LABEL,
            pseudo_domain=CICIoT2023PseudoDomain.PSEUDO_DOMAIN_1,
            features=(float(index),),
        )
        for index in range(1000)
    )
    assignments = assign_secondary_roles(
        rows,
        ROLE_INTERVALS,
        CONFIG.datasets.primary.sampling_caps_per_domain,
        "b" * 64,
    )
    assigned_ids = [assignment.stable_row_id for assignment in assignments]
    assert len(assigned_ids) == len(set(assigned_ids))
