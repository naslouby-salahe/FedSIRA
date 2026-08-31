from fedsira.config.schema import AnchorFedAvgConfig, OptimizerConfig, TrainingConfig
from fedsira.domain.records import (
    LearningRate,
    ModelInputWidth,
    ModelOutputWidth,
    PositiveInt,
)
from fedsira.learning.aggregation import ModelState, load_model_state
from fedsira.learning.federated import LocalTrainingClient, run_fedavg_round
from fedsira.models.mlp import FedSIRAClassifier, trainable_parameter_count


def _model_state_parameter_count(state: ModelState) -> PositiveInt:
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
