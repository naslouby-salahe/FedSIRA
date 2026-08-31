from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.nbaiot.schema import NBAIOT_CLASS_ORDER, NBaiotClass
from fedsira.domain.enums import DatasetId
from fedsira.domain.models import MetricResult
from fedsira.domain.types import ArtifactDigest, ClassCount
from fedsira.protocol.claim_contract import (
    CapabilityClaimContract,
    build_capability_claim_contract,
    capability_claim_contract_passes,
    compute_claim_identity,
    reproduction_evidence_is_adequate,
    screen_evidence_is_adequate,
    validate_source_excluded_production_weight,
    verification_evidence_is_adequate,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
CAPABILITY_CLAIM_CONFIG = CONFIG.capability_claim
EVIDENCE_MINIMA = CAPABILITY_CLAIM_CONFIG.evidence_minima
SUPPORTED_CLASS_COUNT: ClassCount = len(NBAIOT_CLASS_ORDER) - 1


def _contract(
    dataset_manifest_hash: ArtifactDigest = "a" * 64,
    feature_schema_hash: ArtifactDigest = "b" * 64,
) -> CapabilityClaimContract:
    return build_capability_claim_contract(
        dataset_manifest_hash=dataset_manifest_hash,
        supported_control_role="POST_REFERENCE_REPLAY",
        dataset_id=DatasetId.N_BAIOT,
        domain_count=9,
        feature_schema_hash=feature_schema_hash,
        target_class=NBaiotClass.GAFGYT_COMBO.value,
        supported_class_count=SUPPORTED_CLASS_COUNT,
        capability_claim_config=CAPABILITY_CLAIM_CONFIG,
    )


def test_build_capability_claim_contract_uses_dataset_scope_and_configured_thresholds() -> None:
    contract = _contract()
    assert contract.target_class == NBaiotClass.GAFGYT_COMBO.value
    assert contract.supported_class_count == SUPPORTED_CLASS_COUNT
    assert contract.target_f1_minimum == CAPABILITY_CLAIM_CONFIG.target_f1_minimum
    assert (
        contract.benign_false_alarm_rate_increase_maximum
        == CAPABILITY_CLAIM_CONFIG.benign_false_alarm_rate_increase_maximum
    )


def test_compute_claim_identity_is_deterministic() -> None:
    first = compute_claim_identity(_contract())
    second = compute_claim_identity(_contract())
    assert first == second
    assert len(first) == 64


def test_compute_claim_identity_changes_when_dataset_manifest_hash_changes() -> None:
    baseline = compute_claim_identity(_contract())
    changed = compute_claim_identity(_contract(dataset_manifest_hash="c" * 64))
    assert baseline != changed


def test_compute_claim_identity_changes_when_scope_changes() -> None:
    baseline = compute_claim_identity(_contract())
    changed = compute_claim_identity(_contract(feature_schema_hash="d" * 64))
    assert baseline != changed


def test_reproduction_evidence_adequacy_boundary() -> None:
    minimum_target = EVIDENCE_MINIMA.reproduction_target_examples
    minimum_supported = EVIDENCE_MINIMA.reproduction_supported_control_examples
    assert reproduction_evidence_is_adequate(minimum_target, minimum_supported, EVIDENCE_MINIMA)
    assert not reproduction_evidence_is_adequate(
        minimum_target - 1, minimum_supported, EVIDENCE_MINIMA
    )
    assert not reproduction_evidence_is_adequate(
        minimum_target, minimum_supported - 1, EVIDENCE_MINIMA
    )


def test_verification_evidence_adequacy_boundary() -> None:
    minimum_target = EVIDENCE_MINIMA.verification_target_examples
    minimum_supported = EVIDENCE_MINIMA.verification_supported_control_examples
    assert verification_evidence_is_adequate(minimum_target, minimum_supported, EVIDENCE_MINIMA)
    assert not verification_evidence_is_adequate(
        minimum_target - 1, minimum_supported, EVIDENCE_MINIMA
    )


def test_screen_evidence_adequacy_boundary() -> None:
    minimum_target = EVIDENCE_MINIMA.proposal_screen_target_examples
    assert screen_evidence_is_adequate(minimum_target, EVIDENCE_MINIMA)
    assert not screen_evidence_is_adequate(minimum_target - 1, EVIDENCE_MINIMA)


def test_capability_claim_contract_passes_requires_both_gamma_and_beta() -> None:
    contract = _contract()
    passing = capability_claim_contract_passes(
        contract,
        MetricResult(value=contract.target_f1_minimum, denominator=10),
        MetricResult(value=contract.target_f1_gain_over_anchor_minimum, denominator=10),
        MetricResult(value=contract.supported_macro_f1_drop_maximum, denominator=10),
        MetricResult(value=contract.benign_false_alarm_rate_increase_maximum, denominator=10),
    )
    assert passing
    failing_gamma = capability_claim_contract_passes(
        contract,
        MetricResult(value=contract.target_f1_minimum - 0.01, denominator=10),
        MetricResult(value=contract.target_f1_gain_over_anchor_minimum, denominator=10),
        MetricResult(value=contract.supported_macro_f1_drop_maximum, denominator=10),
        MetricResult(value=contract.benign_false_alarm_rate_increase_maximum, denominator=10),
    )
    assert not failing_gamma
    failing_beta = capability_claim_contract_passes(
        contract,
        MetricResult(value=contract.target_f1_minimum, denominator=10),
        MetricResult(value=contract.target_f1_gain_over_anchor_minimum, denominator=10),
        MetricResult(value=contract.supported_macro_f1_drop_maximum + 0.01, denominator=10),
        MetricResult(value=contract.benign_false_alarm_rate_increase_maximum, denominator=10),
    )
    assert not failing_beta


def test_capability_claim_contract_passes_na_metric_is_not_passing() -> None:
    contract = _contract()
    assert not capability_claim_contract_passes(
        contract,
        MetricResult(value=None, denominator=0),
        MetricResult(value=1.0, denominator=10),
        MetricResult(value=0.0, denominator=10),
        MetricResult(value=0.0, denominator=10),
    )


def test_validate_source_excluded_production_weight_rejects_nonzero() -> None:
    validate_source_excluded_production_weight(0.0)
    try:
        validate_source_excluded_production_weight(0.1)
    except ValueError:
        return
    raise AssertionError("expected ValueError for nonzero source production weight")
