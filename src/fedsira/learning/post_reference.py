from collections.abc import Sequence

import torch
from torch import nn, optim
from torch.nn import functional as torch_functional

from fedsira.config.schema import PostReferenceConfig, TrainingConfig
from fedsira.domain.records import (
    DerivedSeed,
    LocalEpochCount,
    SampleId,
    Temperature,
    TrainableParameterCount,
    TrainingLoss,
)
from fedsira.learning.scoring import logits_for_samples, probabilities_for_samples
from fedsira.learning.training import clip_gradients, ordered_batch_indices, step_optimizer
from fedsira.models.mlp import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    trainable_parameter_count,
)


def compute_stability_kl(
    anchor_logits: torch.Tensor, current_logits: torch.Tensor, temperature: Temperature
) -> torch.Tensor:
    anchor_probs = probabilities_for_samples(anchor_logits / temperature)
    current_log_probs = torch_functional.log_softmax(current_logits / temperature, dim=-1)
    per_example_kl = (anchor_probs * (anchor_probs.log() - current_log_probs)).sum(dim=-1)
    return per_example_kl.mean()


def compute_delta_l2(
    current_model: FedSIRAClassifier, anchor_flat_parameters: torch.Tensor
) -> torch.Tensor:
    current_flat = flatten_trainable_parameters(current_model)
    delta = current_flat - anchor_flat_parameters
    return delta.pow(2).sum()


def post_reference_training_step(
    anchor_model: FedSIRAClassifier,
    current_model: FedSIRAClassifier,
    optimizer: optim.AdamW,
    loss_function: nn.CrossEntropyLoss,
    training_config: TrainingConfig,
    post_reference_config: PostReferenceConfig,
    features: torch.Tensor,
    labels: torch.Tensor,
    is_supported: torch.Tensor,
    anchor_flat_parameters: torch.Tensor,
    trainable_parameter_count: TrainableParameterCount,
) -> TrainingLoss:
    current_model.train()
    optimizer.zero_grad(set_to_none=True)

    current_logits = logits_for_samples(current_model, features, keep_gradients=True)
    ce_loss = loss_function(current_logits, labels)

    supported_mask = is_supported.bool()
    if bool(supported_mask.any()):
        anchor_model.eval()
        with torch.no_grad():
            anchor_logits = anchor_model(features[supported_mask])
        current_supported_logits = current_logits[supported_mask]
        stability = compute_stability_kl(
            anchor_logits,
            current_supported_logits,
            post_reference_config.stability_kl_temperature,
        )
    else:
        stability = torch.zeros(())

    delta_l2 = compute_delta_l2(current_model, anchor_flat_parameters) / trainable_parameter_count

    total_loss = (
        ce_loss
        + post_reference_config.stability_weight * stability
        + post_reference_config.delta_l2_weight * delta_l2
    )
    total_loss.backward()
    clip_gradients(current_model, training_config)
    step_optimizer(optimizer)
    return float(total_loss.detach())


def run_post_reference_training(
    anchor_model: FedSIRAClassifier,
    current_model: FedSIRAClassifier,
    optimizer: optim.AdamW,
    loss_function: nn.CrossEntropyLoss,
    training_config: TrainingConfig,
    post_reference_config: PostReferenceConfig,
    features: torch.Tensor,
    labels: torch.Tensor,
    is_supported: torch.Tensor,
    sample_ids: Sequence[SampleId],
    training_seed: DerivedSeed,
    local_epochs: LocalEpochCount,
) -> tuple[TrainingLoss, ...]:
    anchor_flat_parameters = flatten_trainable_parameters(anchor_model).detach()
    parameter_count = trainable_parameter_count(current_model)
    epoch_losses: list[TrainingLoss] = []
    for epoch in range(local_epochs):
        batch_losses: list[TrainingLoss] = []
        for indices in ordered_batch_indices(
            tuple(sample_ids), training_seed, epoch, training_config.batch_size
        ):
            batch_losses.append(
                post_reference_training_step(
                    anchor_model,
                    current_model,
                    optimizer,
                    loss_function,
                    training_config,
                    post_reference_config,
                    features[indices],
                    labels[indices],
                    is_supported[indices],
                    anchor_flat_parameters,
                    parameter_count,
                )
            )
        epoch_losses.append(sum(batch_losses) / len(batch_losses))
    return tuple(epoch_losses)
