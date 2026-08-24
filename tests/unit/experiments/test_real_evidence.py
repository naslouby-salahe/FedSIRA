from pathlib import Path

import pandas
import pytest
import torch

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.acquisition import DiscoveredCsvFile
from fedsira.datasets.nbaiot.materialization import materialize_nbaiot_prepared_views
from fedsira.datasets.nbaiot.preprocessing import NBAIOT_PRIMARY_PREDICTOR_COUNT
from fedsira.datasets.nbaiot.schema import NBAIOT_TRIGGER_FEATURES, NBaiotClass, NBaiotDomain
from fedsira.domain.enums import CapabilityContractScope
from fedsira.domain.records import CanonicalToken
from fedsira.experiments.real_evidence import (
    EpistemicFailureScope,
    RealAnchor,
    RootCauseScope,
    anchor_round_calibration_updates,
    anchor_round_reconstruction_calibration_errors,
    compute_capability_under_specification_summary,
    compute_shared_epistemic_failure_summary,
    evaluate_domain,
    non_source_domains,
    prepared_feature_names,
    real_evidence_available,
    recovery_backdoor_alarm_threshold,
    train_anchor,
    train_centralized_reference_checkpoint,
    train_density_cluster_trimmed_mean_delta,
    train_domain_reproduction_delta,
    train_fedavg_reference_delta,
    train_krum_reference_delta,
    train_local_only_reference_checkpoint,
    train_recovery_after_source_admission_delta,
    train_secure_continual_assessment_delta,
    train_source_update_sanitization_delta,
    train_update_reconstruction_filter_delta,
    triggered_to_benign_rate,
)
from fedsira.experiments.registry import EpistemicFailureType
from fedsira.models.mlp import FedSIRAClassifier, trainable_parameter_count

pytestmark = pytest.mark.skip(
    reason="runs real anchor/reproduction gradient-descent training; skipped by default"
    " to avoid competing for CPU with other work. Re-enable deliberately when verifying"
    " fedsira.experiments.real_evidence."
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
DOMAINS = (
    NBaiotDomain.DANMINI_DOORBELL,
    NBaiotDomain.ENNIO_DOORBELL,
    NBaiotDomain.ECOBEE_THERMOSTAT,
)
CLASSES = (NBaiotClass.BENIGN, NBaiotClass.GAFGYT_COMBO, NBaiotClass.GAFGYT_JUNK)


def _feature_names() -> list[str]:
    names = [f"feature_{index:03d}" for index in range(NBAIOT_PRIMARY_PREDICTOR_COUNT)]
    for index, trigger in enumerate(NBAIOT_TRIGGER_FEATURES):
        names[index] = trigger
    return names


def _write_csv(path: Path, row_count: int, offset: float) -> None:
    frame = pandas.DataFrame(
        {name: [offset + index * 0.001 for index in range(row_count)] for name in _feature_names()}
    )
    frame.to_csv(path, index=False)


def _prepare_real_evidence(root: Path) -> Path:
    discovered: list[DiscoveredCsvFile] = []
    for domain_index, domain in enumerate(DOMAINS):
        for class_index, class_id in enumerate(CLASSES):
            relative_path = f"{class_id.value}.csv"
            absolute_path = root / "raw" / domain.value / relative_path
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            _write_csv(absolute_path, row_count=3000, offset=domain_index + class_index)
            discovered.append(
                DiscoveredCsvFile(
                    domain=domain,
                    class_id=class_id,
                    relative_path=relative_path,
                    file_sha256=f"{domain_index}{class_index}" * 32,
                    absolute_path=absolute_path,
                )
            )
    prepared_root = root / "prepared"
    scaler_root = root / "scaler"
    materialize_nbaiot_prepared_views(
        discovered, CONFIG, prepared_root, scaler_root, overwrite=True
    )
    return prepared_root


@pytest.fixture(scope="module")
def prepared_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _prepare_real_evidence(tmp_path_factory.mktemp("real-evidence"))


@pytest.fixture(scope="module")
def anchor(prepared_root: Path) -> RealAnchor:
    result = train_anchor(prepared_root, CONFIG, master_seed=1)
    assert result is not None
    return result


def test_real_evidence_available_reflects_parquet_presence(
    tmp_path: Path, prepared_root: Path
) -> None:
    assert not real_evidence_available(tmp_path)
    assert real_evidence_available(prepared_root)


def test_train_anchor_produces_a_flat_parameter_vector_of_the_expected_shape(
    anchor: RealAnchor,
) -> None:
    assert anchor.input_width == NBAIOT_PRIMARY_PREDICTOR_COUNT
    expected_parameter_count = trainable_parameter_count(
        FedSIRAClassifier(anchor.input_width, anchor.output_width)
    )
    assert anchor.flat_parameters.shape == (expected_parameter_count,)
    assert torch.isfinite(anchor.flat_parameters).all()


def test_train_anchor_returns_none_without_prepared_data(tmp_path: Path) -> None:
    assert train_anchor(tmp_path, CONFIG, master_seed=1) is None


def test_train_domain_reproduction_delta_is_nonzero_and_finite(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_domain_reproduction_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, domain=DOMAINS[0]
    )
    assert delta is not None
    assert delta.shape == anchor.flat_parameters.shape
    assert torch.isfinite(delta).all()
    assert torch.any(delta != 0.0)


def test_train_domain_reproduction_delta_is_none_without_target_rows(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_domain_reproduction_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, domain=NBaiotDomain.SAMSUNG_WEBCAM
    )
    assert delta is None


def test_evaluate_domain_reports_defined_target_metrics_on_report_test(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    metrics = evaluate_domain(
        prepared_root, anchor, anchor.flat_parameters, DOMAINS[0], Role.REPORT_TEST
    )
    assert metrics is not None
    assert metrics.target_f1.value is not None
    assert metrics.supported_macro_f1.value is not None
    assert metrics.benign_far.value is not None


def test_evaluate_domain_returns_none_without_report_test_rows(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    metrics = evaluate_domain(
        prepared_root,
        anchor,
        anchor.flat_parameters,
        NBaiotDomain.SAMSUNG_WEBCAM,
        Role.REPORT_TEST,
    )
    assert metrics is None


def test_non_source_domains_excludes_only_the_source() -> None:
    domains = non_source_domains(NBaiotDomain.DANMINI_DOORBELL)
    assert NBaiotDomain.DANMINI_DOORBELL not in domains
    assert len(domains) == 8


def test_prepared_feature_names_includes_the_real_trigger_feature_names(
    prepared_root: Path,
) -> None:
    feature_names = prepared_feature_names(prepared_root)
    assert feature_names is not None
    for trigger_feature in NBAIOT_TRIGGER_FEATURES:
        assert trigger_feature in feature_names


def test_prepared_feature_names_returns_none_without_prepared_data(tmp_path: Path) -> None:
    assert prepared_feature_names(tmp_path) is None


def _root_cause_scope(
    feature_names: tuple[CanonicalToken, ...], contract_scope: CapabilityContractScope
) -> RootCauseScope:
    return RootCauseScope(
        contract_scope=contract_scope,
        feature_names=feature_names,
        root_cause_a_feature_name=NBAIOT_TRIGGER_FEATURES[0],
        root_cause_b_feature_name=NBAIOT_TRIGGER_FEATURES[3],
        shift_value=3.0,
    )


def test_train_domain_reproduction_delta_with_root_cause_scope_is_finite(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    feature_names = prepared_feature_names(prepared_root)
    assert feature_names is not None
    scope = _root_cause_scope(feature_names, CapabilityContractScope.BROAD_TARGET_ONLY)
    delta = train_domain_reproduction_delta(
        prepared_root,
        CONFIG,
        master_seed=1,
        anchor=anchor,
        domain=DOMAINS[0],
        root_cause_scope=scope,
    )
    assert delta is not None
    assert torch.isfinite(delta).all()


def test_evaluate_domain_with_root_cause_scope_reports_defined_target_metrics(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    feature_names = prepared_feature_names(prepared_root)
    assert feature_names is not None
    scope = _root_cause_scope(feature_names, CapabilityContractScope.BROAD_TARGET_ONLY)
    metrics = evaluate_domain(
        prepared_root,
        anchor,
        anchor.flat_parameters,
        DOMAINS[0],
        Role.REPORT_TEST,
        root_cause_scope=scope,
    )
    assert metrics is not None
    assert metrics.target_f1.value is not None


def test_compute_capability_under_specification_summary_is_genuinely_computed(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    feature_names = prepared_feature_names(prepared_root)
    assert feature_names is not None
    scope = _root_cause_scope(feature_names, CapabilityContractScope.BROAD_TARGET_ONLY)
    summary = compute_capability_under_specification_summary(
        prepared_root,
        CONFIG,
        master_seed=1,
        anchor=anchor,
        source_domain=None,
        root_cause_scope=scope,
    )
    assert summary.defined_domain_count > 0
    assert summary.aggregate_target_f1.value is not None


def _epistemic_failure_scope(
    feature_names: tuple[CanonicalToken, ...], failure_type: EpistemicFailureType
) -> EpistemicFailureScope:
    return EpistemicFailureScope(
        failure_type=failure_type,
        strength=0.5,
        attack_generation_seed=1,
        feature_names=feature_names,
        spurious_feature_name=NBAIOT_TRIGGER_FEATURES[0],
        spurious_feature_value=6.0,
        common_context_feature_names=NBAIOT_TRIGGER_FEATURES,
        common_context_trigger_value=6.0,
    )


def test_train_domain_reproduction_delta_with_shared_label_error_scope_is_finite(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    feature_names = prepared_feature_names(prepared_root)
    assert feature_names is not None
    scope = _epistemic_failure_scope(feature_names, EpistemicFailureType.SHARED_LABEL_ERROR)
    delta = train_domain_reproduction_delta(
        prepared_root,
        CONFIG,
        master_seed=1,
        anchor=anchor,
        domain=DOMAINS[0],
        epistemic_failure_scope=scope,
    )
    assert delta is not None
    assert torch.isfinite(delta).all()


def test_compute_shared_epistemic_failure_summary_for_label_error_is_genuinely_computed(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    feature_names = prepared_feature_names(prepared_root)
    assert feature_names is not None
    scope = _epistemic_failure_scope(feature_names, EpistemicFailureType.SHARED_LABEL_ERROR)
    summary = compute_shared_epistemic_failure_summary(
        prepared_root,
        CONFIG,
        master_seed=1,
        anchor=anchor,
        source_domain=None,
        epistemic_failure_scope=scope,
    )
    assert summary.defined_domain_count > 0
    assert summary.aggregate_target_f1.value is not None
    assert summary.diagnostic_marker.value is None


def test_compute_shared_epistemic_failure_summary_for_spurious_feature_reports_diagnostic_marker(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    feature_names = prepared_feature_names(prepared_root)
    assert feature_names is not None
    scope = _epistemic_failure_scope(feature_names, EpistemicFailureType.SHARED_SPURIOUS_FEATURE)
    summary = compute_shared_epistemic_failure_summary(
        prepared_root,
        CONFIG,
        master_seed=1,
        anchor=anchor,
        source_domain=None,
        epistemic_failure_scope=scope,
    )
    assert summary.defined_domain_count > 0
    assert summary.diagnostic_marker.value is not None


def test_compute_shared_epistemic_failure_summary_for_common_context_reports_diagnostic_marker(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    feature_names = prepared_feature_names(prepared_root)
    assert feature_names is not None
    scope = _epistemic_failure_scope(
        feature_names, EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT
    )
    summary = compute_shared_epistemic_failure_summary(
        prepared_root,
        CONFIG,
        master_seed=1,
        anchor=anchor,
        source_domain=None,
        epistemic_failure_scope=scope,
    )
    assert summary.defined_domain_count > 0
    assert summary.diagnostic_marker.value is not None


def test_train_fedavg_reference_delta_is_finite_and_nonzero(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_fedavg_reference_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, source_domain=None
    )
    assert delta is not None
    assert delta.shape == anchor.flat_parameters.shape
    assert torch.isfinite(delta).all()
    assert torch.any(delta != 0.0)


def test_train_fedavg_reference_delta_returns_none_without_prepared_data(
    tmp_path: Path, anchor: RealAnchor
) -> None:
    assert (
        train_fedavg_reference_delta(
            tmp_path, CONFIG, master_seed=1, anchor=anchor, source_domain=None
        )
        is None
    )


def test_train_krum_reference_delta_returns_none_with_fewer_than_committee_size_participants(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    assert CONFIG.protocol.synthesis.committee_size > len(DOMAINS)
    delta = train_krum_reference_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, source_domain=None
    )
    assert delta is None


def test_train_krum_reference_delta_returns_none_without_prepared_data(
    tmp_path: Path, anchor: RealAnchor
) -> None:
    assert (
        train_krum_reference_delta(
            tmp_path, CONFIG, master_seed=1, anchor=anchor, source_domain=None
        )
        is None
    )


def test_train_density_cluster_trimmed_mean_delta_is_finite_and_nonzero(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_density_cluster_trimmed_mean_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, source_domain=None
    )
    assert delta is not None
    assert delta.shape == anchor.flat_parameters.shape
    assert torch.isfinite(delta).all()


def test_train_density_cluster_trimmed_mean_delta_returns_none_without_prepared_data(
    tmp_path: Path, anchor: RealAnchor
) -> None:
    assert (
        train_density_cluster_trimmed_mean_delta(
            tmp_path, CONFIG, master_seed=1, anchor=anchor, source_domain=None
        )
        is None
    )


def test_anchor_round_calibration_updates_are_finite_and_match_expected_count(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    updates = anchor_round_calibration_updates(prepared_root, CONFIG, master_seed=1, anchor=anchor)
    assert len(updates) > 0
    assert len(anchor.round_start_flat_parameters) == CONFIG.model.anchor_fedavg.rounds
    for update in updates:
        assert update.shape == anchor.flat_parameters.shape
        assert torch.isfinite(update).all()


def test_train_source_update_sanitization_delta_is_finite_and_clipped(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_source_update_sanitization_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, source_domain=DOMAINS[0]
    )
    assert delta is not None
    assert torch.isfinite(delta).all()


def test_train_source_update_sanitization_delta_returns_none_without_source_domain(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    assert (
        train_source_update_sanitization_delta(
            prepared_root, CONFIG, master_seed=1, anchor=anchor, source_domain=None
        )
        is None
    )


def test_anchor_round_reconstruction_calibration_errors_are_within_expected_count(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    errors = anchor_round_reconstruction_calibration_errors(
        prepared_root, CONFIG, master_seed=1, anchor=anchor
    )
    assert len(errors) > 0
    assert len(errors) <= len(anchor.round_start_flat_parameters) * len(DOMAINS)
    for error in errors:
        assert error >= 0.0


def test_train_update_reconstruction_filter_delta_is_finite(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_update_reconstruction_filter_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, source_domain=None
    )
    assert delta is not None
    assert torch.isfinite(delta).all()


def test_train_update_reconstruction_filter_delta_returns_none_without_prepared_data(
    tmp_path: Path, anchor: RealAnchor
) -> None:
    assert (
        train_update_reconstruction_filter_delta(
            tmp_path, CONFIG, master_seed=1, anchor=anchor, source_domain=None
        )
        is None
    )


def test_recovery_backdoor_alarm_threshold_is_a_finite_rate(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    threshold = recovery_backdoor_alarm_threshold(prepared_root, CONFIG, anchor=anchor)
    assert threshold is not None
    assert 0.0 <= threshold <= 1.0


def test_triggered_to_benign_rate_is_defined_for_gafgyt_udp_rows(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    rate = triggered_to_benign_rate(
        prepared_root,
        anchor,
        anchor.flat_parameters,
        DOMAINS[0],
        Role.ANCHOR_VALIDATION,
        NBAIOT_TRIGGER_FEATURES,
        6.0,
    )
    assert rate.value is not None
    assert 0.0 <= rate.value <= 1.0


def test_train_recovery_after_source_admission_delta_excludes_the_source_domain(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_recovery_after_source_admission_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, source_domain=DOMAINS[0]
    )
    assert delta is not None
    assert torch.isfinite(delta).all()


def test_train_secure_continual_assessment_delta_is_finite_and_nonzero(
    prepared_root: Path, anchor: RealAnchor
) -> None:
    delta = train_secure_continual_assessment_delta(
        prepared_root, CONFIG, master_seed=1, anchor=anchor, source_domain=None
    )
    assert delta is not None
    assert delta.shape == anchor.flat_parameters.shape
    assert torch.isfinite(delta).all()
    assert torch.any(delta != 0.0)


def test_train_secure_continual_assessment_delta_returns_none_without_prepared_data(
    tmp_path: Path, anchor: RealAnchor
) -> None:
    assert (
        train_secure_continual_assessment_delta(
            tmp_path, CONFIG, master_seed=1, anchor=anchor, source_domain=None
        )
        is None
    )


def test_train_local_only_reference_checkpoint_is_finite_and_distinct_per_domain(
    prepared_root: Path,
) -> None:
    first = train_local_only_reference_checkpoint(
        prepared_root, CONFIG, master_seed=1, domain=DOMAINS[0]
    )
    second = train_local_only_reference_checkpoint(
        prepared_root, CONFIG, master_seed=1, domain=DOMAINS[1]
    )
    assert first is not None
    assert second is not None
    assert torch.isfinite(first).all()
    assert torch.isfinite(second).all()
    assert not torch.equal(first, second)


def test_train_local_only_reference_checkpoint_returns_none_without_prepared_data(
    tmp_path: Path,
) -> None:
    assert (
        train_local_only_reference_checkpoint(tmp_path, CONFIG, master_seed=1, domain=DOMAINS[0])
        is None
    )


def test_train_centralized_reference_checkpoint_is_finite(prepared_root: Path) -> None:
    checkpoint = train_centralized_reference_checkpoint(prepared_root, CONFIG, master_seed=1)
    assert checkpoint is not None
    assert torch.isfinite(checkpoint).all()


def test_train_centralized_reference_checkpoint_returns_none_without_prepared_data(
    tmp_path: Path,
) -> None:
    assert train_centralized_reference_checkpoint(tmp_path, CONFIG, master_seed=1) is None
