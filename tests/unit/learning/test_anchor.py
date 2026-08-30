import pytest
import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.learning.aggregation import model_state_from_classifier
from fedsira.learning.anchor import run_anchor_fedavg_training
from fedsira.learning.federated import LocalTrainingClient
from fedsira.models.mlp import FedSIRAClassifier

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
OPTIMIZER_CONFIG = CONFIG.model.optimizer
TRAINING_CONFIG = CONFIG.model.training
ANCHOR_CONFIG = CONFIG.model.anchor_fedavg


def _client_data(seed: int) -> LocalTrainingClient:
    features = torch.randn(6, 4)
    labels = torch.randint(0, 2, (6,))
    sample_ids = tuple(f"sample-{i}" for i in range(6))
    return LocalTrainingClient(
        features=features, labels=labels, sample_ids=sample_ids, training_seed=seed
    )


def test_run_anchor_fedavg_training_requires_exactly_the_configured_round_count() -> None:
    initial_state = model_state_from_classifier(FedSIRAClassifier(4, 2))
    with pytest.raises(ValueError, match=f"exactly {ANCHOR_CONFIG.rounds}"):
        run_anchor_fedavg_training(
            4,
            2,
            initial_state,
            OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate,
            OPTIMIZER_CONFIG,
            TRAINING_CONFIG,
            ANCHOR_CONFIG,
            clients_per_round=((_client_data(1),),),
        )


def test_run_anchor_fedavg_training_returns_a_checkpoint_per_round() -> None:
    initial_state = model_state_from_classifier(FedSIRAClassifier(4, 2))
    rounds = tuple((_client_data(1), _client_data(2)) for _ in range(ANCHOR_CONFIG.rounds))
    final_checkpoint, round_checkpoints = run_anchor_fedavg_training(
        4,
        2,
        initial_state,
        OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate,
        OPTIMIZER_CONFIG,
        TRAINING_CONFIG,
        ANCHOR_CONFIG,
        clients_per_round=rounds,
    )
    assert len(round_checkpoints) == ANCHOR_CONFIG.rounds
    assert final_checkpoint is round_checkpoints[-1]
