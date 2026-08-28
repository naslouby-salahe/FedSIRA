import pytest
import torch

from fedsira.baselines.calibration import (
    clip_source_update,
    cosine_distance,
    cosine_distance_matrix,
    density_cluster_labels,
    l2_normalize,
    parameter_similarity,
    parameter_similarity_certification_row_results,
    parameter_similarity_certifies,
    reconstruction_error,
    reconstruction_filter_accepts,
    reconstruction_filter_calibration_error_count,
    reconstruction_filter_reweight,
    reconstruction_rejection_threshold,
    recovery_alarm_threshold,
    recovery_rollback_is_triggered,
    same_context_verifier_panel,
    sanitization_clip_bounds,
    select_largest_density_cluster,
    trimmed_mean_aggregate,
    vector_l2_norm,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.evaluation.records import MetricResult
from fedsira.protocol.synthesis import CertifiedReproductionRow

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
BASELINES_CONFIG = CONFIG.baselines
MATERIALITY_CONFIG = CONFIG.metrics_and_statistics.materiality
TOLERANCE = 1e-9


def test_reconstruction_error_zero_when_updates_match() -> None:
    update = torch.tensor([1.0, 2.0, 3.0])
    assert abs(reconstruction_error(update, update, 1e-12)) < TOLERANCE


def test_reconstruction_error_matches_normalized_squared_l2_distance() -> None:
    submitted = torch.tensor([1.0, 0.0])
    reconstructed = torch.tensor([0.0, 0.0])
    error = reconstruction_error(submitted, reconstructed, 0.0)
    assert abs(error - 1.0) < TOLERANCE


def test_reconstruction_filter_calibration_error_count_matches_roadmap_worked_example() -> None:
    assert reconstruction_filter_calibration_error_count(20, 9) == 180


def test_reconstruction_rejection_threshold_and_accepts() -> None:
    errors = [0.1, 0.2, 0.3, 0.4, 0.5]
    threshold = reconstruction_rejection_threshold(errors, 95.0)
    assert reconstruction_filter_accepts(threshold, threshold) is True
    assert reconstruction_filter_accepts(threshold + 1.0, threshold) is False


def test_reconstruction_filter_reweight_none_when_all_rejected() -> None:
    assert reconstruction_filter_reweight([], []) is None


def test_reconstruction_filter_reweight_averages_accepted_only() -> None:
    accepted = [{"w": torch.tensor([1.0])}, {"w": torch.tensor([3.0])}]
    result = reconstruction_filter_reweight(accepted, [1, 1])
    assert result is not None
    assert torch.allclose(result["w"], torch.tensor([2.0]))


def test_vector_l2_norm() -> None:
    assert abs(vector_l2_norm(torch.tensor([3.0, 4.0])) - 5.0) < TOLERANCE


def test_l2_normalize_handles_zero_vector() -> None:
    vectors = [torch.tensor([3.0, 4.0]), torch.zeros(2)]
    normalized = l2_normalize(vectors)
    assert abs(vector_l2_norm(normalized[0]) - 1.0) < TOLERANCE
    assert torch.equal(normalized[1], torch.zeros(2))


def test_cosine_distance_zero_vector_semantics() -> None:
    zero = torch.zeros(3)
    nonzero = torch.tensor([1.0, 0.0, 0.0])
    assert abs(cosine_distance(zero, zero)) < TOLERANCE
    assert abs(cosine_distance(zero, nonzero) - 1.0) < TOLERANCE
    assert abs(cosine_distance(nonzero, nonzero)) < TOLERANCE


def test_cosine_distance_is_never_negative_for_near_parallel_vectors() -> None:
    base = torch.tensor([1.0, 2.0, 3.0])
    scaled = base * (1.0 + 1e-8)
    assert cosine_distance(base, scaled) >= 0.0


def test_cosine_distance_matrix_is_symmetric_with_zero_diagonal() -> None:
    vectors = [torch.tensor([1.0, 0.0]), torch.tensor([0.0, 1.0])]
    matrix = cosine_distance_matrix(vectors)
    assert abs(matrix[0][0]) < TOLERANCE
    assert abs(matrix[0][1] - matrix[1][0]) < TOLERANCE
    assert abs(matrix[0][1] - 1.0) < TOLERANCE


def test_density_cluster_labels_and_select_largest_cluster() -> None:
    domains = NBAIOT_DOMAIN_ORDER[:5]
    vectors = [
        torch.tensor([1.0, 0.0]),
        torch.tensor([0.99, 0.01]),
        torch.tensor([0.98, 0.02]),
        torch.tensor([0.0, 1.0]),
        torch.tensor([-1.0, 0.0]),
    ]
    matrix = cosine_distance_matrix(vectors)
    labels = density_cluster_labels(matrix, BASELINES_CONFIG.density_cluster_trimmed_mean)
    largest = select_largest_density_cluster(domains, labels, matrix)
    assert largest is not None
    assert set(largest).issubset(set(domains))
    assert largest == tuple(sorted(largest))


def test_select_largest_density_cluster_none_when_all_noise() -> None:
    labels = (-1, -1, -1)
    assert select_largest_density_cluster(NBAIOT_DOMAIN_ORDER[:3], labels, [[0.0] * 3] * 3) is None


def test_trimmed_mean_aggregate_trims_when_cluster_large_enough() -> None:
    updates = [torch.tensor([1.0]), torch.tensor([2.0]), torch.tensor([100.0])]
    result = trimmed_mean_aggregate(updates, 3, 1)
    assert torch.allclose(result, torch.tensor([2.0]))


def test_trimmed_mean_aggregate_uses_plain_mean_below_minimum_cluster_size() -> None:
    updates = [torch.tensor([1.0]), torch.tensor([3.0])]
    result = trimmed_mean_aggregate(updates, 3, 1)
    assert torch.allclose(result, torch.tensor([2.0]))


def test_recovery_alarm_threshold_and_rollback_trigger_paths() -> None:
    threshold = recovery_alarm_threshold([0.0, 0.1, 0.2, 0.9], 95.0)
    supported_drop = MetricResult(0.5, 100)
    assert (
        recovery_rollback_is_triggered(
            supported_drop,
            MetricResult(0.0, 100),
            MetricResult(0.0, 100),
            MATERIALITY_CONFIG,
            threshold,
        )
        is True
    )
    ok = MetricResult(0.0, 100)
    assert (
        recovery_rollback_is_triggered(
            ok, ok, MetricResult(0.0, 100), MATERIALITY_CONFIG, threshold
        )
        is False
    )


def test_sanitization_clip_bounds_and_clip_source_update() -> None:
    calibration_updates = [torch.tensor([1.0, -1.0]), torch.tensor([2.0, -2.0])]
    bounds = sanitization_clip_bounds(calibration_updates, 95.0)
    source_update = torch.tensor([10.0, -10.0])
    clipped = clip_source_update(source_update, bounds)
    assert torch.all(clipped <= bounds)
    assert torch.all(clipped >= -bounds)


def test_parameter_similarity_na_on_zero_norm() -> None:
    assert parameter_similarity(torch.zeros(3), torch.tensor([1.0, 0.0, 0.0])) is None
    assert parameter_similarity_certifies(None, 0.9) is False


def test_parameter_similarity_certifies_at_threshold() -> None:
    same = torch.tensor([1.0, 0.0])
    similarity = parameter_similarity(same, same)
    assert similarity is not None
    assert abs(similarity - 1.0) < TOLERANCE
    assert parameter_similarity_certifies(1.0, 0.9) is True
    assert parameter_similarity_certifies(0.5, 0.9) is False


def test_parameter_similarity_certification_requires_five_committed_rows() -> None:
    rows = tuple(
        CertifiedReproductionRow(
            reproducer_domain=domain,
            update_vector=torch.tensor([1.0, 0.0]),
        )
        for domain in NBAIOT_DOMAIN_ORDER[:4]
    )
    with pytest.raises(ValueError):
        parameter_similarity_certification_row_results(rows, BASELINES_CONFIG.parameter_similarity)


def test_parameter_similarity_certification_row_results_with_five_rows() -> None:
    rows = tuple(
        CertifiedReproductionRow(
            reproducer_domain=domain,
            update_vector=torch.tensor([1.0, 0.0]),
        )
        for domain in NBAIOT_DOMAIN_ORDER[:5]
    )
    results = parameter_similarity_certification_row_results(
        rows, BASELINES_CONFIG.parameter_similarity
    )
    assert results == (True, True, True, True, True)


def test_same_context_verifier_panel_orders_by_distance_then_domain_id() -> None:
    reproducer_mean = torch.zeros(2)
    feature_means = {
        NBAIOT_DOMAIN_ORDER[0]: torch.tensor([0.1, 0.0]),
        NBAIOT_DOMAIN_ORDER[1]: torch.tensor([0.1, 0.0]),
        NBAIOT_DOMAIN_ORDER[2]: torch.tensor([1.0, 0.0]),
        NBAIOT_DOMAIN_ORDER[3]: torch.tensor([2.0, 0.0]),
    }
    panel = same_context_verifier_panel(reproducer_mean, feature_means, 3)
    assert panel == (NBAIOT_DOMAIN_ORDER[0], NBAIOT_DOMAIN_ORDER[1], NBAIOT_DOMAIN_ORDER[2])
