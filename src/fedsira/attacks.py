import math
from collections import OrderedDict
from collections.abc import Mapping, Sequence

import torch
from torch import nn, optim

from fedsira.config import PostReferenceConfig, TrainingConfig
from fedsira.datasets.nbaiot.schema import NBaiotClass
from fedsira.domain.enums import ByzantineVerifierBehavior, SeedNamespace, TernaryOutcome
from fedsira.domain.types import (
    ArtifactDigest,
    AttackCount,
    DeltaScale,
    ExampleCount,
    FeatureIndex,
    LossWeight,
    NamespaceSeed,
    Probability,
    TrainableParameterCount,
    TrainingLoss,
    TriggerFeatureValue,
)
from fedsira.learning.model import FedSIRAClassifier
from fedsira.learning.post_reference import compute_delta_l2, compute_stability_kl
from fedsira.learning.training import clip_gradients, step_optimizer
from fedsira.runtime_execution import deterministic_order

ATTACK_GENERATION_SEPARATOR = SeedNamespace.ATTACK_GENERATION.value


def fraction_to_attack_count(
    fraction: Probability, eligible_population_size: ExampleCount
) -> AttackCount:
    return math.floor(fraction * eligible_population_size)


def attack_row_order(
    eligible_row_ids: Sequence[ArtifactDigest], attack_generation_namespace_seed: NamespaceSeed
) -> tuple[ArtifactDigest, ...]:
    return deterministic_order(
        tuple(eligible_row_ids), ATTACK_GENERATION_SEPARATOR, attack_generation_namespace_seed
    )


def select_fractional_attack_rows(
    eligible_row_ids: Sequence[ArtifactDigest],
    fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    count = fraction_to_attack_count(fraction, len(eligible_row_ids))
    if fraction > 0.0 and count == 0:
        return None
    return attack_row_order(eligible_row_ids, attack_generation_namespace_seed)[:count]


def apply_trigger_transform(
    standardized_features: torch.Tensor,
    trigger_feature_indices: Sequence[FeatureIndex],
    trigger_value: TriggerFeatureValue,
) -> torch.Tensor:
    triggered = standardized_features.clone()
    for feature_index in trigger_feature_indices:
        triggered[..., feature_index] = trigger_value
    return triggered


def select_source_backdoor_poison_rows(
    eligible_gafgyt_udp_row_ids: Sequence[ArtifactDigest],
    poison_fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    return select_fractional_attack_rows(
        eligible_gafgyt_udp_row_ids, poison_fraction, attack_generation_namespace_seed
    )


def relabel_triggered_rows_as_benign(
    labels_by_row_id: Mapping[ArtifactDigest, NBaiotClass],
    poisoned_row_ids: Sequence[ArtifactDigest],
) -> Mapping[ArtifactDigest, NBaiotClass]:
    relabeled: OrderedDict[ArtifactDigest, NBaiotClass] = OrderedDict(labels_by_row_id)
    for row_id in poisoned_row_ids:
        relabeled[row_id] = NBaiotClass.BENIGN
    return relabeled


def source_copy_update(
    source_flat_parameters: torch.Tensor, baseline_flat_parameters: torch.Tensor
) -> torch.Tensor:
    return source_flat_parameters - baseline_flat_parameters


def select_model_replacement_carrier_rows(
    capped_replay_gafgyt_udp_row_ids: Sequence[ArtifactDigest],
    poison_fraction: Probability,
    attack_generation_namespace_seed: NamespaceSeed,
) -> tuple[ArtifactDigest, ...] | None:
    return select_fractional_attack_rows(
        capped_replay_gafgyt_udp_row_ids, poison_fraction, attack_generation_namespace_seed
    )


def scale_model_replacement_delta(delta: torch.Tensor, delta_scale: DeltaScale) -> torch.Tensor:
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
    trainable_parameter_count: TrainableParameterCount,
    triggered_carrier_features: torch.Tensor,
    triggered_carrier_labels: torch.Tensor,
    carrier_row_mask_in_batch: torch.Tensor,
    triggered_backdoor_loss_weight: LossWeight,
) -> TrainingLoss:
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


def resolve_byzantine_verifier_vote(behavior: ByzantineVerifierBehavior) -> TernaryOutcome:
    if behavior is ByzantineVerifierBehavior.FALSE_POSITIVE:
        return TernaryOutcome.POSITIVE
    return TernaryOutcome.NEGATIVE
