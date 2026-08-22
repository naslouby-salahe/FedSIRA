from collections.abc import Mapping, Sequence

import torch
from sklearn.cluster import DBSCAN

from fedsira.config.schema import (
    DensityClusterTrimmedMeanConfig,
    MaterialityConfig,
    ParameterSimilarityConfig,
)
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER, NBaiotDomain
from fedsira.domain.records import (
    NonNegativeFloat,
    NonNegativeInt,
    Percentage,
    PositiveInt,
    Probability,
)
from fedsira.evaluation.aggregation import quantile_type7
from fedsira.evaluation.records import MetricResult
from fedsira.learning.aggregation import federated_averaging
from fedsira.protocol.synthesis import CertifiedReproductionRow


def reconstruction_error(
    submitted_update: torch.Tensor,
    reconstructed_update: torch.Tensor,
    normalization_epsilon: NonNegativeFloat,
) -> float:
    squared_l2_distance = float(torch.sum((submitted_update - reconstructed_update) ** 2))
    submitted_squared_norm = float(torch.sum(submitted_update**2))
    return squared_l2_distance / (submitted_squared_norm + normalization_epsilon)


def reconstruction_filter_calibration_error_count(
    anchor_round_count: PositiveInt, domain_count: PositiveInt
) -> PositiveInt:
    return anchor_round_count * domain_count


def reconstruction_rejection_threshold(
    calibration_errors: Sequence[float], calibration_percentile: Percentage
) -> float:
    return quantile_type7(sorted(calibration_errors), calibration_percentile / 100.0)


def reconstruction_filter_accepts(error: float, rejection_threshold: float) -> bool:
    return error <= rejection_threshold


def reconstruction_filter_reweight(
    accepted_state_dicts: Sequence[Mapping[str, torch.Tensor]],
    accepted_example_counts: Sequence[PositiveInt],
) -> dict[str, torch.Tensor] | None:
    if len(accepted_state_dicts) == 0:
        return None
    return federated_averaging(accepted_state_dicts, accepted_example_counts)


def vector_l2_norm(vector: torch.Tensor) -> float:
    return float(torch.sqrt(torch.sum(vector**2)))


def l2_normalize(update_vectors: Sequence[torch.Tensor]) -> tuple[torch.Tensor, ...]:
    normalized: list[torch.Tensor] = []
    for vector in update_vectors:
        norm = vector_l2_norm(vector)
        normalized.append(vector / norm if norm > 0.0 else vector.clone())
    return tuple(normalized)


def cosine_distance(first: torch.Tensor, second: torch.Tensor) -> float:
    first_norm = vector_l2_norm(first)
    second_norm = vector_l2_norm(second)
    if first_norm == 0.0 and second_norm == 0.0:
        return 0.0
    if first_norm == 0.0 or second_norm == 0.0:
        return 1.0
    cosine_similarity = float(torch.dot(first, second)) / (first_norm * second_norm)
    return 1.0 - cosine_similarity


def cosine_distance_matrix(update_vectors: Sequence[torch.Tensor]) -> tuple[tuple[float, ...], ...]:
    return tuple(
        tuple(cosine_distance(first, second) for second in update_vectors)
        for first in update_vectors
    )


def density_cluster_labels(
    distance_matrix: Sequence[Sequence[float]], config: DensityClusterTrimmedMeanConfig
) -> tuple[int, ...]:
    model = DBSCAN(
        eps=config.dbscan_epsilon, min_samples=config.dbscan_min_samples, metric="precomputed"
    )
    labels = model.fit_predict([list(row) for row in distance_matrix])
    return tuple(int(label) for label in labels)


def _mean_within_cluster_distance(
    indices: Sequence[int], distance_matrix: Sequence[Sequence[float]]
) -> float:
    if len(indices) < 2:
        return 0.0
    pairwise_distances = [
        distance_matrix[first][second]
        for position, first in enumerate(indices)
        for second in indices[position + 1 :]
    ]
    return sum(pairwise_distances) / len(pairwise_distances)


def select_largest_density_cluster(
    domains: Sequence[NBaiotDomain],
    labels: Sequence[int],
    distance_matrix: Sequence[Sequence[float]],
) -> tuple[NBaiotDomain, ...] | None:
    clusters: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        if label == -1:
            continue
        clusters.setdefault(label, []).append(index)
    if not clusters:
        return None
    canonical_members = {
        label: tuple(sorted(domains[index] for index in indices))
        for label, indices in clusters.items()
    }
    ranked = sorted(
        clusters.items(),
        key=lambda item: (
            -len(item[1]),
            _mean_within_cluster_distance(item[1], distance_matrix),
            canonical_members[item[0]],
        ),
    )
    return canonical_members[ranked[0][0]]


def trimmed_mean_aggregate(
    raw_updates: Sequence[torch.Tensor],
    minimum_cluster_size_for_trimming: PositiveInt,
    trim_each_tail_count: NonNegativeInt,
) -> torch.Tensor:
    stacked = torch.stack(list(raw_updates), dim=0)
    if stacked.shape[0] < minimum_cluster_size_for_trimming:
        return stacked.mean(dim=0)
    sorted_values, _ = torch.sort(stacked, dim=0)
    trimmed = sorted_values[trim_each_tail_count : sorted_values.shape[0] - trim_each_tail_count]
    return trimmed.mean(dim=0)


def recovery_alarm_threshold(
    defined_domain_rates: Sequence[float], percentile: Percentage
) -> float:
    return quantile_type7(sorted(defined_domain_rates), percentile / 100.0)


def recovery_rollback_is_triggered(
    supported_macro_f1_drop: MetricResult,
    benign_false_alarm_rate_increase: MetricResult,
    triggered_to_benign_rate: MetricResult,
    materiality_config: MaterialityConfig,
    alarm_threshold: float,
) -> bool:
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
    calibration_updates: Sequence[torch.Tensor], coordinate_bound_percentile: Percentage
) -> torch.Tensor:
    stacked_absolute = torch.stack([update.abs() for update in calibration_updates], dim=0)
    probability = coordinate_bound_percentile / 100.0
    bounds = torch.empty(stacked_absolute.shape[1], dtype=stacked_absolute.dtype)
    for coordinate in range(stacked_absolute.shape[1]):
        sorted_values = sorted(float(value) for value in stacked_absolute[:, coordinate])
        bounds[coordinate] = quantile_type7(sorted_values, probability)
    return bounds


def clip_source_update(source_update: torch.Tensor, clip_bounds: torch.Tensor) -> torch.Tensor:
    return torch.clamp(source_update, min=-clip_bounds, max=clip_bounds)


def parameter_similarity(
    row_vector: torch.Tensor, other_rows_mean_vector: torch.Tensor
) -> float | None:
    row_norm = vector_l2_norm(row_vector)
    mean_norm = vector_l2_norm(other_rows_mean_vector)
    if row_norm == 0.0 or mean_norm == 0.0:
        return None
    return float(torch.dot(row_vector, other_rows_mean_vector)) / (row_norm * mean_norm)


def parameter_similarity_certifies(
    similarity: float | None, minimum_cosine_similarity: Probability
) -> bool:
    if similarity is None:
        return False
    return similarity >= minimum_cosine_similarity


def parameter_similarity_certification_row_results(
    committed_rows: Sequence[CertifiedReproductionRow], config: ParameterSimilarityConfig
) -> tuple[bool, ...]:
    if len(committed_rows) < config.required_committed_rows:
        raise ValueError(
            f"parameter-similarity certification requires at least "
            f"{config.required_committed_rows} committed rows, got {len(committed_rows)}"
        )
    results: list[bool] = []
    for index, row in enumerate(committed_rows):
        other_vectors = [
            other.update_vector
            for position, other in enumerate(committed_rows)
            if position != index
        ]
        mean_vector = torch.stack(other_vectors, dim=0).mean(dim=0)
        similarity = parameter_similarity(row.update_vector, mean_vector)
        results.append(parameter_similarity_certifies(similarity, config.cosine_similarity_minimum))
    return tuple(results)


def same_context_verifier_panel(
    reproducer_feature_mean: torch.Tensor,
    eligible_verifier_feature_means: Mapping[NBaiotDomain, torch.Tensor],
    panel_size: PositiveInt,
) -> tuple[NBaiotDomain, ...]:
    domain_index = {domain: index for index, domain in enumerate(NBAIOT_DOMAIN_ORDER)}
    ranked = sorted(
        eligible_verifier_feature_means.items(),
        key=lambda item: (
            vector_l2_norm(item[1] - reproducer_feature_mean),
            domain_index[item[0]],
        ),
    )
    return tuple(domain for domain, _ in ranked[:panel_size])
