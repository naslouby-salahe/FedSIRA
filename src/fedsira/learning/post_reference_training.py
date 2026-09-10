from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import NBAIOT_CLASS_ORDER, NBaiotClass, NBaiotDomain
from fedsira.domain.types import AlgorithmName, ArtifactDigest, MasterSeed
from fedsira.evaluation.summaries import decile_bin, decile_boundaries
from fedsira.experiments.definitions import EpistemicFailureType
from fedsira.experiments.workflow import (
    BackdoorScope,
    EpistemicFailureScope,
    HeterogeneityScope,
    RealAnchor,
    RootCauseScope,
    apply_epistemic_target_marker,
    apply_heterogeneity_shift,
    flat_parameters_identity,
    load_prepared_rows,
    poison_backdoor_rows,
    relabel_shared_label_error_rows_for_scope,
    scope_and_shift_rows,
    tensor_view,
)
from fedsira.learning.anchor_training import training_seed
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.learning.post_reference import run_post_reference_training
from fedsira.learning.scoring import per_sample_cross_entropy
from fedsira.runtime import current_application_context, seed_job_local_rng_streams

SOURCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "SOURCE_CANDIDATE"
REPRODUCTION_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "REPRODUCTION"
GENERIC_HARD_SUPPORTED_EXAMPLES_TRAINING_ALGORITHM_TOKEN: AlgorithmName = (
    "GENERIC_HARD_SUPPORTED_EXAMPLES"
)


def combined_post_reference_rows(
    prepared_root: Path,
    domain: NBaiotDomain,
    target_role: Role,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], torch.Tensor] | None:
    target_rows = load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, target_role)
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
    target_tensor = tensor_view(target_rows)
    if target_tensor is None:
        return None
    target_features, target_labels, target_sample_ids = target_tensor
    supported_features: list[torch.Tensor] = [target_features]
    supported_labels: list[torch.Tensor] = [target_labels]
    supported_sample_ids: list[ArtifactDigest] = list(target_sample_ids)
    is_supported: list[torch.Tensor] = [torch.zeros(target_features.shape[0], dtype=torch.bool)]
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        rows = load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
        relabeled_mask: tuple[bool, ...] | None = None
        if (
            rows is not None
            and class_id is NBaiotClass.BENIGN
            and epistemic_failure_scope is not None
            and epistemic_failure_scope.failure_type is EpistemicFailureType.SHARED_LABEL_ERROR
        ):
            rows, relabeled_mask = relabel_shared_label_error_rows_for_scope(
                rows, epistemic_failure_scope
            )
        if rows is not None and class_id is NBaiotClass.GAFGYT_UDP and backdoor_scope is not None:
            rows = poison_backdoor_rows(rows, backdoor_scope)
        if rows is not None and heterogeneity_scope is not None:
            rows = apply_heterogeneity_shift(rows, domain, heterogeneity_scope)
        replay_tensor = tensor_view(rows)
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


def _train_post_reference_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: NBaiotDomain,
    target_role: Role,
    algorithm_token: AlgorithmName,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> torch.Tensor | None:
    combined = combined_post_reference_rows(
        prepared_root,
        domain,
        target_role,
        root_cause_scope,
        epistemic_failure_scope,
        backdoor_scope,
        heterogeneity_scope,
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
        domain,
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


def train_domain_reproduction_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: NBaiotDomain,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> torch.Tensor | None:
    return _train_post_reference_delta(
        prepared_root,
        master_seed,
        anchor,
        domain,
        Role.REPRODUCTION,
        REPRODUCTION_TRAINING_ALGORITHM_TOKEN,
        root_cause_scope,
        epistemic_failure_scope,
        heterogeneity_scope=heterogeneity_scope,
    )


def certified_domain_delta_committee(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domains: Sequence[NBaiotDomain],
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> OrderedDict[NBaiotDomain, torch.Tensor]:
    deltas: OrderedDict[NBaiotDomain, torch.Tensor] = OrderedDict()
    for domain in domains:
        delta = train_domain_reproduction_delta(
            prepared_root, master_seed, anchor, domain, heterogeneity_scope=heterogeneity_scope
        )
        if delta is not None:
            deltas[domain] = delta
    return deltas


def train_source_candidate_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain,
    backdoor_scope: BackdoorScope | None = None,
) -> torch.Tensor | None:
    return _train_post_reference_delta(
        prepared_root,
        master_seed,
        anchor,
        source_domain,
        Role.SOURCE_PROPOSAL,
        SOURCE_TRAINING_ALGORITHM_TOKEN,
        backdoor_scope=backdoor_scope,
    )


def train_generic_hard_supported_examples_delta(
    prepared_root: Path, master_seed: MasterSeed, anchor: RealAnchor, source_domain: NBaiotDomain
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    selected_features: list[torch.Tensor] = []
    selected_labels: list[torch.Tensor] = []
    selected_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        rows = tensor_view(
            load_prepared_rows(prepared_root, source_domain, class_id, Role.POST_REFERENCE_REPLAY)
        )
        if rows is None:
            continue
        features, labels, sample_ids = rows
        losses = [
            float(value) for value in per_sample_cross_entropy(anchor_model, features, labels)
        ]
        boundaries = decile_boundaries(tuple(losses))
        top_decile_bin = len(boundaries)
        top_decile_indices = [
            index
            for index, loss in enumerate(losses)
            if decile_bin(loss, boundaries) == top_decile_bin
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
        source_domain,
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
