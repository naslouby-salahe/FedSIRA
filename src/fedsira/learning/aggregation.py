import torch

from fedsira.domain.records import ParameterName, PositiveInt, TensorDomainModel


class ModelParameter(TensorDomainModel):
    name: ParameterName
    value: torch.Tensor


class ModelState(TensorDomainModel):
    parameters: tuple[ModelParameter, ...]


class WeightedModelState(TensorDomainModel):
    state: ModelState
    example_count: PositiveInt


def model_parameter(
    state: ModelState,
    parameter_name: ParameterName,
) -> ModelParameter:
    for parameter in state.parameters:
        if parameter.name == parameter_name:
            return parameter
    raise ValueError(f"model state does not contain parameter {parameter_name}")


def _validate_parameter_schema(client_states: tuple[WeightedModelState, ...]) -> None:
    expected_names = tuple(parameter.name for parameter in client_states[0].state.parameters)
    if not expected_names:
        raise ValueError("federated averaging requires model parameters")
    if len(set(expected_names)) != len(expected_names):
        raise ValueError("model parameter names must be unique")
    for client_state in client_states[1:]:
        observed_names = tuple(parameter.name for parameter in client_state.state.parameters)
        if observed_names != expected_names:
            raise ValueError("client model parameter schemas must match exactly")


def federated_averaging(
    client_states: tuple[WeightedModelState, ...],
) -> ModelState:
    if not client_states:
        raise ValueError("federated averaging requires at least one client update")
    _validate_parameter_schema(client_states)
    total_examples = sum(client_state.example_count for client_state in client_states)
    averaged: list[ModelParameter] = []
    for reference_parameter in client_states[0].state.parameters:
        weighted_sum = torch.zeros_like(reference_parameter.value, dtype=torch.float32)
        for client_state in client_states:
            parameter = model_parameter(client_state.state, reference_parameter.name)
            weighted_sum += parameter.value.to(torch.float32) * (
                client_state.example_count / total_examples
            )
        averaged.append(ModelParameter(name=reference_parameter.name, value=weighted_sum))
    return ModelState(parameters=tuple(averaged))
