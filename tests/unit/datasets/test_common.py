import pytest

from fedsira.datasets.common import (
    EVIDENCE_ROLES,
    ROLE_HASH_TOKEN,
    TRAINING_AND_SCREENING_ROLES,
    Role,
    RoleWindow,
    compute_sample_id,
    role_for_normalized_position,
)


def test_every_role_has_a_hash_token() -> None:
    assert set(ROLE_HASH_TOKEN.keys()) == set(Role)
    assert all(token == token.upper() for token in ROLE_HASH_TOKEN.values())


def test_role_hash_tokens_match_roadmap_exactly() -> None:
    assert ROLE_HASH_TOKEN[Role.ANCHOR_TRAIN] == "ANCHOR_TRAIN"
    assert ROLE_HASH_TOKEN[Role.ANCHOR_VALIDATION] == "ANCHOR_VALIDATION"
    assert ROLE_HASH_TOKEN[Role.POST_REFERENCE_REPLAY] == "POST_REFERENCE_REPLAY"
    assert ROLE_HASH_TOKEN[Role.ROW_VERIFICATION] == "ROW_VERIFICATION"
    assert ROLE_HASH_TOKEN[Role.FINAL_GATE] == "FINAL_GATE"
    assert ROLE_HASH_TOKEN[Role.REPORT_TEST] == "REPORT_TEST"
    assert ROLE_HASH_TOKEN[Role.SOURCE_PROPOSAL] == "SOURCE_PROPOSAL"
    assert ROLE_HASH_TOKEN[Role.CANDIDATE_SCREEN] == "CANDIDATE_SCREEN"
    assert ROLE_HASH_TOKEN[Role.REPRODUCTION] == "REPRODUCTION"


def test_training_and_evidence_roles_are_disjoint() -> None:
    assert TRAINING_AND_SCREENING_ROLES.isdisjoint(EVIDENCE_ROLES)


def test_role_window_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError, match="lower < upper"):
        RoleWindow(Role.ANCHOR_TRAIN, 0.5, 0.1)


def test_role_window_rejects_out_of_range_bounds() -> None:
    with pytest.raises(ValueError):
        RoleWindow(Role.ANCHOR_TRAIN, -0.1, 0.5)


def test_role_window_contains_is_lower_inclusive_upper_exclusive() -> None:
    window = RoleWindow(Role.ANCHOR_TRAIN, 0.0, 0.395)
    assert window.contains(0.0)
    assert window.contains(0.394999)
    assert not window.contains(0.395)


def test_role_for_normalized_position_finds_matching_window() -> None:
    windows = (
        RoleWindow(Role.ANCHOR_TRAIN, 0.0, 0.395),
        RoleWindow(Role.ANCHOR_VALIDATION, 0.4, 0.495),
    )
    assert role_for_normalized_position(0.1, windows) is Role.ANCHOR_TRAIN
    assert role_for_normalized_position(0.45, windows) is Role.ANCHOR_VALIDATION


def test_role_for_normalized_position_returns_none_in_a_guard_gap() -> None:
    windows = (
        RoleWindow(Role.ANCHOR_TRAIN, 0.0, 0.395),
        RoleWindow(Role.ANCHOR_VALIDATION, 0.4, 0.495),
    )
    assert role_for_normalized_position(0.397, windows) is None


def test_compute_sample_id_is_a_sha256_hex_digest() -> None:
    digest = compute_sample_id("PREFIX_V1", "a/b.csv", "a" * 64, 0)
    assert len(digest) == 64
    bytes.fromhex(digest)


def test_compute_sample_id_is_deterministic() -> None:
    args = ("PREFIX_V1", "a/b.csv", "a" * 64, 5)
    assert compute_sample_id(*args) == compute_sample_id(*args)


def test_compute_sample_id_changes_with_row_index() -> None:
    first = compute_sample_id("PREFIX_V1", "a/b.csv", "a" * 64, 0)
    second = compute_sample_id("PREFIX_V1", "a/b.csv", "a" * 64, 1)
    assert first != second
