import torch

from fedsira.config.schema import OptimizerConfig, TrainingConfig
from fedsira.domain.records import (
    DerivedSeed,
    LearningRate,
    LocalEpochCount,
    ModelInputWidth,
    ModelOutputWidth,
    PositiveInt,
    SampleId,
    TensorDomainModel,
)
from fedsira.learning.aggregation import (
    ModelState,
    WeightedModelState,
    federated_averaging,
    load_model_state,
    model_state_from_classifier,
)
from fedsira.learning.training import (
    build_loss_function,
    build_optimizer,
    train_epochs_with_deterministic_batch_order,
)
from fedsira.models.mlp import FedSIRAClassifier


class LocalTrainingClient(TensorDomainModel):
    features: torch.Tensor
    labels: torch.Tensor
    sample_ids: tuple[SampleId, ...]
    training_seed: DerivedSeed


def _validate_client_rows(client: LocalTrainingClient) -> PositiveInt:
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
