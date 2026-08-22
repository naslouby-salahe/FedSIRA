from collections.abc import Sequence

import torch

from fedsira.config.schema import AnchorFedAvgConfig, OptimizerConfig, TrainingConfig
from fedsira.domain.records import CanonicalToken, DerivedSeed, PositiveFloat, PositiveInt
from fedsira.learning.federated import run_fedavg_round
from fedsira.models.mlp import FedSIRAClassifier, trainable_parameter_count


def run_anchor_fedavg_training(
    input_width: PositiveInt,
    output_width: PositiveInt,
    initial_state_dict: dict[str, torch.Tensor],
    learning_rate: PositiveFloat,
    optimizer_config: OptimizerConfig,
    training_config: TrainingConfig,
    anchor_config: AnchorFedAvgConfig,
    clients_per_round: Sequence[
        Sequence[tuple[torch.Tensor, torch.Tensor, Sequence[CanonicalToken], DerivedSeed]]
    ],
) -> tuple[dict[str, torch.Tensor], tuple[dict[str, torch.Tensor], ...]]:
    if len(clients_per_round) != anchor_config.rounds:
        raise ValueError(
            f"expected exactly {anchor_config.rounds} rounds of client data, "
            f"got {len(clients_per_round)}"
        )
    expected_parameter_count = trainable_parameter_count(
        FedSIRAClassifier(input_width, output_width)
    )
    observed_parameter_count = sum(tensor.numel() for tensor in initial_state_dict.values())
    if observed_parameter_count != expected_parameter_count:
        raise ValueError(
            f"initial_state_dict has {observed_parameter_count} parameters, expected "
            f"{expected_parameter_count} for input_width={input_width}, "
            f"output_width={output_width}"
        )
    state_dict = initial_state_dict
    round_checkpoints: list[dict[str, torch.Tensor]] = []
    for round_clients in clients_per_round:
        state_dict = run_fedavg_round(
            state_dict,
            input_width,
            output_width,
            learning_rate,
            optimizer_config,
            training_config,
            anchor_config.local_epochs_per_round,
            round_clients,
        )
        round_checkpoints.append(state_dict)
    return round_checkpoints[-1], tuple(round_checkpoints)
