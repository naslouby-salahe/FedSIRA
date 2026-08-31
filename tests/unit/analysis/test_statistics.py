from fedsira.evaluation.statistics import (
    enumerate_sign_flip_assignments,
    exact_sign_flip_non_inferiority_p_value,
    exact_sign_flip_two_sided_p_value,
    holm_adjusted_p_values,
)


def test_enumerate_sign_flip_assignments_has_exactly_1024_entries_at_n_10() -> None:
    assignments = enumerate_sign_flip_assignments(10)
    assert len(assignments) == 1024
    assert len(set(assignments)) == 1024


def test_exact_sign_flip_two_sided_p_value_is_one_when_all_differences_are_zero() -> None:
    p_value = exact_sign_flip_two_sided_p_value((0.0,) * 10)
    assert p_value == 1.0


def test_exact_sign_flip_two_sided_p_value_matches_hand_computation_for_n_2() -> None:
    p_value = exact_sign_flip_two_sided_p_value((1.0, 1.0))
    assert abs(p_value - 0.5) < 1e-9


def test_exact_sign_flip_two_sided_p_value_is_small_for_a_strong_consistent_effect() -> None:
    p_value = exact_sign_flip_two_sided_p_value((1.0,) * 10)
    assert abs(p_value - (2 / 1024)) < 1e-9


def test_exact_sign_flip_non_inferiority_p_value_at_zero_margin_matches_upper_tail() -> None:
    p_value = exact_sign_flip_non_inferiority_p_value((1.0,) * 10, margin=0.0)
    assert abs(p_value - (1 / 1024)) < 1e-9


def test_holm_adjusted_p_values_matches_hand_fixture() -> None:
    raw = (("c", 0.01), ("a", 0.04), ("b", 0.03))
    adjusted = holm_adjusted_p_values(raw)
    assert adjusted == (("c", 0.03), ("b", 0.06), ("a", 0.06))


def test_holm_adjusted_p_values_is_monotonic_nondecreasing_in_rank_order() -> None:
    raw = (("a", 0.2), ("b", 0.001), ("c", 0.05), ("d", 0.19))
    adjusted = holm_adjusted_p_values(raw)
    values = tuple(value for _, value in adjusted)
    assert values == tuple(sorted(values))


def test_holm_adjusted_p_value_ties_use_ascending_comparison_name() -> None:
    raw = (("z", 0.02), ("a", 0.02))
    adjusted = holm_adjusted_p_values(raw)
    assert tuple(name for name, _ in adjusted) == ("a", "z")


def test_holm_adjusted_p_values_caps_at_one() -> None:
    adjusted = holm_adjusted_p_values((("a", 0.9), ("b", 0.9)))
    assert all(value <= 1.0 for _, value in adjusted)
