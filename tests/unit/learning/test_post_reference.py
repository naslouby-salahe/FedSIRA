import math

import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.learning.model import FedSIRAClassifier, flatten_trainable_parameters
from fedsira.learning.post_reference import (
    compute_delta_l2,
    compute_stability_kl,
    post_reference_training_step,
    run_post_reference_training,
)
from fedsira.learning.training import build_loss_function, build_optimizer
from fedsira.runtime.determinism import seed_job_local_rng_streams

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
OPTIMIZER_CONFIG = CONFIG.model.optimizer
TRAINING_CONFIG = CONFIG.model.training
POST_REFERENCE_CONFIG = CONFIG.model.post_reference


def test_stability_kl_is_zero_when_distributions_match() -> None:
    logits = torch.randn(5, 3)
    kl = compute_stability_kl(logits, logits, temperature=1.0)
    assert abs(float(kl)) < 1e-5


def test_stability_kl_is_positive_when_distributions_differ() -> None:
    anchor_logits = torch.tensor([[10.0, 0.0, 0.0]])
    current_logits = torch.tensor([[0.0, 10.0, 0.0]])
    kl = compute_stability_kl(anchor_logits, current_logits, temperature=1.0)
    assert float(kl) > 1.0


def test_delta_l2_is_zero_when_current_equals_anchor() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    anchor_flat = flatten_trainable_parameters(model).detach().clone()
    delta = compute_delta_l2(model, anchor_flat)
    assert abs(float(delta.detach())) < 1e-9


def test_delta_l2_grows_with_parameter_distance() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    anchor_flat = flatten_trainable_parameters(model).detach().clone() + 1.0
    delta = compute_delta_l2(model, anchor_flat)
    assert float(delta.detach()) > 0.0


def test_post_reference_training_step_with_zero_supported_examples_uses_zero_stability() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.post_reference_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(6, 4)
    labels = torch.randint(0, 2, (6,))
    is_supported = torch.zeros(6, dtype=torch.bool)
    anchor_flat = flatten_trainable_parameters(anchor_model).detach()

    loss = post_reference_training_step(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        anchor_flat,
        trainable_parameter_count=sum(p.numel() for p in current_model.parameters()),
    )
    assert not math.isnan(loss)


def test_post_reference_training_step_zero_supported_matches_ce_and_delta_l2_exactly() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.post_reference_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(6, 4)
    labels = torch.randint(0, 2, (6,))
    is_supported = torch.zeros(6, dtype=torch.bool)
    anchor_flat = flatten_trainable_parameters(anchor_model).detach()
    parameter_count = sum(p.numel() for p in current_model.parameters())

    seed_job_local_rng_streams(0)
    with torch.no_grad():
        expected_ce_loss = float(loss_function(current_model(features), labels))
    expected_delta_l2 = float(
        compute_delta_l2(current_model, anchor_flat).detach() / parameter_count
    )

    seed_job_local_rng_streams(0)
    loss = post_reference_training_step(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        anchor_flat,
        trainable_parameter_count=parameter_count,
    )
    expected_total = expected_ce_loss + POST_REFERENCE_CONFIG.delta_l2_weight * expected_delta_l2
    assert abs(loss - expected_total) < 1e-6


def test_run_post_reference_training_runs_the_configured_epoch_count() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.post_reference_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(10, 4)
    labels = torch.randint(0, 2, (10,))
    is_supported = torch.tensor([True, False] * 5)
    sample_ids = tuple(f"sample-{i}" for i in range(10))

    epoch_losses = run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed=42,
        local_epochs=3,
    )
    assert len(epoch_losses) == 3


def test_run_post_reference_training_moves_parameters_away_from_the_anchor() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.post_reference_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(10, 4)
    labels = torch.randint(0, 2, (10,))
    is_supported = torch.tensor([True, False] * 5)
    sample_ids = tuple(f"sample-{i}" for i in range(10))

    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        POST_REFERENCE_CONFIG,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed=42,
        local_epochs=3,
    )
    anchor_flat = flatten_trainable_parameters(anchor_model)
    current_flat = flatten_trainable_parameters(current_model)
    assert not torch.allclose(anchor_flat, current_flat)
