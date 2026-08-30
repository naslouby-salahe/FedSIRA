import pytest
import torch

from fedsira.learning.aggregation import (
    ModelParameter,
    ModelState,
    WeightedModelState,
    federated_averaging,
)


def _weighted_state(value: float, example_count: int) -> WeightedModelState:
    return WeightedModelState(
        state=ModelState(parameters=(ModelParameter(name="w", value=torch.tensor([value])),)),
        example_count=example_count,
    )


def test_federated_averaging_weights_by_example_count() -> None:
    averaged = federated_averaging((_weighted_state(0.0, 1), _weighted_state(10.0, 9)))
    assert torch.allclose(averaged.parameters[0].value, torch.tensor([9.0]))


def test_federated_averaging_is_a_plain_mean_with_equal_counts() -> None:
    averaged = federated_averaging((_weighted_state(2.0, 1), _weighted_state(4.0, 1)))
    assert torch.allclose(averaged.parameters[0].value, torch.tensor([3.0]))


def test_federated_averaging_rejects_mismatched_parameter_schemas() -> None:
    client_a = WeightedModelState(
        state=ModelState(parameters=(ModelParameter(name="a", value=torch.tensor([1.0])),)),
        example_count=1,
    )
    client_b = WeightedModelState(
        state=ModelState(parameters=(ModelParameter(name="b", value=torch.tensor([2.0])),)),
        example_count=1,
    )
    with pytest.raises(ValueError, match="schemas must match"):
        federated_averaging((client_a, client_b))


def test_federated_averaging_rejects_zero_clients() -> None:
    with pytest.raises(ValueError, match="at least one"):
        federated_averaging(())


def test_federated_averaging_covers_every_parameter_key() -> None:
    client_a = WeightedModelState(
        state=ModelState(
            parameters=(
                ModelParameter(name="a", value=torch.tensor([1.0])),
                ModelParameter(name="b", value=torch.tensor([2.0])),
            )
        ),
        example_count=1,
    )
    client_b = WeightedModelState(
        state=ModelState(
            parameters=(
                ModelParameter(name="a", value=torch.tensor([3.0])),
                ModelParameter(name="b", value=torch.tensor([4.0])),
            )
        ),
        example_count=1,
    )
    averaged = federated_averaging((client_a, client_b))
    assert {parameter.name for parameter in averaged.parameters} == {"a", "b"}
