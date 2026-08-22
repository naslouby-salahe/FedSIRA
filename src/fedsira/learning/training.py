from collections.abc import Sequence
from typing import Protocol, cast

import torch
from torch import nn, optim

from fedsira.config.schema import OptimizerConfig, TrainingConfig
from fedsira.domain.records import (
    CanonicalToken,
    DerivedSeed,
    EpochIndex,
    NonNegativeFloat,
    PositiveFloat,
)
from fedsira.models.mlp import FedSIRAClassifier
from fedsira.runtime.determinism import minibatch_order


class _SteppableOptimizer(Protocol):
    def step(self) -> None: ...


def step_optimizer(optimizer: optim.AdamW) -> None:
    cast(_SteppableOptimizer, optimizer).step()


def build_loss_function() -> nn.CrossEntropyLoss:
    return nn.CrossEntropyLoss(weight=None, reduction="mean", label_smoothing=0.0)


def build_optimizer(
    model: FedSIRAClassifier, learning_rate: PositiveFloat, optimizer_config: OptimizerConfig
) -> optim.AdamW:
    return optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        betas=optimizer_config.betas,
        eps=optimizer_config.epsilon,
        weight_decay=optimizer_config.weight_decay,
        amsgrad=False,
        maximize=False,
        capturable=False,
        differentiable=False,
        foreach=False,
        fused=False,
    )


def clip_gradients(model: FedSIRAClassifier, training_config: TrainingConfig) -> None:
    nn.utils.clip_grad_norm_(model.parameters(), max_norm=training_config.gradient_global_l2_clip)


def ordered_minibatches(
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    sample_ids: Sequence[CanonicalToken],
    batch_size: int,
) -> tuple[tuple[CanonicalToken, ...], ...]:
    ordered = minibatch_order(training_seed, epoch, sample_ids)
    return tuple(
        ordered[start : start + batch_size] for start in range(0, len(ordered), batch_size)
    )


def train_one_epoch(
    model: FedSIRAClassifier,
    optimizer: optim.AdamW,
    loss_function: nn.CrossEntropyLoss,
    training_config: TrainingConfig,
    batches: Sequence[tuple[torch.Tensor, torch.Tensor]],
) -> NonNegativeFloat:
    model.train()
    total_loss = 0.0
    for features, labels in batches:
        optimizer.zero_grad(set_to_none=True)
        logits = model(features)
        loss = loss_function(logits, labels)
        loss.backward()
        clip_gradients(model, training_config)
        step_optimizer(optimizer)
        total_loss += float(loss.detach())
    return total_loss / len(batches)


def ordered_batch_indices(
    sample_ids: Sequence[CanonicalToken],
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    batch_size: int,
) -> tuple[torch.Tensor, ...]:
    sample_id_to_index = {sample_id: index for index, sample_id in enumerate(sample_ids)}
    ordered_batches = ordered_minibatches(training_seed, epoch, sample_ids, batch_size)
    return tuple(
        torch.tensor([sample_id_to_index[sample_id] for sample_id in batch_sample_ids])
        for batch_sample_ids in ordered_batches
    )


def build_epoch_batches(
    features: torch.Tensor,
    labels: torch.Tensor,
    sample_ids: Sequence[CanonicalToken],
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    batch_size: int,
) -> tuple[tuple[torch.Tensor, torch.Tensor], ...]:
    return tuple(
        (features[indices], labels[indices])
        for indices in ordered_batch_indices(sample_ids, training_seed, epoch, batch_size)
    )


def train_epochs_with_deterministic_batch_order(
    model: FedSIRAClassifier,
    optimizer: optim.AdamW,
    loss_function: nn.CrossEntropyLoss,
    training_config: TrainingConfig,
    features: torch.Tensor,
    labels: torch.Tensor,
    sample_ids: Sequence[CanonicalToken],
    training_seed: DerivedSeed,
    local_epochs: int,
) -> tuple[NonNegativeFloat, ...]:
    epoch_losses: list[NonNegativeFloat] = []
    for epoch in range(local_epochs):
        batches = build_epoch_batches(
            features, labels, sample_ids, training_seed, epoch, training_config.batch_size
        )
        epoch_losses.append(
            train_one_epoch(model, optimizer, loss_function, training_config, batches)
        )
    return tuple(epoch_losses)
