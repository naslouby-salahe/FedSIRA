import torch

from fedsira.attacks.reproduction import (
    scale_model_replacement_delta,
    select_model_replacement_carrier_rows,
    source_copy_update,
    verifier_aware_training_step,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.learning.model import FedSIRAClassifier, flatten_trainable_parameters
from fedsira.learning.training import build_loss_function, build_optimizer
from fedsira.runtime.determinism import seed_job_local_rng_streams

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
OPTIMIZER_CONFIG = CONFIG.model.optimizer
TRAINING_CONFIG = CONFIG.model.training
POST_REFERENCE_CONFIG = CONFIG.model.post_reference
VERIFIER_AWARE_OVERRIDE_CONFIG = CONFIG.model.verifier_aware_backdoor_override


def test_source_copy_update_is_source_minus_baseline() -> None:
    source = torch.tensor([1.0, 2.0, 3.0])
    baseline = torch.tensor([0.5, 0.5, 0.5])
    assert torch.allclose(source_copy_update(source, baseline), torch.tensor([0.5, 1.5, 2.5]))


def test_select_model_replacement_carrier_rows_uses_configured_10_percent() -> None:
    rows = [f"row-{i}" for i in range(30)]
    selected = select_model_replacement_carrier_rows(
        rows,
        CONFIG.attacks_and_boundaries.byzantine_reproduction.model_replacement.poison_fraction,
        42,
    )
    assert selected is not None
    assert len(selected) == 3


def test_scale_model_replacement_delta_uses_configured_scale() -> None:
    delta = torch.tensor([1.0, -1.0, 2.0])
    scaled = scale_model_replacement_delta(
        delta, CONFIG.attacks_and_boundaries.byzantine_reproduction.model_replacement.delta_scale
    )
    assert torch.allclose(scaled, torch.tensor([5.0, -5.0, 10.0]))


def test_verifier_aware_training_step_is_zero_backdoor_loss_without_carrier_rows_in_batch() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(6, 4)
    labels = torch.randint(0, 2, (6,))
    is_supported = torch.zeros(6, dtype=torch.bool)
    anchor_flat = flatten_trainable_parameters(anchor_model).detach()
    parameter_count = sum(p.numel() for p in current_model.parameters())
    triggered_features = torch.randn(6, 4)
    triggered_labels = torch.zeros(6, dtype=torch.long)
    no_carrier_mask = torch.zeros(6, dtype=torch.bool)

    seed_job_local_rng_streams(0)
    with torch.no_grad():
        expected_ce_loss = float(loss_function(current_model(features), labels))

    seed_job_local_rng_streams(0)
    loss = verifier_aware_training_step(
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
        parameter_count,
        triggered_features,
        triggered_labels,
        no_carrier_mask,
        VERIFIER_AWARE_OVERRIDE_CONFIG.triggered_backdoor_loss_weight,
    )
    assert abs(loss - expected_ce_loss) < 1e-6


def test_verifier_aware_training_step_adds_weighted_backdoor_loss_when_carriers_present() -> None:
    anchor_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model = FedSIRAClassifier(input_width=4, output_width=2)
    current_model.load_state_dict(anchor_model.state_dict())
    optimizer = build_optimizer(
        current_model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(6, 4)
    labels = torch.randint(0, 2, (6,))
    is_supported = torch.zeros(6, dtype=torch.bool)
    anchor_flat = flatten_trainable_parameters(anchor_model).detach()
    parameter_count = sum(p.numel() for p in current_model.parameters())
    triggered_features = torch.randn(6, 4)
    triggered_labels = torch.zeros(6, dtype=torch.long)
    carrier_mask = torch.tensor([True, False, False, False, False, False])

    loss = verifier_aware_training_step(
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
        parameter_count,
        triggered_features,
        triggered_labels,
        carrier_mask,
        VERIFIER_AWARE_OVERRIDE_CONFIG.triggered_backdoor_loss_weight,
    )
    assert loss > 0.0
