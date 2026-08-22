import hashlib
from dataclasses import dataclass
from typing import Final

from fedsira.config.schema import CapabilityClaimConfig, EvidenceMinimaConfig
from fedsira.datasets.nbaiot.schema import NBaiotClass
from fedsira.domain.enums import DatasetId
from fedsira.domain.records import (
    ArtifactDigest,
    CanonicalToken,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    Probability,
)
from fedsira.evaluation.records import MetricResult
from fedsira.runtime.determinism import canonical_bytes

CLAIM_IDENTITY_SEPARATOR = "FedSIRA|capability_claim_contract_identity"
SOURCE_DIRECT_PRODUCTION_WEIGHT: Final[NonNegativeFloat] = 0.0
SUPPORTED_NON_TARGET_CLASS_COUNT: Final[int] = 10


@dataclass(frozen=True)
class CapabilityClaimSelector:
    dataset_manifest_hash: ArtifactDigest
    supported_control_role: CanonicalToken


@dataclass(frozen=True)
class CapabilityClaimScope:
    dataset_id: DatasetId
    domain_count: PositiveInt
    feature_schema_hash: ArtifactDigest


@dataclass(frozen=True)
class CapabilityClaimContract:
    selector: CapabilityClaimSelector
    target_class: NBaiotClass
    supported_class_count: PositiveInt
    target_f1_minimum: Probability
    target_f1_gain_over_anchor_minimum: Probability
    supported_macro_f1_drop_maximum: Probability
    benign_false_alarm_rate_increase_maximum: Probability
    scope: CapabilityClaimScope


def build_capability_claim_contract(
    dataset_manifest_hash: ArtifactDigest,
    supported_control_role: CanonicalToken,
    dataset_id: DatasetId,
    domain_count: PositiveInt,
    feature_schema_hash: ArtifactDigest,
    capability_claim_config: CapabilityClaimConfig,
) -> CapabilityClaimContract:
    return CapabilityClaimContract(
        selector=CapabilityClaimSelector(dataset_manifest_hash, supported_control_role),
        target_class=NBaiotClass.GAFGYT_COMBO,
        supported_class_count=SUPPORTED_NON_TARGET_CLASS_COUNT,
        target_f1_minimum=capability_claim_config.target_f1_minimum,
        target_f1_gain_over_anchor_minimum=capability_claim_config.target_f1_gain_over_anchor_minimum,
        supported_macro_f1_drop_maximum=capability_claim_config.supported_macro_f1_drop_maximum,
        benign_false_alarm_rate_increase_maximum=(
            capability_claim_config.benign_false_alarm_rate_increase_maximum
        ),
        scope=CapabilityClaimScope(dataset_id, domain_count, feature_schema_hash),
    )


def compute_claim_identity(contract: CapabilityClaimContract) -> ArtifactDigest:
    digest = hashlib.sha256(
        canonical_bytes(
            CLAIM_IDENTITY_SEPARATOR,
            contract.selector.dataset_manifest_hash,
            contract.selector.supported_control_role,
            contract.target_class.value,
            contract.supported_class_count,
            str(contract.target_f1_minimum),
            str(contract.target_f1_gain_over_anchor_minimum),
            str(contract.supported_macro_f1_drop_maximum),
            str(contract.benign_false_alarm_rate_increase_maximum),
            contract.scope.dataset_id.value,
            contract.scope.domain_count,
            contract.scope.feature_schema_hash,
        )
    ).hexdigest()
    return digest


def reproduction_evidence_is_adequate(
    target_example_count: NonNegativeInt,
    supported_control_example_count: NonNegativeInt,
    evidence_minima: EvidenceMinimaConfig,
) -> bool:
    return (
        target_example_count >= evidence_minima.reproduction_target_examples
        and supported_control_example_count
        >= evidence_minima.reproduction_supported_control_examples
    )


def verification_evidence_is_adequate(
    target_example_count: NonNegativeInt,
    supported_control_example_count: NonNegativeInt,
    evidence_minima: EvidenceMinimaConfig,
) -> bool:
    return (
        target_example_count >= evidence_minima.verification_target_examples
        and supported_control_example_count
        >= evidence_minima.verification_supported_control_examples
    )


def screen_evidence_is_adequate(
    target_example_count: NonNegativeInt, evidence_minima: EvidenceMinimaConfig
) -> bool:
    return target_example_count >= evidence_minima.proposal_screen_target_examples


def capability_claim_contract_passes(
    contract: CapabilityClaimContract,
    target_f1: MetricResult,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
) -> bool:
    if (
        target_f1.value is None
        or target_f1_gain.value is None
        or supported_macro_f1_drop.value is None
        or benign_far_increase.value is None
    ):
        return False
    return (
        target_f1.value >= contract.target_f1_minimum
        and target_f1_gain.value >= contract.target_f1_gain_over_anchor_minimum
        and supported_macro_f1_drop.value <= contract.supported_macro_f1_drop_maximum
        and benign_far_increase.value <= contract.benign_false_alarm_rate_increase_maximum
    )


def validate_source_excluded_production_weight(
    direct_production_weight: NonNegativeFloat,
) -> None:
    if direct_production_weight != SOURCE_DIRECT_PRODUCTION_WEIGHT:
        raise ValueError(
            "source artifact must have zero direct production weight in a source-excluded path"
        )
