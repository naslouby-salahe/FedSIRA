import pytest

from fedsira.datasets.common import (
    EVIDENCE_ROLES,
    TRAINING_AND_SCREENING_ROLES,
    Role,
    RoleWindow,
    compute_sample_id,
    role_for_normalized_position,
)


def role_window(role: Role, lower: float, upper: float) -> RoleWindow:
    return RoleWindow(role=role, lower_inclusive=lower, upper_exclusive=upper)


def test_every_role_name_is_a_round_trip_hash_token() -> None:
    for role in Role:
        token = role.name
        assert token == token.upper()
        assert Role[token] is role


def test_role_hash_tokens_match_roadmap_exactly() -> None:
    assert Role.ANCHOR_TRAIN.name == "ANCHOR_TRAIN"
    assert Role.ANCHOR_VALIDATION.name == "ANCHOR_VALIDATION"
    assert Role.POST_REFERENCE_REPLAY.name == "POST_REFERENCE_REPLAY"
    assert Role.ROW_VERIFICATION.name == "ROW_VERIFICATION"
    assert Role.FINAL_GATE.name == "FINAL_GATE"
    assert Role.REPORT_TEST.name == "REPORT_TEST"
    assert Role.SOURCE_PROPOSAL.name == "SOURCE_PROPOSAL"
    assert Role.CANDIDATE_SCREEN.name == "CANDIDATE_SCREEN"
    assert Role.REPRODUCTION.name == "REPRODUCTION"


def test_unknown_role_hash_token_is_rejected() -> None:
    with pytest.raises(KeyError):
        Role["UNKNOWN_ROLE"]


def test_training_and_evidence_roles_are_disjoint() -> None:
    assert TRAINING_AND_SCREENING_ROLES.isdisjoint(EVIDENCE_ROLES)


def test_role_window_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError, match="lower < upper"):
        role_window(Role.ANCHOR_TRAIN, 0.5, 0.1)


def test_role_window_rejects_out_of_range_bounds() -> None:
    with pytest.raises(ValueError):
        role_window(Role.ANCHOR_TRAIN, -0.1, 0.5)


def test_role_window_contains_is_lower_inclusive_upper_exclusive() -> None:
    window = role_window(Role.ANCHOR_TRAIN, 0.0, 0.395)
    assert window.contains(0.0)
    assert window.contains(0.394999)
    assert not window.contains(0.395)


def test_role_for_normalized_position_finds_matching_window() -> None:
    windows = (
        role_window(Role.ANCHOR_TRAIN, 0.0, 0.395),
        role_window(Role.ANCHOR_VALIDATION, 0.4, 0.495),
    )
    assert role_for_normalized_position(0.1, windows) is Role.ANCHOR_TRAIN
    assert role_for_normalized_position(0.45, windows) is Role.ANCHOR_VALIDATION


def test_role_for_normalized_position_returns_none_in_a_guard_gap() -> None:
    windows = (
        role_window(Role.ANCHOR_TRAIN, 0.0, 0.395),
        role_window(Role.ANCHOR_VALIDATION, 0.4, 0.495),
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
