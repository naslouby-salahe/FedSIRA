import torch

from fedsira.attacks.source_backdoor import (
    apply_trigger_transform,
    relabel_triggered_rows_as_benign,
    select_source_backdoor_poison_rows,
)
from fedsira.datasets.nbaiot.schema import NBaiotClass


def test_apply_trigger_transform_sets_only_the_given_indices() -> None:
    features = torch.zeros(3, 5)
    triggered = apply_trigger_transform(features, [1, 3], 6.0)
    expected = torch.tensor([[0.0, 6.0, 0.0, 6.0, 0.0]] * 3)
    assert torch.equal(triggered, expected)
    assert torch.equal(features, torch.zeros(3, 5))


def test_select_source_backdoor_poison_rows_matches_transform_selection() -> None:
    rows = [f"row-{i}" for i in range(20)]
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
