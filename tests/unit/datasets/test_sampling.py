from fedsira.datasets.sampling import (
    PREPROCESSING_SAMPLE_ORDER_SEED,
    apply_sampling_cap,
    sampling_cap_selection_digest,
)


def test_preprocessing_sample_order_seed_matches_the_fixed_roadmap_value() -> None:
    assert PREPROCESSING_SAMPLE_ORDER_SEED == 4154850028


def test_sampling_cap_selection_digest_is_deterministic() -> None:
    args = ("a" * 64, "DANMINI_DOORBELL", "GAFGYT_COMBO", "SOURCE_PROPOSAL", 7)
    assert sampling_cap_selection_digest(*args) == sampling_cap_selection_digest(*args)


def test_sampling_cap_selection_digest_changes_with_row_index() -> None:
    base = ("a" * 64, "DANMINI_DOORBELL", "GAFGYT_COMBO", "SOURCE_PROPOSAL")
    first = sampling_cap_selection_digest(*base, 0)
    second = sampling_cap_selection_digest(*base, 1)
    assert first != second


def test_apply_sampling_cap_returns_all_rows_when_under_the_cap() -> None:
    selected = apply_sampling_cap(
        "a" * 64,
        "DANMINI_DOORBELL",
        "GAFGYT_COMBO",
        "SOURCE_PROPOSAL",
        (0, 1, 2),
        cap=10,
    )
    assert set(selected) == {0, 1, 2}


def test_apply_sampling_cap_selects_exactly_the_cap_when_over() -> None:
    selected = apply_sampling_cap(
        "a" * 64,
        "DANMINI_DOORBELL",
        "GAFGYT_COMBO",
        "SOURCE_PROPOSAL",
        tuple(range(100)),
        cap=10,
    )
    assert len(selected) == 10
    assert len(set(selected)) == 10
    assert set(selected).issubset(set(range(100)))


def test_apply_sampling_cap_is_deterministic_across_runs() -> None:
    args = (
        "a" * 64,
        "DANMINI_DOORBELL",
        "GAFGYT_COMBO",
        "SOURCE_PROPOSAL",
        tuple(range(50)),
    )
    first = apply_sampling_cap(*args, cap=5)
    second = apply_sampling_cap(*args, cap=5)
    assert first == second


def test_apply_sampling_cap_selection_differs_by_role_and_class() -> None:
    rows = tuple(range(50))
    source_proposal = apply_sampling_cap(
        "a" * 64,
        "DANMINI_DOORBELL",
        "GAFGYT_COMBO",
        "SOURCE_PROPOSAL",
        rows,
        cap=5,
    )
    candidate_screen = apply_sampling_cap(
        "a" * 64,
        "DANMINI_DOORBELL",
        "GAFGYT_COMBO",
        "CANDIDATE_SCREEN",
        rows,
        cap=5,
    )
    assert set(source_proposal) != set(candidate_screen)
