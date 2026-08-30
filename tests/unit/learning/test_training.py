import math

import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.learning.training import (
    build_epoch_batches,
    build_loss_function,
    build_optimizer,
    clip_gradients,
    ordered_minibatches,
    step_optimizer,
    train_epochs_with_deterministic_batch_order,
    train_one_epoch,
)
from fedsira.models.mlp import FedSIRAClassifier

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
OPTIMIZER_CONFIG = CONFIG.model.optimizer
TRAINING_CONFIG = CONFIG.model.training


def test_build_loss_function_has_no_class_weights_or_smoothing() -> None:
    loss_function = build_loss_function()
    assert loss_function.weight is None
    assert loss_function.label_smoothing == 0.0
    assert loss_function.reduction == "mean"


def test_build_optimizer_uses_configured_hyperparameters() -> None:
    model = FedSIRAClassifier(input_width=10, output_width=3)
    optimizer = build_optimizer(
        model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    param_group = optimizer.param_groups[0]
    assert param_group["lr"] == OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate
    assert tuple(param_group["betas"]) == tuple(OPTIMIZER_CONFIG.betas)
    assert param_group["eps"] == OPTIMIZER_CONFIG.epsilon
    assert param_group["weight_decay"] == OPTIMIZER_CONFIG.weight_decay
    assert param_group["amsgrad"] is False
    assert param_group["maximize"] is False
    assert param_group["foreach"] is False
    assert param_group["fused"] is None or param_group["fused"] is False


def test_clip_gradients_bounds_the_global_gradient_norm() -> None:
    model = FedSIRAClassifier(input_width=10, output_width=3)
    logits = model(torch.ones(4, 10) * 1000.0)
    loss = logits.sum()
    loss.backward()
    clip_gradients(model, TRAINING_CONFIG)
    squared_norms = torch.stack(
        [
            parameter.grad.pow(2).sum()
            for parameter in model.parameters()
            if parameter.grad is not None
        ]
    )
    total_norm = torch.sqrt(squared_norms.sum())
    assert total_norm <= TRAINING_CONFIG.gradient_global_l2_clip + 1e-4


def test_ordered_minibatches_covers_every_sample_exactly_once() -> None:
    sample_ids = tuple(f"sample-{i}" for i in range(10))
    batches = ordered_minibatches(42, 0, sample_ids, batch_size=3)
    flattened = tuple(sample_id for batch in batches for sample_id in batch)
    assert set(flattened) == set(sample_ids)
    assert len(flattened) == len(sample_ids)


def test_ordered_minibatches_retains_a_final_partial_batch() -> None:
    sample_ids = tuple(f"sample-{i}" for i in range(10))
    batches = ordered_minibatches(42, 0, sample_ids, batch_size=3)
    assert len(batches) == 4
    assert len(batches[-1]) == 1


def test_ordered_minibatches_is_deterministic() -> None:
    sample_ids = tuple(f"sample-{i}" for i in range(20))
    first = ordered_minibatches(42, 0, sample_ids, batch_size=4)
    second = ordered_minibatches(42, 0, sample_ids, batch_size=4)
    assert first == second


def test_train_one_epoch_reduces_loss_on_separable_synthetic_data() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    optimizer = build_optimizer(
        model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.cat([torch.ones(50, 4) * -1.0, torch.ones(50, 4) * 1.0])
    labels = torch.cat([torch.zeros(50, dtype=torch.long), torch.ones(50, dtype=torch.long)])
    batches = ((features, labels),)

    initial_loss = train_one_epoch(model, optimizer, loss_function, TRAINING_CONFIG, batches)
    final_loss = initial_loss
    for _ in range(20):
        final_loss = train_one_epoch(model, optimizer, loss_function, TRAINING_CONFIG, batches)

    assert final_loss < initial_loss


def test_build_epoch_batches_gathers_the_correct_rows_in_deterministic_order() -> None:
    features = torch.arange(10.0).reshape(10, 1)
    labels = torch.arange(10)
    sample_ids = tuple(f"sample-{i}" for i in range(10))
    batches = build_epoch_batches(features, labels, sample_ids, 42, 0, batch_size=4)
    flattened_labels = torch.cat([labels_batch for _, labels_batch in batches])
    observed = {int(value) for value in flattened_labels}
    assert observed == set(range(10))
    for batch_features, batch_labels in batches:
        assert torch.equal(batch_features.squeeze(-1), batch_labels.to(torch.float32))


def test_build_epoch_batches_differs_across_epochs() -> None:
    features = torch.arange(10.0).reshape(10, 1)
    labels = torch.arange(10)
    sample_ids = tuple(f"sample-{i}" for i in range(10))
    epoch_0 = build_epoch_batches(features, labels, sample_ids, 42, 0, batch_size=4)
    epoch_1 = build_epoch_batches(features, labels, sample_ids, 42, 1, batch_size=4)
    first_batch_matches = torch.equal(epoch_0[0][0], epoch_1[0][0])
    assert not first_batch_matches


def test_train_epochs_with_deterministic_batch_order_runs_the_configured_epoch_count() -> None:
    model = FedSIRAClassifier(input_width=1, output_width=2)
    optimizer = build_optimizer(
        model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.cat([torch.ones(10, 1) * -1.0, torch.ones(10, 1) * 1.0])
    labels = torch.cat([torch.zeros(10, dtype=torch.long), torch.ones(10, dtype=torch.long)])
    sample_ids = tuple(f"sample-{i}" for i in range(20))

    epoch_losses = train_epochs_with_deterministic_batch_order(
        model,
        optimizer,
        loss_function,
        TRAINING_CONFIG,
        features,
        labels,
        sample_ids,
        42,
        local_epochs=3,
    )
    assert len(epoch_losses) == 3


def test_one_batch_forward_backward_remains_finite() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    optimizer = build_optimizer(
        model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(8, 4)
    labels = torch.randint(0, 2, (8,))

    optimizer.zero_grad(set_to_none=True)
    logits = model(features)
    assert torch.isfinite(logits).all()
    loss = loss_function(logits, labels)
    assert math.isfinite(float(loss.detach()))
    loss.backward()
    for parameter in model.parameters():
        assert parameter.grad is not None
        assert torch.isfinite(parameter.grad).all()
    clip_gradients(model, TRAINING_CONFIG)
    step_optimizer(optimizer)
    for parameter in model.parameters():
        assert torch.isfinite(parameter).all()


def test_checkpoint_restore_reproduces_predictions_within_tight_tolerance() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    optimizer = build_optimizer(
        model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(12, 4)
    labels = torch.randint(0, 2, (12,))
    for _ in range(3):
        optimizer.zero_grad(set_to_none=True)
        logits = model(features)
        loss = loss_function(logits, labels)
        loss.backward()
        step_optimizer(optimizer)

    checkpoint = {name: tensor.clone() for name, tensor in model.state_dict().items()}
    model.eval()
    with torch.no_grad():
        original_predictions = model(features).clone()

    restored_model = FedSIRAClassifier(input_width=4, output_width=2)
    restored_model.load_state_dict(checkpoint)
    restored_model.eval()
    with torch.no_grad():
        restored_predictions = restored_model(features)

    assert torch.allclose(original_predictions, restored_predictions, atol=1e-6)


def test_optimizer_state_persists_across_epochs_within_one_invocation() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    optimizer = build_optimizer(
        model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(8, 4)
    labels = torch.randint(0, 2, (8,))
    batches = ((features, labels),)

    train_one_epoch(model, optimizer, loss_function, TRAINING_CONFIG, batches)
    first_parameter = next(model.parameters())
    assert optimizer.state[first_parameter]["step"] == 1

    train_one_epoch(model, optimizer, loss_function, TRAINING_CONFIG, batches)
    assert optimizer.state[first_parameter]["step"] == 2


def test_fresh_optimizer_per_round_resets_adamw_state() -> None:
    model = FedSIRAClassifier(input_width=4, output_width=2)
    stale_optimizer = build_optimizer(
        model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    loss_function = build_loss_function()
    features = torch.randn(8, 4)
    labels = torch.randint(0, 2, (8,))
    train_one_epoch(model, stale_optimizer, loss_function, TRAINING_CONFIG, ((features, labels),))
    assert len(stale_optimizer.state) > 0

    fresh_optimizer = build_optimizer(
        model, OPTIMIZER_CONFIG.anchor_and_standard_fl_learning_rate, OPTIMIZER_CONFIG
    )
    assert len(fresh_optimizer.state) == 0
