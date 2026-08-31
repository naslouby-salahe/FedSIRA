import torch

from fedsira.config.schema import (
    DensityClusterTrimmedMeanConfig,
    MaterialityConfig,
    ParameterSimilarityConfig,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, NBaiotDomain
from fedsira.domain.records import (
    BooleanValue,
    ClusterSize,
    DeterministicInteger,
    DomainCount,
    FederatedRoundCount,
    FiniteFloat,
    FrozenDomainModel,
    MetricValue,
    NonNegativeFloat,
    NonNegativeInt,
    NumericalEpsilon,
    OptionalParameterSimilarity,
    PairwiseDistanceMatrix,
    Percentage,
    PositiveInt,
    Probability,
    ReconstructionError,
    ReconstructionErrorSeries,
    ReconstructionThreshold,
    TensorDomainModel,
    TrimCount,
    VerifierCount,
)
from fedsira.evaluation.aggregation import quantile_type7
from fedsira.evaluation.records import MetricResult
from fedsira.learning.aggregation import ModelState, WeightedModelState, federated_averaging
from fedsira.protocol.synthesis import CertifiedReproductionRow

_DBSCAN_UNASSIGNED: DeterministicInteger = -2
_DBSCAN_NOISE: DeterministicInteger = -1


class DomainFeatureMean(TensorDomainModel):
    domain: NBaiotDomain
    feature_mean: torch.Tensor


class DensityCluster(FrozenDomainModel):
    label: DeterministicInteger
    member_indices: tuple[NonNegativeInt, ...]


def reconstruction_error(
    submitted_update: torch.Tensor,
    reconstructed_update: torch.Tensor,
    normalization_epsilon: NumericalEpsilon,
) -> NonNegativeFloat:
    squared_l2_distance = float(torch.sum((submitted_update - reconstructed_update) ** 2))
    submitted_squared_norm = float(torch.sum(submitted_update**2))
    return squared_l2_distance / (submitted_squared_norm + normalization_epsilon)


def reconstruction_filter_calibration_error_count(
    anchor_round_count: FederatedRoundCount,
    domain_count: DomainCount,
) -> PositiveInt:
    return anchor_round_count * domain_count


def reconstruction_rejection_threshold(
    calibration_errors: ReconstructionErrorSeries,
    calibration_percentile: Percentage,
) -> NonNegativeFloat:
    return quantile_type7(
        tuple(sorted(calibration_errors)),
        calibration_percentile / 100.0,
    )


def reconstruction_filter_accepts(
    error: ReconstructionError,
    rejection_threshold: ReconstructionThreshold,
) -> BooleanValue:
    return error <= rejection_threshold


def reconstruction_filter_reweight(
    accepted_states: tuple[WeightedModelState, ...],
) -> ModelState | None:
    if not accepted_states:
        return None
    return federated_averaging(accepted_states)


def vector_l2_norm(vector: torch.Tensor) -> NonNegativeFloat:
    return float(torch.sqrt(torch.sum(vector**2)))


def l2_normalize(update_vectors: tuple[torch.Tensor, ...]) -> tuple[torch.Tensor, ...]:
    normalized: list[torch.Tensor] = []
    for vector in update_vectors:
        norm = vector_l2_norm(vector)
        normalized.append(vector / norm if norm > 0.0 else vector.clone())
    return tuple(normalized)


def cosine_distance(first: torch.Tensor, second: torch.Tensor) -> NonNegativeFloat:
    first_norm = vector_l2_norm(first)
    second_norm = vector_l2_norm(second)
    if first_norm == 0.0 and second_norm == 0.0:
        return 0.0
    if first_norm == 0.0 or second_norm == 0.0:
        return 1.0
    cosine_similarity = float(torch.dot(first, second)) / (first_norm * second_norm)
    return 1.0 - max(-1.0, min(1.0, cosine_similarity))


def cosine_distance_matrix(
    update_vectors: tuple[torch.Tensor, ...],
) -> tuple[tuple[NonNegativeFloat, ...], ...]:
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
    point_index: NonNegativeInt,
    distance_matrix: PairwiseDistanceMatrix,
    epsilon: NonNegativeFloat,
) -> tuple[NonNegativeInt, ...]:
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
    next_cluster: NonNegativeInt = 0
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
    indices: tuple[NonNegativeInt, ...],
    distance_matrix: PairwiseDistanceMatrix,
) -> NonNegativeFloat:
    if len(indices) < 2:
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
) -> tuple[NonNegativeInt, ...]:
    return tuple(index for index, observed in enumerate(labels) if observed == label)


def _ordered_cluster_domains(
    domains: tuple[NBaiotDomain, ...],
    indices: tuple[NonNegativeInt, ...],
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
) -> BooleanValue:
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
) -> FiniteFloat | None:
    row_norm = vector_l2_norm(row_vector)
    mean_norm = vector_l2_norm(other_rows_mean_vector)
    if row_norm == 0.0 or mean_norm == 0.0:
        return None
    return float(torch.dot(row_vector, other_rows_mean_vector)) / (row_norm * mean_norm)


def parameter_similarity_certifies(
    similarity: OptionalParameterSimilarity,
    minimum_cosine_similarity: Probability,
) -> BooleanValue:
    return similarity is not None and similarity >= minimum_cosine_similarity


def parameter_similarity_certification_row_results(
    committed_rows: tuple[CertifiedReproductionRow, ...],
    config: ParameterSimilarityConfig,
) -> tuple[BooleanValue, ...]:
    if len(committed_rows) < config.required_committed_rows:
        raise ValueError(
            f"parameter-similarity certification requires at least "
            f"{config.required_committed_rows} committed rows, got {len(committed_rows)}"
        )
    results: list[BooleanValue] = []
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
