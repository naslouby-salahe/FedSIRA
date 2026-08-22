import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.learning.training import (
    build_epoch_batches,
    build_loss_function,
    build_optimizer,
    clip_gradients,
    ordered_minibatches,
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
    batches = [(features, labels)]

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
