from collections.abc import Sequence

import torch

from fedsira.config.schema import OptimizerConfig, TrainingConfig
from fedsira.domain.records import SampleId, DerivedSeed, PositiveFloat, PositiveInt
from fedsira.learning.aggregation import federated_averaging
from fedsira.learning.training import (
    build_loss_function,
    build_optimizer,
    train_epochs_with_deterministic_batch_order,
)
from fedsira.models.mlp import FedSIRAClassifier


def train_one_client_locally(
    global_state_dict: dict[str, torch.Tensor],
    input_width: PositiveInt,
    output_width: PositiveInt,
    learning_rate: PositiveFloat,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    local_epochs: PositiveInt,
    features: torch.Tensor,
    labels: torch.Tensor,
    sample_ids: Sequence[SampleId],
    training_seed: DerivedSeed,
) -> tuple[dict[str, torch.Tensor], PositiveInt]:
    model = FedSIRAClassifier(input_width, output_width)
    model.load_state_dict(global_state_dict)
    optimizer = build_optimizer(model, learning_rate, optimizer_config)
    loss_function = build_loss_function()
    train_epochs_with_deterministic_batch_order(
        model,
        optimizer,
        loss_function,
        training_config,
        features,
        labels,
        sample_ids,
        training_seed,
        local_epochs,
    )
    example_count = features.shape[0]
    return model.state_dict(), example_count


def run_fedavg_round(
    global_state_dict: dict[str, torch.Tensor],
    input_width: PositiveInt,
    output_width: PositiveInt,
    learning_rate: PositiveFloat,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    local_epochs: PositiveInt,
    clients: Sequence[tuple[torch.Tensor, torch.Tensor, Sequence[SampleId], DerivedSeed]],
) -> dict[str, torch.Tensor]:
    client_state_dicts: list[dict[str, torch.Tensor]] = []
    client_example_counts: list[PositiveInt] = []
    for features, labels, sample_ids, training_seed in clients:
        state_dict, example_count = train_one_client_locally(
            global_state_dict,
            input_width,
            output_width,
            learning_rate,
            optimizer_config,
            training_config,
            local_epochs,
            features,
            labels,
            sample_ids,
            training_seed,
        )
        client_state_dicts.append(state_dict)
        client_example_counts.append(example_count)
    return federated_averaging(client_state_dicts, client_example_counts)
