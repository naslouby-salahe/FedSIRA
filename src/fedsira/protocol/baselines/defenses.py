from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeVar

import torch

from fedsira.config import (
    DensityClusterTrimmedMeanConfig,
    MaterialityConfig,
    ParameterSimilarityConfig,
    ThreeRowCoordinateMedianConfig,
)
from fedsira.datasets.common import (
    DomainTargetMetrics,
    Role,
    dataset_manifest_hash,
)
from fedsira.datasets.nbaiot.learning.post_reference_training import combined_post_reference_rows
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    NBaiotDomain,
    deterministic_domain_order,
    nbaiot_adapter,
    nbaiot_domain_hash_token,
)
from fedsira.domain.enums import AdmissionState, SeedNamespace
from fedsira.domain.models import MetricResult
from fedsira.domain.types import (
    AlgorithmName,
    ArtifactDigest,
    CalibrationErrorCount,
    CapabilityContractSatisfied,
    ClassIndex,
    ClassLabel,
    ClusterSize,
    CommitteeSize,
    DbscanEpsilon,
    DerivedSeed,
    DeterministicInteger,
    DiscardSourceWeights,
    DomainCount,
    FeatureCount,
    FederatedRoundCount,
    FrozenDomainModel,
    GroupCount,
    GroupIndex,
    LocalEpochCount,
    MasterSeed,
    MemberIndex,
    MetricValue,
    NamespaceSeed,
    NonAbstainingReproductionSeries,
    NumericalEpsilon,
    OptionalParameterSimilarity,
    PairwiseDistance,
    PairwiseDistanceMatrix,
    ParameterSimilarityCertified,
    ParticipantCount,
    Percentage,
    Probability,
    ReconstructionAccepted,
    ReconstructionError,
    ReconstructionErrorSeries,
    ReconstructionThreshold,
    RecoveryRollbackTriggered,
    ReviewerCount,
    ReviewerPositiveDecision,
    RoundIndex,
    RowCount,
    SourceIsProductionUpdate,
    TargetBearingMemberPresent,
    TensorDomainModel,
    TrimCount,
    VectorNorm,
    VerifierCount,
    VoteCount,
)
from fedsira.evaluation.metrics import (
    benign_false_alarm_rate,
    compute_confusion_counts_by_class,
    f1_for_class,
    macro_f1,
)
from fedsira.evaluation.statistics import quantile_type7
from fedsira.learning.federated import (
    LocalTrainingClient,
    run_anchor_fedavg_training,
    run_fedavg_round,
    training_seed,
)
from fedsira.learning.model import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
    logits_for_samples,
)
from fedsira.learning.training import (
    ModelState,
    WeightedModelState,
    federated_averaging,
    load_model_state,
    model_state_from_classifier,
)
from fedsira.protocol.baselines.registry import post_reference_retrain_maximum_local_epochs
from fedsira.protocol.synthesis import CertifiedReproductionRow
from fedsira.runtime import (
    current_application_context,
    derive_uint32,
    deterministic_order,
    namespace_seed,
    seed_job_local_rng_streams,
)

CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES: Final[tuple[Role, Role]] = (
    Role.CANDIDATE_SCREEN,
    Role.POST_REFERENCE_REPLAY,
)
CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT: Final[ReviewerCount] = 3
SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT: Final[ReviewerCount] = 3
SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS: Final[ReviewerCount] = 2
INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT: Final[ReviewerCount] = 3
INDEPENDENT_LOCAL_REFERENCE_REQUIRED_POSITIVE_REVIEWS: Final[ReviewerCount] = 2


def client_review_direct_admission_production_is_source(
    production_update: torch.Tensor, source_update: torch.Tensor
) -> SourceIsProductionUpdate:
    return torch.equal(production_update, source_update)


def validate_client_review_composite_screen(roles: tuple[Role, ...]) -> None:
    if roles != CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES:
        raise ValueError(
            "client review must use the fixed composite screen view: "
            "target Candidate Screen rows plus supported Post-Reference Replay rows"
        )


def validate_client_review_reviewer_count(reviewer_count: ReviewerCount) -> None:
    if reviewer_count != CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT:
        raise ValueError(
            f"client review requires exactly {CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT} reviewers"
        )


def client_review_then_retrain_should_discard_source_weights(
    review_outcome: AdmissionState,
) -> DiscardSourceWeights:
    return review_outcome is AdmissionState.ADMITTED


def client_review_then_retrain_local_epochs() -> LocalEpochCount:
    return post_reference_retrain_maximum_local_epochs()


def independent_local_reference_reviewer_is_positive(
    source_satisfies_capability_contract: CapabilityContractSatisfied,
    source_supported_macro_f1: Probability,
    local_reference_supported_macro_f1: Probability,
    source_benign_false_alarm_rate: Probability,
    local_reference_benign_false_alarm_rate: Probability,
    materiality_config: MaterialityConfig,
) -> ReviewerPositiveDecision:
    if not source_satisfies_capability_contract:
        return False
    if (
        source_supported_macro_f1
        < local_reference_supported_macro_f1
        - materiality_config.supported_macro_f1_noninferiority_margin
    ):
        return False
    return (
        source_benign_false_alarm_rate
        <= local_reference_benign_false_alarm_rate
        + materiality_config.benign_false_alarm_rate_noninferiority_margin
    )


def secure_continual_assessment_post_reference_rounds() -> FederatedRoundCount:
    baselines = current_application_context().scientific_config.baselines
    return baselines.secure_continual_assessment_post_reference_rounds


CLIENT_SAMPLING_SEPARATOR = SeedNamespace.CLIENT_SAMPLING.value
Domain = TypeVar("Domain")


def direct_krum_committee_rows(
    committed_rows: tuple[CertifiedReproductionRow, ...],
    is_non_abstaining: NonAbstainingReproductionSeries,
    committee_size: CommitteeSize,
) -> tuple[CertifiedReproductionRow, ...] | None:
    if len(committed_rows) != len(is_non_abstaining):
        raise ValueError("committed rows and abstention states must have equal length")
    eligible = tuple(
        row
        for row, non_abstaining in zip(committed_rows, is_non_abstaining, strict=True)
        if non_abstaining
    )
    if len(eligible) < committee_size:
        return None
    return eligible[:committee_size]


def validate_three_row_coordinate_median_committee_size(
    committee_size: CommitteeSize,
    config: ThreeRowCoordinateMedianConfig,
) -> None:
    if committee_size != config.row_count:
        raise ValueError(
            f"Three-Row Coordinate-Median Alternative requires exactly {config.row_count} rows, "
            f"got {committee_size}"
        )


def coordinate_wise_median_synthesis(
    update_vectors: tuple[torch.Tensor, ...],
) -> torch.Tensor:
    if not update_vectors:
        raise ValueError("coordinate-wise median requires at least one update")
    stacked = torch.stack(update_vectors, dim=0)
    return torch.median(stacked, dim=0).values


def krum_reference_post_reference_rounds() -> FederatedRoundCount:
    baselines = current_application_context().scientific_config.baselines
    return baselines.fedavg_post_reference_rounds


def client_sampling_round_seed(master_seed: MasterSeed, round_index: RoundIndex) -> DerivedSeed:
    return derive_uint32(CLIENT_SAMPLING_SEPARATOR, master_seed, round_index)


def client_sampling_round_order(
    eligible_domains: tuple[Domain, ...],
    master_seed: MasterSeed,
    round_index: RoundIndex,
) -> tuple[Domain, ...]:
    round_seed = client_sampling_round_seed(master_seed, round_index)
    return deterministic_order(eligible_domains, CLIENT_SAMPLING_SEPARATOR, round_seed)


def krum_reference_round_participants(
    round_order: tuple[Domain, ...],
    compromised_domain: Domain | None,
    participant_count: ParticipantCount,
) -> tuple[Domain, ...] | None:
    if compromised_domain is None:
        selected = round_order[:participant_count]
    else:
        remaining = tuple(domain for domain in round_order if domain is not compromised_domain)
        selected = (compromised_domain, *remaining[: participant_count - 1])
    if len(selected) < participant_count:
        return None
    return selected


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
    first_rows = nbaiot_adapter(prepared_root).load_rows(
        group_domains[0], NBaiotClass.BENIGN, Role.ANCHOR_TRAIN
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
                rows = nbaiot_adapter(prepared_root).tensor_view(
                    nbaiot_adapter(prepared_root).load_rows(domain, class_id, Role.ANCHOR_TRAIN)
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
                        nbaiot_domain_hash_token(domain),
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
        target_rows = nbaiot_adapter(prepared_root).load_rows(
            domain, NBaiotClass.GAFGYT_COMBO, Role.REPRODUCTION
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
                rows = nbaiot_adapter(prepared_root).tensor_view(
                    nbaiot_adapter(prepared_root).load_rows(
                        domain, class_id, Role.POST_REFERENCE_REPLAY
                    )
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
                    nbaiot_domain_hash_token(domain),
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
        rows = nbaiot_adapter(prepared_root).load_rows(domain, class_id, role)
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


_DBSCAN_UNASSIGNED: DeterministicInteger = -2
_DBSCAN_NOISE: DeterministicInteger = -1


class DomainFeatureMean(TensorDomainModel):
    domain: NBaiotDomain
    feature_mean: torch.Tensor


class DensityCluster(FrozenDomainModel):
    label: DeterministicInteger
    member_indices: tuple[MemberIndex, ...]


def reconstruction_error(
    submitted_update: torch.Tensor,
    reconstructed_update: torch.Tensor,
    normalization_epsilon: NumericalEpsilon,
) -> ReconstructionError:
    squared_l2_distance = float(
        torch.sum((submitted_update.detach() - reconstructed_update.detach()) ** 2)
    )
    submitted_squared_norm = float(torch.sum(submitted_update.detach() ** 2))
    return squared_l2_distance / (submitted_squared_norm + normalization_epsilon)


def reconstruction_filter_calibration_error_count(
    anchor_round_count: FederatedRoundCount,
    domain_count: DomainCount,
) -> CalibrationErrorCount:
    return anchor_round_count * domain_count


def reconstruction_rejection_threshold(
    calibration_errors: ReconstructionErrorSeries,
    calibration_percentile: Percentage,
) -> ReconstructionThreshold:
    return quantile_type7(
        tuple(sorted(calibration_errors)),
        calibration_percentile / 100.0,
    )


def reconstruction_filter_accepts(
    error: ReconstructionError,
    rejection_threshold: ReconstructionThreshold,
) -> ReconstructionAccepted:
    return error <= rejection_threshold


def reconstruction_filter_reweight(
    accepted_states: tuple[WeightedModelState, ...],
) -> ModelState | None:
    if not accepted_states:
        return None
    return federated_averaging(accepted_states)


def vector_l2_norm(vector: torch.Tensor) -> VectorNorm:
    return float(torch.sqrt(torch.sum(vector.detach() ** 2)))


def l2_normalize(update_vectors: tuple[torch.Tensor, ...]) -> tuple[torch.Tensor, ...]:
    normalized: list[torch.Tensor] = []
    for vector in update_vectors:
        norm = vector_l2_norm(vector)
        normalized.append(vector / norm if norm > 0.0 else vector.clone())
    return tuple(normalized)


def cosine_distance(first: torch.Tensor, second: torch.Tensor) -> PairwiseDistance:
    first_norm = vector_l2_norm(first)
    second_norm = vector_l2_norm(second)
    if first_norm == 0.0 and second_norm == 0.0:
        return 0.0
    if first_norm == 0.0 or second_norm == 0.0:
        return 1.0
    cosine_similarity = float(torch.dot(first.detach(), second.detach())) / (
        first_norm * second_norm
    )
    return 1.0 - max(-1.0, min(1.0, cosine_similarity))


def cosine_distance_matrix(
    update_vectors: tuple[torch.Tensor, ...],
) -> PairwiseDistanceMatrix:
    return tuple(
        tuple(cosine_distance(first, second) for second in update_vectors)
        for first in update_vectors
    )


def _validate_distance_matrix(
    distance_matrix: PairwiseDistanceMatrix,
) -> None:
    size = len(distance_matrix)
    if any(len(row) != size for row in distance_matrix):
        raise ValueError("precomputed distance matrix must be square")


def _dbscan_neighbors(
    point_index: MemberIndex,
    distance_matrix: PairwiseDistanceMatrix,
    epsilon: DbscanEpsilon,
) -> tuple[MemberIndex, ...]:
    return tuple(
        candidate_index
        for candidate_index, distance in enumerate(distance_matrix[point_index])
        if distance <= epsilon
    )


def density_cluster_labels(
    distance_matrix: PairwiseDistanceMatrix,
    config: DensityClusterTrimmedMeanConfig,
) -> tuple[DeterministicInteger, ...]:
    _validate_distance_matrix(distance_matrix)
    labels: list[DeterministicInteger] = [_DBSCAN_UNASSIGNED] * len(distance_matrix)
    next_cluster: DeterministicInteger = 0
    for point_index in range(len(distance_matrix)):
        if labels[point_index] != _DBSCAN_UNASSIGNED:
            continue
        neighbors = _dbscan_neighbors(point_index, distance_matrix, config.dbscan_epsilon)
        if len(neighbors) < config.dbscan_min_samples:
            labels[point_index] = _DBSCAN_NOISE
            continue
        labels[point_index] = next_cluster
        expansion = list(neighbors)
        expansion_index = 0
        while expansion_index < len(expansion):
            candidate = expansion[expansion_index]
            if labels[candidate] == _DBSCAN_NOISE:
                labels[candidate] = next_cluster
            if labels[candidate] == _DBSCAN_UNASSIGNED:
                labels[candidate] = next_cluster
                candidate_neighbors = _dbscan_neighbors(
                    candidate,
                    distance_matrix,
                    config.dbscan_epsilon,
                )
                if len(candidate_neighbors) >= config.dbscan_min_samples:
                    for neighbor in candidate_neighbors:
                        if neighbor not in expansion:
                            expansion.append(neighbor)
            expansion_index += 1
        next_cluster += 1
    return tuple(labels)


def _mean_within_cluster_distance(
    indices: tuple[MemberIndex, ...],
    distance_matrix: PairwiseDistanceMatrix,
) -> PairwiseDistance:
    minimum_pairwise_index_count = 2
    if len(indices) < minimum_pairwise_index_count:
        return 0.0
    pairwise_distances = tuple(
        distance_matrix[first][second]
        for position, first in enumerate(indices)
        for second in indices[position + 1 :]
    )
    return sum(pairwise_distances) / len(pairwise_distances)


def _cluster_members(
    label: DeterministicInteger,
    labels: tuple[DeterministicInteger, ...],
) -> tuple[MemberIndex, ...]:
    return tuple(index for index, observed in enumerate(labels) if observed == label)


def _ordered_cluster_domains(
    domains: tuple[NBaiotDomain, ...],
    indices: tuple[MemberIndex, ...],
) -> tuple[NBaiotDomain, ...]:
    return tuple(
        sorted(
            (domains[index] for index in indices),
            key=NBAIOT_DOMAIN_ORDER.index,
        )
    )


def select_largest_density_cluster(
    domains: tuple[NBaiotDomain, ...],
    labels: tuple[DeterministicInteger, ...],
    distance_matrix: PairwiseDistanceMatrix,
) -> tuple[NBaiotDomain, ...] | None:
    if len(domains) != len(labels) or len(labels) != len(distance_matrix):
        raise ValueError("domains, labels, and distance matrix must have matching sizes")
    cluster_labels = tuple(sorted(frozenset(label for label in labels if label != _DBSCAN_NOISE)))
    if not cluster_labels:
        return None
    clusters = tuple(
        DensityCluster(label=label, member_indices=_cluster_members(label, labels))
        for label in cluster_labels
    )
    selected = min(
        clusters,
        key=lambda cluster: (
            -len(cluster.member_indices),
            _mean_within_cluster_distance(cluster.member_indices, distance_matrix),
            tuple(
                NBAIOT_DOMAIN_ORDER.index(domain)
                for domain in _ordered_cluster_domains(domains, cluster.member_indices)
            ),
        ),
    )
    return _ordered_cluster_domains(domains, selected.member_indices)


def trimmed_mean_aggregate(
    raw_updates: tuple[torch.Tensor, ...],
    minimum_cluster_size_for_trimming: ClusterSize,
    trim_each_tail_count: TrimCount,
) -> torch.Tensor:
    if not raw_updates:
        raise ValueError("trimmed mean requires at least one update")
    stacked = torch.stack(raw_updates, dim=0)
    if stacked.shape[0] < minimum_cluster_size_for_trimming:
        return stacked.mean(dim=0)
    sorted_values, _ = torch.sort(stacked, dim=0)
    upper_bound = sorted_values.shape[0] - trim_each_tail_count
    trimmed = sorted_values[trim_each_tail_count:upper_bound]
    return trimmed.mean(dim=0)


def recovery_alarm_threshold(
    defined_domain_rates: tuple[MetricValue, ...],
    percentile: Percentage,
) -> MetricValue:
    return quantile_type7(tuple(sorted(defined_domain_rates)), percentile / 100.0)


def recovery_rollback_is_triggered(
    supported_macro_f1_drop: MetricResult,
    benign_false_alarm_rate_increase: MetricResult,
    triggered_to_benign_rate: MetricResult,
    materiality_config: MaterialityConfig,
    alarm_threshold: MetricValue,
) -> RecoveryRollbackTriggered:
    if (
        supported_macro_f1_drop.value is not None
        and supported_macro_f1_drop.value
        > materiality_config.supported_macro_f1_noninferiority_margin
    ):
        return True
    if (
        benign_false_alarm_rate_increase.value is not None
        and benign_false_alarm_rate_increase.value
        > materiality_config.benign_false_alarm_rate_noninferiority_margin
    ):
        return True
    return (
        triggered_to_benign_rate.value is not None
        and triggered_to_benign_rate.value > alarm_threshold
    )


def sanitization_clip_bounds(
    calibration_updates: tuple[torch.Tensor, ...],
    coordinate_bound_percentile: Percentage,
) -> torch.Tensor:
    if not calibration_updates:
        raise ValueError("sanitization calibration requires at least one update")
    stacked_absolute = torch.stack(tuple(update.abs() for update in calibration_updates), dim=0)
    probability = coordinate_bound_percentile / 100.0
    bounds = torch.empty(stacked_absolute.shape[1], dtype=stacked_absolute.dtype)
    for coordinate in range(stacked_absolute.shape[1]):
        sorted_values = tuple(float(value) for value in stacked_absolute[:, coordinate])
        bounds[coordinate] = quantile_type7(tuple(sorted(sorted_values)), probability)
    return bounds


def clip_source_update(
    source_update: torch.Tensor,
    clip_bounds: torch.Tensor,
) -> torch.Tensor:
    return torch.clamp(source_update, min=-clip_bounds, max=clip_bounds)


def parameter_similarity(
    row_vector: torch.Tensor,
    other_rows_mean_vector: torch.Tensor,
) -> OptionalParameterSimilarity:
    row_norm = vector_l2_norm(row_vector)
    mean_norm = vector_l2_norm(other_rows_mean_vector)
    if row_norm == 0.0 or mean_norm == 0.0:
        return None
    return float(torch.dot(row_vector.detach(), other_rows_mean_vector.detach())) / (
        row_norm * mean_norm
    )


def parameter_similarity_certifies(
    similarity: OptionalParameterSimilarity,
    minimum_cosine_similarity: Probability,
) -> ParameterSimilarityCertified:
    return similarity is not None and similarity >= minimum_cosine_similarity


def parameter_similarity_certification_row_results(
    committed_rows: tuple[CertifiedReproductionRow, ...],
    config: ParameterSimilarityConfig,
) -> tuple[ParameterSimilarityCertified, ...]:
    if len(committed_rows) < config.required_committed_rows:
        raise ValueError(
            f"parameter-similarity certification requires at least "
            f"{config.required_committed_rows} committed rows, got {len(committed_rows)}"
        )
    results: list[ParameterSimilarityCertified] = []
    for index, row in enumerate(committed_rows):
        other_vectors = tuple(
            other.update_vector
            for position, other in enumerate(committed_rows)
            if position != index
        )
        mean_vector = torch.stack(other_vectors, dim=0).mean(dim=0)
        similarity = parameter_similarity(row.update_vector, mean_vector)
        results.append(parameter_similarity_certifies(similarity, config.cosine_similarity_minimum))
    return tuple(results)


def same_context_verifier_panel(
    reproducer_feature_mean: torch.Tensor,
    eligible_verifier_feature_means: tuple[DomainFeatureMean, ...],
    panel_size: VerifierCount,
) -> tuple[NBaiotDomain, ...]:
    ranked = sorted(
        eligible_verifier_feature_means,
        key=lambda item: (
            vector_l2_norm(item.feature_mean - reproducer_feature_mean),
            NBAIOT_DOMAIN_ORDER.index(item.domain),
        ),
    )
    return tuple(item.domain for item in ranked[:panel_size])
