from collections.abc import Sequence

import torch
from torch import nn, optim

from fedsira.attacks.transform import select_transform_rows
from fedsira.config.schema import PostReferenceConfig, TrainingConfig
from fedsira.domain.records import (
    CanonicalToken,
    NamespaceSeed,
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    Probability,
)
from fedsira.learning.post_reference import compute_delta_l2, compute_stability_kl
from fedsira.learning.training import clip_gradients, step_optimizer
from fedsira.models.mlp import FedSIRAClassifier


def source_copy_update(
    source_flat_parameters: torch.Tensor, baseline_flat_parameters: torch.Tensor
) -> torch.Tensor:
    return source_flat_parameters - baseline_flat_parameters


def select_model_replacement_carrier_rows(
    capped_replay_gafgyt_udp_row_ids: Sequence[CanonicalToken],
    poison_fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[CanonicalToken, ...] | None:
    return select_transform_rows(
        capped_replay_gafgyt_udp_row_ids, poison_fraction, attack_generation_namespace_seed
    )


def scale_model_replacement_delta(delta: torch.Tensor, delta_scale: PositiveFloat) -> torch.Tensor:
    return delta * delta_scale


def verifier_aware_training_step(
    anchor_model: FedSIRAClassifier,
    current_model: FedSIRAClassifier,
    optimizer: optim.AdamW,
    loss_function: nn.CrossEntropyLoss,
    training_config: TrainingConfig,
    post_reference_config: PostReferenceConfig,
    clean_features: torch.Tensor,
    clean_labels: torch.Tensor,
    is_supported: torch.Tensor,
    anchor_flat_parameters: torch.Tensor,
    trainable_parameter_count: PositiveInt,
    triggered_carrier_features: torch.Tensor,
    triggered_carrier_labels: torch.Tensor,
    carrier_row_mask_in_batch: torch.Tensor,
    triggered_backdoor_loss_weight: NonNegativeFloat,
) -> NonNegativeFloat:
    current_model.train()
    optimizer.zero_grad(set_to_none=True)

    current_logits = current_model(clean_features)
    ce_loss = loss_function(current_logits, clean_labels)

    supported_mask = is_supported.bool()
    if bool(supported_mask.any()):
        anchor_model.eval()
        with torch.no_grad():
            anchor_logits = anchor_model(clean_features[supported_mask])
        stability = compute_stability_kl(
            anchor_logits,
            current_logits[supported_mask],
            post_reference_config.stability_kl_temperature,
        )
    else:
        stability = torch.zeros(())

    delta_l2 = compute_delta_l2(current_model, anchor_flat_parameters) / trainable_parameter_count
    legitimate_loss = (
        ce_loss
        + post_reference_config.stability_weight * stability
        + post_reference_config.delta_l2_weight * delta_l2
    )

    carrier_mask = carrier_row_mask_in_batch.bool()
    if bool(carrier_mask.any()):
        triggered_logits = current_model(triggered_carrier_features[carrier_mask])
        triggered_backdoor_loss = loss_function(
            triggered_logits, triggered_carrier_labels[carrier_mask]
        )
    else:
        triggered_backdoor_loss = torch.zeros(())

    total_loss = legitimate_loss + triggered_backdoor_loss_weight * triggered_backdoor_loss
    total_loss.backward()
    clip_gradients(current_model, training_config)
    step_optimizer(optimizer)
    return float(total_loss.detach())
