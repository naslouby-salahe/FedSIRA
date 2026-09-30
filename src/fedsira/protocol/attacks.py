import torch
from torch import nn, optim

from fedsira.config import PostReferenceConfig, TrainingConfig
from fedsira.domain.enums import ByzantineVerifierBehavior, TernaryOutcome
from fedsira.domain.types import (
    DeltaScale,
    LossWeight,
    ModelInputWidth,
    ModelOutputWidth,
    Probability,
    TrainableParameterCount,
    TrainingLoss,
)
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.learning.post_reference import compute_delta_l2, compute_stability_kl
from fedsira.learning.training import (
    ModelState,
    clip_gradients,
    load_model_state,
    model_state_from_classifier,
    step_optimizer,
)
from fedsira.runtime import current_application_context


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


def source_copy_update(
    source_flat_parameters: torch.Tensor, baseline_flat_parameters: torch.Tensor
) -> torch.Tensor:
    return source_flat_parameters - baseline_flat_parameters


def declared_source_backdoor_poison_fractions() -> tuple[Probability, ...]:
    attacks = current_application_context().scientific_config.attacks_and_boundaries
    return attacks.hidden_source_backdoor.poison_fraction_sweep


def validate_declared_source_backdoor_poison_fraction(poison_fraction: Probability) -> None:
    declared = declared_source_backdoor_poison_fractions()
    if poison_fraction not in declared:
        raise ValueError(
            f"source-backdoor poison fraction {poison_fraction!r} is not one of the declared "
            f"robustness sweep fractions {declared}"
        )


def scale_model_replacement_delta(delta: torch.Tensor, delta_scale: DeltaScale) -> torch.Tensor:
    return delta * delta_scale


def model_replacement_client_state(
    current_state: ModelState,
    trained_state: ModelState,
    input_width: ModelInputWidth,
    output_width: ModelOutputWidth,
    delta_scale: DeltaScale,
) -> ModelState:
    current_model = FedSIRAClassifier(input_width, output_width)
    trained_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(current_model, current_state)
    load_model_state(trained_model, trained_state)
    current_flat = flatten_trainable_parameters(current_model)
    trained_flat = flatten_trainable_parameters(trained_model)
    replaced = FedSIRAClassifier(input_width, output_width)
    load_flat_trainable_parameters(
        replaced,
        current_flat + scale_model_replacement_delta(trained_flat - current_flat, delta_scale),
    )
    return model_state_from_classifier(replaced)
