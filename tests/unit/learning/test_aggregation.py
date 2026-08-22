import pytest
import torch

from fedsira.learning.aggregation import federated_averaging


def test_federated_averaging_weights_by_example_count() -> None:
    client_a = {"w": torch.tensor([0.0])}
    client_b = {"w": torch.tensor([10.0])}
    averaged = federated_averaging([client_a, client_b], [1, 9])
    assert torch.allclose(averaged["w"], torch.tensor([9.0]))


def test_federated_averaging_is_a_plain_mean_with_equal_counts() -> None:
    client_a = {"w": torch.tensor([2.0])}
    client_b = {"w": torch.tensor([4.0])}
    averaged = federated_averaging([client_a, client_b], [1, 1])
    assert torch.allclose(averaged["w"], torch.tensor([3.0]))


def test_federated_averaging_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="equal length"):
        federated_averaging([{"w": torch.tensor([1.0])}], [1, 2])


def test_federated_averaging_rejects_zero_clients() -> None:
    with pytest.raises(ValueError, match="at least one"):
        federated_averaging([], [])


def test_federated_averaging_covers_every_parameter_key() -> None:
    client_a = {"a": torch.tensor([1.0]), "b": torch.tensor([2.0])}
    client_b = {"a": torch.tensor([3.0]), "b": torch.tensor([4.0])}
    averaged = federated_averaging([client_a, client_b], [1, 1])
    assert set(averaged.keys()) == {"a", "b"}
