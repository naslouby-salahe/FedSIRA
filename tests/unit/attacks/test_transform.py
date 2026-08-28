from fedsira.attacks.transform import balanced_50_50_selection


def test_balanced_selection_uses_the_smaller_group_size() -> None:
    group_a = [f"a-{index}" for index in range(10)]
    group_b = [f"b-{index}" for index in range(4)]
    selected_a, selected_b = balanced_50_50_selection(group_a, group_b, 42)
    assert len(selected_a) == 4
    assert len(selected_b) == 4
