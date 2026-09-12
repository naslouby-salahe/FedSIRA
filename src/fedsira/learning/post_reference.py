from collections import OrderedDict
from collections.abc import Sequence
from typing import TypeVar

import torch
from torch import nn, optim
from torch.nn import functional as torch_functional

from fedsira.config import PostReferenceConfig, TrainingConfig
from fedsira.datasets.common import (
    BackdoorScope,
    DatasetAdapter,
    EpistemicFailureScope,
    HeterogeneityScope,
    RealAnchor,
    Role,
    RootCauseScope,
    apply_epistemic_target_marker,
    apply_heterogeneity_shift,
    flat_parameters_identity,
    poison_backdoor_rows,
    relabel_shared_label_error_rows_for_scope,
    scope_and_shift_rows,
    select_source_backdoor_poison_rows,
)
from fedsira.domain.enums import (
    EpistemicFailureType,
    SeedNamespace,
)
from fedsira.domain.types import (
    AlgorithmName,
    ArtifactDigest,
    BooleanValue,
    DatasetClassToken,
    DerivedSeed,
    DomainId,
    LocalEpochCount,
    LossWeight,
    MasterSeed,
    SampleId,
    Temperature,
    TrainableParameterCount,
    TrainingLoss,
)
from fedsira.evaluation.statistics import (
    decile_bin,
    decile_boundaries,
)
from fedsira.learning.federated import (
    LocalTrainingClient,
    train_one_client_locally,
    training_seed,
)
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
    logits_for_samples,
    per_sample_cross_entropy,
    probabilities_for_samples,
    trainable_parameter_count,
)
from fedsira.learning.training import (
    clip_gradients,
    load_model_state,
    model_state_from_classifier,
    ordered_batch_indices,
    step_optimizer,
)
from fedsira.protocol.baselines.registry import (
    centralized_reference_local_epochs,
    centralized_reference_pooled_rows,
    local_only_reference_local_epochs,
    local_only_reference_training_role,
)
from fedsira.runtime import (
    current_application_context,
    derive_uint32,
    namespace_seed,
    seed_job_local_rng_streams,
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
    triggered_features: torch.Tensor | None = None,
    triggered_labels: torch.Tensor | None = None,
    carrier_row_mask: torch.Tensor | None = None,
    triggered_backdoor_loss_weight: LossWeight | None = None,
) -> tuple[TrainingLoss, ...]:
    anchor_flat_parameters = flatten_trainable_parameters(anchor_model).detach()
    parameter_count = trainable_parameter_count(current_model)
    epoch_losses: list[TrainingLoss] = []
    for epoch in range(local_epochs):
        batch_losses: list[TrainingLoss] = []
        for indices in ordered_batch_indices(
            tuple(sample_ids), training_seed, epoch, training_config.batch_size
        ):
            if (
                triggered_features is not None
                and triggered_labels is not None
                and carrier_row_mask is not None
                and triggered_backdoor_loss_weight is not None
            ):
                from fedsira.protocol.attacks import verifier_aware_training_step

                batch_losses.append(
                    verifier_aware_training_step(
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
                        triggered_features[indices],
                        triggered_labels[indices],
                        carrier_row_mask[indices],
                        triggered_backdoor_loss_weight,
                    )
                )
            else:
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


DomainT = TypeVar("DomainT", bound=str)


LOCAL_ONLY_REFERENCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "LOCAL_ONLY_REFERENCE"
CENTRALIZED_REFERENCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "CENTRALIZED_REFERENCE"


def train_local_only_reference_checkpoint(
    adapter: DatasetAdapter, master_seed: MasterSeed, domain: DomainId
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    combined_features: list[torch.Tensor] = []
    combined_labels: list[torch.Tensor] = []
    combined_sample_ids: list[ArtifactDigest] = []
    training_role = local_only_reference_training_role()
    for class_id in adapter.class_tokens:
        if class_id == adapter.target_class_token:
            continue
        rows = adapter.tensor_view(adapter.load_rows(domain, class_id, training_role))
        if rows is None:
            continue
        features, labels, sample_ids = rows
        combined_features.append(features)
        combined_labels.append(labels)
        combined_sample_ids.extend(sample_ids)
    if not combined_features:
        return None
    features = torch.cat(combined_features, dim=0)
    labels = torch.cat(combined_labels, dim=0)
    input_width = features.shape[1]
    output_width = len(adapter.class_tokens)
    seed_job_local_rng_streams(
        derive_uint32(
            "LOCAL_ONLY_REFERENCE_INIT",
            namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
            adapter.domain_token(domain),
        )
    )
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    client_result = train_one_client_locally(
        initial_state,
        input_width,
        output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        local_only_reference_local_epochs(),
        LocalTrainingClient(
            features=features,
            labels=labels,
            sample_ids=tuple(combined_sample_ids),
            training_seed=training_seed(
                master_seed,
                adapter.manifest_hash(),
                "local-only-start",
                LOCAL_ONLY_REFERENCE_TRAINING_ALGORITHM_TOKEN,
                adapter.domain_token(domain),
                0,
            ),
        ),
    )
    final_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(final_model, client_result.state)
    return flatten_trainable_parameters(final_model)


def train_centralized_reference_checkpoint(
    adapter: DatasetAdapter, master_seed: MasterSeed
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    domain_features: OrderedDict[DomainId, torch.Tensor] = OrderedDict()
    domain_labels: OrderedDict[DomainId, torch.Tensor] = OrderedDict()
    domain_sample_ids: OrderedDict[DomainId, tuple[ArtifactDigest, ...]] = OrderedDict()
    for domain in adapter.domain_ids:
        combined_features: list[torch.Tensor] = []
        combined_labels: list[torch.Tensor] = []
        combined_sample_ids: list[ArtifactDigest] = []
        for class_id in adapter.class_tokens:
            if class_id == adapter.target_class_token:
                continue
            rows = adapter.tensor_view(adapter.load_rows(domain, class_id, Role.ANCHOR_TRAIN))
            if rows is None:
                continue
            features, labels, sample_ids = rows
            combined_features.append(features)
            combined_labels.append(labels)
            combined_sample_ids.extend(sample_ids)
        if not combined_features:
            continue
        domain_features[domain] = torch.cat(combined_features, dim=0)
        domain_labels[domain] = torch.cat(combined_labels, dim=0)
        domain_sample_ids[domain] = tuple(combined_sample_ids)
    if not domain_features:
        return None
    pooled_features = centralized_reference_pooled_rows(
        tuple(domain_features[domain] for domain in adapter.domain_ids if domain in domain_features)
    )
    pooled_labels = centralized_reference_pooled_rows(
        tuple(domain_labels[domain] for domain in adapter.domain_ids if domain in domain_labels)
    )
    pooled_sample_ids = tuple(
        sample_id
        for domain in adapter.domain_ids
        if domain in domain_sample_ids
        for sample_id in domain_sample_ids[domain]
    )
    input_width = pooled_features.shape[1]
    output_width = len(adapter.class_tokens)
    seed_job_local_rng_streams(
        derive_uint32(
            "CENTRALIZED_REFERENCE_INIT",
            namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
        )
    )
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    client_result = train_one_client_locally(
        initial_state,
        input_width,
        output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        centralized_reference_local_epochs(),
        LocalTrainingClient(
            features=pooled_features,
            labels=pooled_labels,
            sample_ids=pooled_sample_ids,
            training_seed=training_seed(
                master_seed,
                adapter.manifest_hash(),
                "centralized-start",
                CENTRALIZED_REFERENCE_TRAINING_ALGORITHM_TOKEN,
                adapter.domain_token(adapter.domain_ids[0]),
                0,
            ),
        ),
    )
    final_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(final_model, client_result.state)
    return flatten_trainable_parameters(final_model)


SOURCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "SOURCE_CANDIDATE"
REPRODUCTION_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "REPRODUCTION"
VERIFIER_AWARE_REPRODUCTION_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "VERIFIER_AWARE_REPRODUCTION"
IRRELEVANT_SOURCE_IMPROVEMENT_TRAINING_ALGORITHM_TOKEN: AlgorithmName = (
    "IRRELEVANT_SOURCE_IMPROVEMENT"
)
GENERIC_HARD_SUPPORTED_EXAMPLES_TRAINING_ALGORITHM_TOKEN: AlgorithmName = (
    "GENERIC_HARD_SUPPORTED_EXAMPLES"
)


def combined_post_reference_rows(
    adapter: DatasetAdapter,
    domain: DomainId,
    target_role: Role,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
    irrelevant_class: DatasetClassToken | None = None,
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], torch.Tensor] | None:
    target_rows = (
        adapter.load_rows(domain, irrelevant_class, Role.POST_REFERENCE_REPLAY)
        if irrelevant_class is not None
        else adapter.load_rows(domain, adapter.target_class_token, target_role)
    )
    if target_rows is not None and root_cause_scope is not None:
        target_rows = scope_and_shift_rows(target_rows, root_cause_scope)
    if (
        target_rows is not None
        and epistemic_failure_scope is not None
        and epistemic_failure_scope.failure_type
        in (
            EpistemicFailureType.SHARED_SPURIOUS_FEATURE,
            EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT,
        )
    ):
        target_rows = apply_epistemic_target_marker(target_rows, epistemic_failure_scope)
    if target_rows is not None and heterogeneity_scope is not None:
        target_rows = apply_heterogeneity_shift(target_rows, domain, heterogeneity_scope)
    target_tensor = adapter.tensor_view(target_rows)
    if target_tensor is None:
        return None
    target_features, target_labels, target_sample_ids = target_tensor
    target_is_supported = irrelevant_class is not None
    supported_features: list[torch.Tensor] = [target_features]
    supported_labels: list[torch.Tensor] = [target_labels]
    supported_sample_ids: list[ArtifactDigest] = list(target_sample_ids)
    is_supported: list[torch.Tensor] = [
        torch.full(
            (target_features.shape[0],),
            target_is_supported,
            dtype=torch.bool,
        )
    ]
    for class_id in adapter.class_tokens:
        if class_id == adapter.target_class_token or class_id == irrelevant_class:
            continue
        rows = adapter.load_rows(domain, class_id, Role.POST_REFERENCE_REPLAY)
        relabeled_mask: tuple[bool, ...] | None = None
        if (
            rows is not None
            and class_id == adapter.benign_class_token
            and epistemic_failure_scope is not None
            and epistemic_failure_scope.failure_type is EpistemicFailureType.SHARED_LABEL_ERROR
        ):
            rows, relabeled_mask = relabel_shared_label_error_rows_for_scope(
                rows, epistemic_failure_scope, adapter.target_class_token
            )
        if (
            rows is not None
            and class_id == adapter.attack_carrier_class_token()
            and backdoor_scope is not None
        ):
            rows = poison_backdoor_rows(rows, backdoor_scope, adapter.benign_class_token)
        if rows is not None and heterogeneity_scope is not None:
            rows = apply_heterogeneity_shift(
                rows, adapter.domain_token(domain), heterogeneity_scope
            )
        replay_tensor = adapter.tensor_view(rows)
        if replay_tensor is None:
            continue
        features, labels, sample_ids = replay_tensor
        supported_features.append(features)
        supported_labels.append(labels)
        supported_sample_ids.extend(sample_ids)
        is_supported.append(
            torch.tensor(relabeled_mask, dtype=torch.bool)
            if relabeled_mask is not None
            else torch.ones(features.shape[0], dtype=torch.bool)
        )
    return (
        torch.cat(supported_features, dim=0),
        torch.cat(supported_labels, dim=0),
        tuple(supported_sample_ids),
        torch.cat(is_supported, dim=0),
    )


def verifier_aware_carrier_mask(
    adapter: DatasetAdapter,
    domain: DomainId,
    backdoor_scope: BackdoorScope,
    sample_ids: tuple[SampleId, ...],
) -> torch.Tensor:
    carrier_rows = adapter.load_rows(
        domain, adapter.attack_carrier_class_token(), Role.POST_REFERENCE_REPLAY
    )
    if carrier_rows is None:
        return torch.zeros(len(sample_ids), dtype=torch.bool)
    selected = select_source_backdoor_poison_rows(
        carrier_rows.sample_ids,
        backdoor_scope.poison_fraction,
        backdoor_scope.attack_generation_seed,
    )
    if selected is None:
        return torch.zeros(len(sample_ids), dtype=torch.bool)
    poisoned_ids = frozenset(selected)
    return torch.tensor([sample_id in poisoned_ids for sample_id in sample_ids], dtype=torch.bool)


def _train_post_reference_delta(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: DomainId,
    target_role: Role,
    algorithm_token: AlgorithmName,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
    verifier_aware: BooleanValue = False,
    irrelevant_class: DatasetClassToken | None = None,
) -> torch.Tensor | None:
    combined = combined_post_reference_rows(
        adapter,
        domain,
        target_role,
        root_cause_scope,
        epistemic_failure_scope,
        backdoor_scope,
        heterogeneity_scope,
        irrelevant_class,
    )
    if combined is None:
        return None
    features, labels, sample_ids, is_supported = combined
    config = current_application_context().scientific_config
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    current_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(current_model, anchor.flat_parameters)
    derived_seed = training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        flat_parameters_identity(anchor.flat_parameters),
        algorithm_token,
        adapter.domain_token(domain),
        -1,
    )
    seed_job_local_rng_streams(derived_seed)
    optimizer = torch.optim.AdamW(
        current_model.parameters(),
        lr=config.model.optimizer.post_reference_learning_rate,
        betas=config.model.optimizer.betas,
        eps=config.model.optimizer.epsilon,
        weight_decay=config.model.optimizer.weight_decay,
    )
    if verifier_aware and backdoor_scope is not None:
        run_post_reference_training(
            anchor_model,
            current_model,
            optimizer,
            torch.nn.CrossEntropyLoss(),
            config.model.training,
            config.model.post_reference,
            features,
            labels,
            is_supported,
            sample_ids,
            derived_seed,
            config.model.verifier_aware_backdoor_override.local_epochs,
            triggered_features=features,
            triggered_labels=labels,
            carrier_row_mask=verifier_aware_carrier_mask(
                adapter, domain, backdoor_scope, sample_ids
            ),
            triggered_backdoor_loss_weight=(
                config.model.verifier_aware_backdoor_override.triggered_backdoor_loss_weight
            ),
        )
    else:
        run_post_reference_training(
            anchor_model,
            current_model,
            optimizer,
            torch.nn.CrossEntropyLoss(),
            config.model.training,
            config.model.post_reference,
            features,
            labels,
            is_supported,
            sample_ids,
            derived_seed,
            config.model.post_reference.local_epochs,
        )
    return flatten_trainable_parameters(current_model) - anchor.flat_parameters


def irrelevant_source_class_by_anchor_cross_entropy(
    adapter: DatasetAdapter,
    anchor: RealAnchor,
    source_domain: DomainId,
) -> DatasetClassToken | None:
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    selected: DatasetClassToken | None = None
    selected_mean: TrainingLoss | None = None
    for class_id in adapter.class_tokens:
        if class_id in (adapter.target_class_token, adapter.benign_class_token):
            continue
        rows = adapter.load_rows(source_domain, class_id, Role.ANCHOR_VALIDATION)
        tensor_rows = adapter.tensor_view(rows)
        if tensor_rows is None:
            continue
        features, labels, _sample_ids = tensor_rows
        losses = per_sample_cross_entropy(model, features, labels)
        mean_loss = float(losses.mean().detach())
        if selected_mean is None or mean_loss > selected_mean:
            selected_mean = mean_loss
            selected = class_id
    return selected


def train_irrelevant_source_improvement_delta(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId,
) -> torch.Tensor | None:
    irrelevant = irrelevant_source_class_by_anchor_cross_entropy(adapter, anchor, source_domain)
    if irrelevant is None:
        return None
    return _train_post_reference_delta(
        adapter,
        master_seed,
        anchor,
        source_domain,
        Role.REPRODUCTION,
        IRRELEVANT_SOURCE_IMPROVEMENT_TRAINING_ALGORITHM_TOKEN,
        None,
        None,
        None,
        None,
        False,
        irrelevant,
    )


def train_verifier_aware_reproduction_delta(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: DomainId,
    backdoor_scope: BackdoorScope,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> torch.Tensor | None:
    return _train_post_reference_delta(
        adapter,
        master_seed,
        anchor,
        domain,
        Role.REPRODUCTION,
        VERIFIER_AWARE_REPRODUCTION_TRAINING_ALGORITHM_TOKEN,
        None,
        None,
        backdoor_scope,
        heterogeneity_scope,
        verifier_aware=True,
    )


def train_domain_reproduction_delta(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: DomainId,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
) -> torch.Tensor | None:
    return _train_post_reference_delta(
        adapter,
        master_seed,
        anchor,
        domain,
        Role.REPRODUCTION,
        REPRODUCTION_TRAINING_ALGORITHM_TOKEN,
        root_cause_scope,
        epistemic_failure_scope,
        backdoor_scope,
        heterogeneity_scope,
    )


def certified_domain_delta_committee(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domains: Sequence[DomainT],
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> OrderedDict[DomainT, torch.Tensor]:
    deltas: OrderedDict[DomainT, torch.Tensor] = OrderedDict()
    for domain in domains:
        delta = train_domain_reproduction_delta(
            adapter, master_seed, anchor, domain, heterogeneity_scope=heterogeneity_scope
        )
        if delta is not None:
            deltas[domain] = delta
    return deltas


def train_source_candidate_delta(
    adapter: DatasetAdapter,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: DomainId,
    backdoor_scope: BackdoorScope | None = None,
) -> torch.Tensor | None:
    return _train_post_reference_delta(
        adapter,
        master_seed,
        anchor,
        source_domain,
        Role.SOURCE_PROPOSAL,
        SOURCE_TRAINING_ALGORITHM_TOKEN,
        backdoor_scope=backdoor_scope,
    )


def train_generic_hard_supported_examples_delta(
    adapter: DatasetAdapter, master_seed: MasterSeed, anchor: RealAnchor, source_domain: DomainId
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    selected_features: list[torch.Tensor] = []
    selected_labels: list[torch.Tensor] = []
    selected_sample_ids: list[ArtifactDigest] = []
    for class_id in adapter.class_tokens:
        if class_id == adapter.target_class_token:
            continue
        rows = adapter.tensor_view(
            adapter.load_rows(source_domain, class_id, Role.POST_REFERENCE_REPLAY)
        )
        if rows is None:
            continue
        features, labels, sample_ids = rows
        losses = [
            float(value) for value in per_sample_cross_entropy(anchor_model, features, labels)
        ]
        boundaries = decile_boundaries(tuple(losses))
        assigned_bins = tuple(decile_bin(loss, boundaries) for loss in losses)
        top_decile_bin = max(assigned_bins)
        top_decile_indices = [
            index for index, bin_index in enumerate(assigned_bins) if bin_index == top_decile_bin
        ]
        if not top_decile_indices:
            continue
        selected_features.append(features[top_decile_indices])
        selected_labels.append(labels[top_decile_indices])
        selected_sample_ids.extend(sample_ids[index] for index in top_decile_indices)
    if not selected_features:
        return None
    combined_features = torch.cat(selected_features, dim=0)
    combined_labels = torch.cat(selected_labels, dim=0)
    is_supported = torch.ones(combined_features.shape[0], dtype=torch.bool)
    current_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(current_model, anchor.flat_parameters)
    seed = training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        flat_parameters_identity(anchor.flat_parameters),
        GENERIC_HARD_SUPPORTED_EXAMPLES_TRAINING_ALGORITHM_TOKEN,
        adapter.domain_token(source_domain),
        -1,
    )
    seed_job_local_rng_streams(seed)
    optimizer = torch.optim.AdamW(
        current_model.parameters(),
        lr=config.model.optimizer.post_reference_learning_rate,
        betas=config.model.optimizer.betas,
        eps=config.model.optimizer.epsilon,
        weight_decay=config.model.optimizer.weight_decay,
    )
    loss_function = torch.nn.CrossEntropyLoss()
    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        config.model.training,
        config.model.post_reference,
        combined_features,
        combined_labels,
        is_supported,
        tuple(selected_sample_ids),
        seed,
        config.model.post_reference.local_epochs,
    )
    return flatten_trainable_parameters(current_model) - anchor.flat_parameters
