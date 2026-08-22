import pandas

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.ciciot2023.preprocessing import (
    assign_group_local_roles,
    assign_pseudo_domains,
    compute_stable_row_id,
    order_group_by_stable_row_id,
    resolve_predictor_columns,
)
from fedsira.datasets.ciciot2023.schema import PSEUDO_DOMAIN_COUNT, TARGET_LABEL
from fedsira.datasets.common import Role

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


def test_resolve_predictor_columns_excludes_label_and_true_row_index() -> None:
    header = ("index", "feature_a", "feature_b", "Label")
    sample = pandas.DataFrame({"index": [0, 1, 2], "feature_a": [1.0, 2.0, 3.0]})
    predictors = resolve_predictor_columns(header, "Label", sample)
    assert predictors == ("feature_a", "feature_b")


def test_resolve_predictor_columns_keeps_a_non_sequential_index_like_column() -> None:
    header = ("index", "feature_a", "Label")
    sample = pandas.DataFrame({"index": [5, 1, 9]})
    predictors = resolve_predictor_columns(header, "Label", sample)
    assert "index" in predictors


def test_assign_pseudo_domains_returns_values_within_the_pseudo_domain_count() -> None:
    domains = assign_pseudo_domains("a" * 64, "BACKDOOR_MALWARE", ("b" * 64, "c" * 64), 730201)
    assert len(domains) == 2
    assert all(0 <= domain < PSEUDO_DOMAIN_COUNT for domain in domains)


def test_assign_pseudo_domains_is_deterministic() -> None:
    args = ("a" * 64, "BACKDOOR_MALWARE", ("b" * 64,), 730201)
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


def test_assign_group_local_roles_has_no_guard_gap_at_boundary() -> None:
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
