import torch

from fedsira.attacks.source import (
    apply_trigger_transform,
    attack_row_order,
    fraction_to_attack_count,
    relabel_triggered_rows_as_benign,
    select_fractional_attack_rows,
    select_source_backdoor_poison_rows,
)
from fedsira.datasets.nbaiot.schema import NBaiotClass


def test_fraction_to_attack_count_floors() -> None:
    assert fraction_to_attack_count(0.05, 100) == 5
    assert fraction_to_attack_count(0.05, 19) == 0
    assert fraction_to_attack_count(0.1, 25) == 2


def test_attack_row_order_is_deterministic() -> None:
    rows = ["a", "b", "c", "d"]
    first = attack_row_order(rows, 42)
    second = attack_row_order(rows, 42)
    assert first == second
    assert set(first) == set(rows)


def test_fractional_attack_selection_uses_hash_order() -> None:
    rows = [f"row-{index}" for index in range(20)]
    selected = select_fractional_attack_rows(rows, 0.1, 42)
    assert selected is not None
    assert len(selected) == 2
    assert selected == attack_row_order(rows, 42)[:2]


def test_fractional_attack_selection_reports_insufficient_evidence_when_floor_is_zero() -> None:
    rows = [f"row-{index}" for index in range(5)]
    assert select_fractional_attack_rows(rows, 0.05, 42) is None


def test_zero_attack_fraction_selects_no_rows() -> None:
    rows = [f"row-{index}" for index in range(5)]
    assert select_fractional_attack_rows(rows, 0.0, 42) == ()


def test_apply_trigger_transform_sets_only_the_given_indices() -> None:
    features = torch.zeros(3, 5)
    triggered = apply_trigger_transform(features, [1, 3], 6.0)
    expected = torch.tensor([[0.0, 6.0, 0.0, 6.0, 0.0]] * 3)
    assert torch.equal(triggered, expected)
    assert torch.equal(features, torch.zeros(3, 5))


def test_select_source_backdoor_poison_rows_selects_expected_count() -> None:
    rows = [f"row-{index}" for index in range(20)]
    selected = select_source_backdoor_poison_rows(rows, 0.05, 42)
    assert selected is not None
    assert len(selected) == 1


def test_relabel_triggered_rows_as_benign_only_touches_selected_rows() -> None:
    labels = {"a": NBaiotClass.GAFGYT_UDP, "b": NBaiotClass.GAFGYT_UDP, "c": NBaiotClass.BENIGN}
    relabeled = relabel_triggered_rows_as_benign(labels, ["a"])
    assert relabeled["a"] is NBaiotClass.BENIGN
    assert relabeled["b"] is NBaiotClass.GAFGYT_UDP
    assert relabeled["c"] is NBaiotClass.BENIGN
    assert labels["a"] is NBaiotClass.GAFGYT_UDP
