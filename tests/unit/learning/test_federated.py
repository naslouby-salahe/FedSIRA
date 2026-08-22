import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.learning.federated import run_fedavg_round, train_one_client_locally
from fedsira.models.mlp import FedSIRAClassifier

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
OPTIMIZER_CONFIG = CONFIG.model.optimizer
TRAINING_CONFIG = CONFIG.model.training


def _global_state_dict() -> dict[str, torch.Tensor]:
    return FedSIRAClassifier(input_width=4, output_width=2).state_dict()


def _client_data(seed: int = 1) -> tuple[torch.Tensor, torch.Tensor, tuple[str, ...], int]:
    features = torch.randn(6, 4)
    labels = torch.randint(0, 2, (6,))
    sample_ids = tuple(f"sample-{i}" for i in range(6))
    return features, labels, sample_ids, seed


def test_train_one_client_locally_returns_a_full_state_dict_and_example_count() -> None:
    features, labels, sample_ids, seed = _client_data()
    state_dict, example_count = train_one_client_locally(
        _global_state_dict(),
        4,
        2,
        OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate,
        OPTIMIZER_CONFIG,
        TRAINING_CONFIG,
        local_epochs=1,
        features=features,
        labels=labels,
        sample_ids=sample_ids,
        training_seed=seed,
    )
    assert example_count == 6
    assert set(state_dict.keys()) == set(_global_state_dict().keys())


def test_run_fedavg_round_produces_a_full_state_dict_from_multiple_clients() -> None:
    global_state_dict = _global_state_dict()
    averaged = run_fedavg_round(
        global_state_dict,
        4,
        2,
        OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate,
        OPTIMIZER_CONFIG,
        TRAINING_CONFIG,
        local_epochs=1,
        clients=[_client_data(1), _client_data(2), _client_data(3)],
    )
    assert set(averaged.keys()) == set(global_state_dict.keys())


def test_run_fedavg_round_changes_the_global_parameters() -> None:
    global_state_dict = _global_state_dict()
    averaged = run_fedavg_round(
        global_state_dict,
        4,
        2,
        OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate,
        OPTIMIZER_CONFIG,
        TRAINING_CONFIG,
        local_epochs=1,
        clients=[_client_data(1), _client_data(2)],
    )
    any_parameter_changed = any(
        not torch.allclose(averaged[key], global_state_dict[key]) for key in averaged
    )
    assert any_parameter_changed
