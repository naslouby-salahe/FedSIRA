import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.learning.aggregation import model_parameter, model_state_from_classifier
from fedsira.learning.federated import (
    LocalTrainingClient,
    run_fedavg_round,
    train_one_client_locally,
)
from fedsira.models.mlp import FedSIRAClassifier

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
OPTIMIZER_CONFIG = CONFIG.model.optimizer
TRAINING_CONFIG = CONFIG.model.training


def _global_state():
    return model_state_from_classifier(FedSIRAClassifier(input_width=4, output_width=2))


def _client_data(seed: int = 1) -> LocalTrainingClient:
    return LocalTrainingClient(
        features=torch.randn(6, 4),
        labels=torch.randint(0, 2, (6,)),
        sample_ids=tuple(f"sample-{index}" for index in range(6)),
        training_seed=seed,
    )


def test_train_one_client_locally_returns_typed_state_and_example_count() -> None:
    trained = train_one_client_locally(
        _global_state(),
        4,
        2,
        OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate,
        OPTIMIZER_CONFIG,
        TRAINING_CONFIG,
        local_epochs=1,
        client=_client_data(),
    )
    assert trained.example_count == 6
    assert tuple(parameter.name for parameter in trained.state.parameters) == tuple(
        parameter.name for parameter in _global_state().parameters
    )


def test_run_fedavg_round_produces_full_typed_model_state() -> None:
    global_state = _global_state()
    averaged = run_fedavg_round(
        global_state,
        4,
        2,
        OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate,
        OPTIMIZER_CONFIG,
        TRAINING_CONFIG,
        local_epochs=1,
        clients=(_client_data(1), _client_data(2), _client_data(3)),
    )
    assert tuple(parameter.name for parameter in averaged.parameters) == tuple(
        parameter.name for parameter in global_state.parameters
    )


def test_run_fedavg_round_changes_global_parameters() -> None:
    global_state = _global_state()
    averaged = run_fedavg_round(
        global_state,
        4,
        2,
        OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate,
        OPTIMIZER_CONFIG,
        TRAINING_CONFIG,
        local_epochs=1,
        clients=(_client_data(1), _client_data(2)),
    )
    assert any(
        not torch.allclose(
            model_parameter(averaged, parameter.name).value,
            parameter.value,
        )
        for parameter in global_state.parameters
    )
