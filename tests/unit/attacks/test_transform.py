from fedsira.attacks.transform import (
    a_dominant_80_20_selection,
    attack_generation_order,
    balanced_50_50_selection,
    fraction_to_transform_count,
    select_transform_rows,
)


def test_fraction_to_transform_count_floors() -> None:
    assert fraction_to_transform_count(0.05, 100) == 5
    assert fraction_to_transform_count(0.05, 19) == 0
    assert fraction_to_transform_count(0.1, 25) == 2


def test_attack_generation_order_is_deterministic() -> None:
    rows = ["a", "b", "c", "d"]
    first = attack_generation_order(rows, 42)
    second = attack_generation_order(rows, 42)
    assert first == second
    assert set(first) == set(rows)


def test_select_transform_rows_returns_first_m_in_hash_order() -> None:
    rows = [f"row-{i}" for i in range(20)]
    selected = select_transform_rows(rows, 0.1, 42)
    assert selected is not None
    assert len(selected) == 2
    assert selected == attack_generation_order(rows, 42)[:2]


def test_select_transform_rows_is_evidence_insufficient_when_count_rounds_to_zero() -> None:
    rows = [f"row-{i}" for i in range(5)]
    assert select_transform_rows(rows, 0.05, 42) is None


def test_select_transform_rows_zero_fraction_is_not_evidence_insufficient() -> None:
    rows = [f"row-{i}" for i in range(5)]
    result = select_transform_rows(rows, 0.0, 42)
    assert result == ()


def test_balanced_50_50_selection_uses_the_smaller_group_size() -> None:
    group_a = [f"a-{i}" for i in range(10)]
    group_b = [f"b-{i}" for i in range(4)]
    selected_a, selected_b = balanced_50_50_selection(group_a, group_b, 42)
    assert len(selected_a) == 4
    assert len(selected_b) == 4


def test_a_dominant_80_20_selection_uses_4to1_ratio() -> None:
    group_a = [f"a-{i}" for i in range(20)]
    group_b = [f"b-{i}" for i in range(3)]
    selected_a, selected_b = a_dominant_80_20_selection(group_a, group_b, 42)
    assert len(selected_b) == 3
    assert len(selected_a) == 12
