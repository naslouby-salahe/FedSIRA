import torch

from fedsira.config import AnchorFedAvgConfig, OptimizerConfig, TrainingConfig
from fedsira.domain.types import (
    DerivedSeed,
    ExampleCount,
    LearningRate,
    LocalEpochCount,
    ModelInputWidth,
    ModelOutputWidth,
    SampleId,
    TensorDomainModel,
    TrainableParameterCount,
)
from fedsira.learning.model import FedSIRAClassifier, trainable_parameter_count
from fedsira.learning.training import (
    ModelState,
    WeightedModelState,
    build_loss_function,
    build_optimizer,
    federated_averaging,
    load_model_state,
    model_state_from_classifier,
    train_epochs_with_deterministic_batch_order,
)


class LocalTrainingClient(TensorDomainModel):
    features: torch.Tensor
    labels: torch.Tensor
    sample_ids: tuple[SampleId, ...]
    training_seed: DerivedSeed


def _validate_client_rows(client: LocalTrainingClient) -> ExampleCount:
    feature_rows = client.features.shape[0]
    if feature_rows <= 0:
        raise ValueError("local training requires at least one example")
    if client.labels.shape[0] != feature_rows or len(client.sample_ids) != feature_rows:
        raise ValueError("features, labels, and sample ids must have identical row counts")
    return feature_rows


def train_one_client_locally(
    global_state: ModelState,
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
    learning_rate: LearningRate,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    local_epochs: LocalEpochCount,
    client: LocalTrainingClient,
) -> WeightedModelState:
    example_count = _validate_client_rows(client)
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, global_state)
    optimizer = build_optimizer(model, learning_rate, optimizer_config)
    loss_function = build_loss_function()
    train_epochs_with_deterministic_batch_order(
        model,
        optimizer,
        loss_function,
        training_config,
        client.features,
        client.labels,
        client.sample_ids,
        client.training_seed,
        local_epochs,
    )
    return WeightedModelState(
        state=model_state_from_classifier(model),
        example_count=example_count,
    )


def run_fedavg_round(
    global_state: ModelState,
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
    learning_rate: LearningRate,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    local_epochs: LocalEpochCount,
    clients: tuple[LocalTrainingClient, ...],
) -> ModelState:
    if not clients:
        raise ValueError("FedAvg round requires at least one client")
    trained_clients = tuple(
        train_one_client_locally(
            global_state,
            input_width,
            output_width,
            learning_rate,
            optimizer_config,
            training_config,
            local_epochs,
            client,
        )
        for client in clients
    )
    return federated_averaging(trained_clients)


def _model_state_parameter_count(state: ModelState) -> TrainableParameterCount:
    parameter_count = sum(parameter.value.numel() for parameter in state.parameters)
    if parameter_count <= 0:
        raise ValueError("anchor model state must contain trainable parameters")
    return parameter_count


def run_anchor_fedavg_training(
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
    initial_state: ModelState,
    learning_rate: LearningRate,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    anchor_config: AnchorFedAvgConfig,
    clients_per_round: tuple[tuple[LocalTrainingClient, ...], ...],
) -> tuple[ModelState, tuple[ModelState, ...]]:
    if len(clients_per_round) != anchor_config.rounds:
        raise ValueError(
            f"expected exactly {anchor_config.rounds} rounds of client data, "
            f"got {len(clients_per_round)}"
        )
    expected_parameter_count = trainable_parameter_count(
        FedSIRAClassifier(input_width, output_width)
    )
    observed_parameter_count = _model_state_parameter_count(initial_state)
    if observed_parameter_count != expected_parameter_count:
        raise ValueError(
            f"initial model state has {observed_parameter_count} parameters, expected "
            f"{expected_parameter_count} for input_width={input_width}, "
            f"output_width={output_width}"
        )
    validation_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(validation_model, initial_state)
    state = initial_state
    round_checkpoints: list[ModelState] = []
    for round_clients in clients_per_round:
        state = run_fedavg_round(
            state,
            input_width,
            output_width,
            learning_rate,
            optimizer_config,
            training_config,
            anchor_config.local_epochs_per_round,
            round_clients,
        )
        round_checkpoints.append(state)
    return round_checkpoints[-1], tuple(round_checkpoints)
