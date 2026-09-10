from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import torch

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
    deterministic_domain_order,
)
from fedsira.domain.enums import SeedNamespace
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    AlgorithmName,
    ArtifactDigest,
    ClassIndex,
    ClassLabel,
    FeatureCount,
    FederatedRoundCount,
    GroupCount,
    GroupIndex,
    MasterSeed,
    NamespaceSeed,
    Probability,
    RoundIndex,
    RowCount,
    TargetBearingMemberPresent,
    VoteCount,
)
from fedsira.evaluation.metrics import (
    benign_false_alarm_rate,
    compute_confusion_counts_by_class,
    f1_for_class,
    macro_f1,
)
from fedsira.experiments.workflow import (
    DomainTargetMetrics,
    dataset_manifest_hash,
    load_prepared_rows,
    tensor_view,
)
from fedsira.learning.aggregation import load_model_state, model_state_from_classifier
from fedsira.learning.anchor import run_anchor_fedavg_training
from fedsira.learning.anchor_training import training_seed
from fedsira.learning.federated import LocalTrainingClient, run_fedavg_round
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.learning.post_reference_training import combined_post_reference_rows
from fedsira.learning.scoring import logits_for_samples
from fedsira.runtime import current_application_context
from fedsira.runtime_execution import derive_uint32, namespace_seed, seed_job_local_rng_streams

DOMAIN_PARTITION_SEPARATOR = SeedNamespace.DOMAIN_PARTITION.value
CERTIFIED_ENSEMBLE_ANCHOR_TRAINING_ALGORITHM_TOKEN: AlgorithmName = "CERTIFIED_ENSEMBLE_ANCHOR"
CERTIFIED_ENSEMBLE_POST_REFERENCE_TRAINING_ALGORITHM_TOKEN: AlgorithmName = (
    "CERTIFIED_ENSEMBLE_POST_REFERENCE"
)


@dataclass(frozen=True)
class GroupCheckpoint:
    input_width: FeatureCount
    output_width: FeatureCount
    flat_parameters: torch.Tensor


def certified_ensemble_post_reference_rounds() -> FederatedRoundCount:
    baselines = current_application_context().scientific_config.baselines
    return baselines.fedavg_post_reference_rounds


def certified_ensemble_domain_groups(
    domain_partition_namespace_seed: NamespaceSeed, group_count: GroupCount
) -> tuple[tuple[NBaiotDomain, ...], ...]:
    ordered = deterministic_domain_order(
        NBAIOT_DOMAIN_ORDER, DOMAIN_PARTITION_SEPARATOR, domain_partition_namespace_seed
    )
    group_size = len(ordered) // group_count
    return tuple(
        ordered[group_index * group_size : (group_index + 1) * group_size]
        for group_index in range(group_count)
    )


def validate_group_without_target_member_uses_supported_only(
    has_target_bearing_member: TargetBearingMemberPresent, group_target_row_count: RowCount
) -> None:
    if not has_target_bearing_member and group_target_row_count != 0:
        raise ValueError(
            "ensemble group without a target-bearing member must not receive target rows"
        )


def ensemble_predicted_label(
    predicted_labels: Sequence[ClassIndex], softmax_probabilities: Sequence[Sequence[Probability]]
) -> ClassIndex:
    counts: OrderedDict[ClassIndex, VoteCount] = OrderedDict()
    for label in predicted_labels:
        counts[label] = counts.get(label, 0) + 1
    max_count = max(counts.values())
    if max_count > 1:
        return min(label for label, count in counts.items() if count == max_count)

    tied_labels = sorted(set(predicted_labels))
    mean_probability_by_label: OrderedDict[ClassIndex, Probability] = OrderedDict(
        (
            label,
            sum(probabilities[label] for probabilities in softmax_probabilities)
            / len(softmax_probabilities),
        )
        for label in tied_labels
    )
    best_mean_probability = max(mean_probability_by_label.values())
    return min(
        label
        for label, mean_probability in mean_probability_by_label.items()
        if mean_probability == best_mean_probability
    )


def _group_anchor_checkpoint(
    prepared_root: Path,
    master_seed: MasterSeed,
    group_domains: Sequence[NBaiotDomain],
    group_index: GroupIndex,
) -> GroupCheckpoint | None:
    config = current_application_context().scientific_config
    first_rows = load_prepared_rows(
        prepared_root, group_domains[0], NBaiotClass.BENIGN, Role.ANCHOR_TRAIN
    )
    if first_rows is None:
        return None
    input_width = len(first_rows.features[0])
    output_width = len(NBAIOT_CLASS_ORDER)
    initialization_seed = derive_uint32(
        "CERTIFIED_ENSEMBLE_GROUP_INIT",
        namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
        group_index,
    )
    seed_job_local_rng_streams(initialization_seed)
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    start_checkpoint_identity = f"certified-ensemble-group-{group_index}-anchor-start"
    clients_per_round: list[tuple[LocalTrainingClient, ...]] = []
    for round_index in range(config.model.anchor_fedavg.rounds):
        round_clients: list[LocalTrainingClient] = []
        for domain in group_domains:
            combined_features: list[torch.Tensor] = []
            combined_labels: list[torch.Tensor] = []
            combined_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                rows = tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
                )
                if rows is None:
                    continue
                features, labels, sample_ids = rows
                combined_features.append(features)
                combined_labels.append(labels)
                combined_sample_ids.extend(sample_ids)
            if not combined_features:
                continue
            round_clients.append(
                LocalTrainingClient(
                    features=torch.cat(combined_features, dim=0),
                    labels=torch.cat(combined_labels, dim=0),
                    sample_ids=tuple(combined_sample_ids),
                    training_seed=training_seed(
                        master_seed,
                        dataset_manifest_hash(prepared_root),
                        start_checkpoint_identity,
                        CERTIFIED_ENSEMBLE_ANCHOR_TRAINING_ALGORITHM_TOKEN,
                        domain,
                        round_index,
                    ),
                )
            )
        if not round_clients:
            return None
        clients_per_round.append(tuple(round_clients))
    final_state, _round_checkpoints = run_anchor_fedavg_training(
        input_width,
        output_width,
        initial_state,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        config.model.anchor_fedavg,
        tuple(clients_per_round),
    )
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, final_state)
    return GroupCheckpoint(
        input_width=input_width,
        output_width=output_width,
        flat_parameters=flatten_trainable_parameters(model),
    )


def _group_post_reference_round_clients(
    prepared_root: Path,
    master_seed: MasterSeed,
    group_domains: Sequence[NBaiotDomain],
    group_index: GroupIndex,
    round_index: RoundIndex,
) -> list[LocalTrainingClient]:
    manifest_hash = dataset_manifest_hash(prepared_root)
    start_checkpoint_identity = f"certified-ensemble-group-{group_index}-post-reference-start"
    has_target_bearing_member = False
    group_target_row_count = 0
    clients: list[LocalTrainingClient] = []
    for domain in group_domains:
        target_rows = load_prepared_rows(
            prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.REPRODUCTION
        )
        if target_rows is not None:
            has_target_bearing_member = True
            group_target_row_count += target_rows.row_count
        combined = combined_post_reference_rows(prepared_root, domain, Role.REPRODUCTION)
        if combined is not None:
            features, labels, sample_ids, _is_supported = combined
        else:
            supported_features: list[torch.Tensor] = []
            supported_labels: list[torch.Tensor] = []
            supported_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                rows = tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
                )
                if rows is None:
                    continue
                sample_features, sample_labels, sample_ids = rows
                supported_features.append(sample_features)
                supported_labels.append(sample_labels)
                supported_sample_ids.extend(sample_ids)
            if not supported_features:
                continue
            features = torch.cat(supported_features, dim=0)
            labels = torch.cat(supported_labels, dim=0)
            sample_ids = tuple(supported_sample_ids)
        clients.append(
            LocalTrainingClient(
                features=features,
                labels=labels,
                sample_ids=sample_ids,
                training_seed=training_seed(
                    master_seed,
                    manifest_hash,
                    start_checkpoint_identity,
                    CERTIFIED_ENSEMBLE_POST_REFERENCE_TRAINING_ALGORITHM_TOKEN,
                    domain,
                    round_index,
                ),
            )
        )
    validate_group_without_target_member_uses_supported_only(
        has_target_bearing_member, 0 if has_target_bearing_member else group_target_row_count
    )
    return clients


def train_certified_ensemble_group_checkpoints(
    prepared_root: Path, master_seed: MasterSeed
) -> tuple[GroupCheckpoint, ...] | None:
    config = current_application_context().scientific_config
    domain_partition_namespace_seed = namespace_seed(master_seed, SeedNamespace.DOMAIN_PARTITION)
    groups = certified_ensemble_domain_groups(
        domain_partition_namespace_seed,
        config.baselines.multiple_model_certified_ensemble_group_count,
    )
    checkpoints: list[GroupCheckpoint] = []
    for group_index, group_domains in enumerate(groups):
        group_anchor = _group_anchor_checkpoint(
            prepared_root, master_seed, group_domains, group_index
        )
        if group_anchor is None:
            return None
        model = FedSIRAClassifier(group_anchor.input_width, group_anchor.output_width)
        load_flat_trainable_parameters(model, group_anchor.flat_parameters)
        state = model_state_from_classifier(model)
        for round_index in range(certified_ensemble_post_reference_rounds()):
            round_clients = _group_post_reference_round_clients(
                prepared_root, master_seed, group_domains, group_index, round_index
            )
            if not round_clients:
                continue
            state = run_fedavg_round(
                state,
                group_anchor.input_width,
                group_anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                tuple(round_clients),
            )
        final_model = FedSIRAClassifier(group_anchor.input_width, group_anchor.output_width)
        load_model_state(final_model, state)
        checkpoints.append(
            GroupCheckpoint(
                input_width=group_anchor.input_width,
                output_width=group_anchor.output_width,
                flat_parameters=flatten_trainable_parameters(final_model),
            )
        )
    return tuple(checkpoints)


def _ensemble_predictions_for_domain(
    prepared_root: Path,
    group_checkpoints: Sequence[GroupCheckpoint],
    domain: NBaiotDomain,
    role: Role,
) -> tuple[list[ClassLabel], list[ClassLabel]] | None:
    true_labels: list[ClassLabel] = []
    predicted_labels: list[ClassLabel] = []
    models: list[FedSIRAClassifier] = []
    for checkpoint in group_checkpoints:
        model = FedSIRAClassifier(checkpoint.input_width, checkpoint.output_width)
        load_flat_trainable_parameters(model, checkpoint.flat_parameters)
        model.eval()
        models.append(model)
    for class_id in NBAIOT_CLASS_ORDER:
        rows = load_prepared_rows(prepared_root, domain, class_id, role)
        if rows is None:
            continue
        features = torch.tensor(rows.features, dtype=torch.float32)
        with torch.no_grad():
            per_model_logits = [logits_for_samples(model, features) for model in models]
        for sample_index in range(features.shape[0]):
            predicted_indices: list[int] = []
            softmax_probabilities: list[tuple[float, ...]] = []
            for logits in per_model_logits:
                sample_logits = logits[sample_index]
                predicted_indices.append(int(torch.argmax(sample_logits)))
                probabilities = torch.softmax(sample_logits, dim=-1)
                softmax_probabilities.append(tuple(float(value) for value in probabilities))
            ensemble_index = ensemble_predicted_label(predicted_indices, softmax_probabilities)
            true_labels.append(class_id.value)
            predicted_labels.append(NBAIOT_CLASS_ORDER[ensemble_index].value)
    if not true_labels:
        return None
    return (true_labels, predicted_labels)


def evaluate_certified_ensemble(
    prepared_root: Path,
    group_checkpoints: Sequence[GroupCheckpoint],
    domain: NBaiotDomain,
    role: Role,
) -> DomainTargetMetrics | None:
    result = _ensemble_predictions_for_domain(prepared_root, group_checkpoints, domain, role)
    if result is None:
        return None
    true_labels, predicted_labels = result
    class_tokens = tuple(class_id.value for class_id in NBAIOT_CLASS_ORDER)
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    f1_by_class = OrderedDict(
        ((token, f1_for_class(counts)) for token, counts in counts_by_class.items())
    )
    supported_f1 = OrderedDict(
        (token, f1_by_class[token]) for token in class_tokens if token != NBaiotClass.GAFGYT_COMBO
    )
    return DomainTargetMetrics(
        target_f1=f1_by_class.get(
            NBaiotClass.GAFGYT_COMBO, MetricResult(value=None, denominator=0)
        ),
        supported_macro_f1=macro_f1(supported_f1),
        benign_far=benign_false_alarm_rate(true_labels, predicted_labels, NBaiotClass.BENIGN),
    )
