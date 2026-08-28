import hashlib
from typing import Final

from fedsira.config.schema import CapabilityClaimConfig, EvidenceMinimaConfig
from fedsira.domain.enums import DatasetId
from fedsira.domain.records import (
    ArtifactDigest,
    BenignFalseAlarmRateIncrease,
    CapabilityContractSatisfied,
    ClassCount,
    ClassLabel,
    DatasetManifestDigest,
    DomainCount,
    EvidenceAdequate,
    ExampleCount,
    FeatureSchemaDigest,
    FrozenDomainModel,
    ProductionWeight,
    RoleToken,
    SeedDerivationLabel,
    SupportedMacroF1Drop,
    TargetF1,
    TargetF1Gain,
)
from fedsira.evaluation.records import MetricResult
from fedsira.runtime.determinism import framed_bytes

CLAIM_IDENTITY_SEPARATOR: SeedDerivationLabel = "FedSIRA|capability_claim_contract_identity"
SOURCE_DIRECT_PRODUCTION_WEIGHT: Final[ProductionWeight] = 0.0


class CapabilityClaimSelector(FrozenDomainModel):
    dataset_manifest_hash: DatasetManifestDigest
    supported_control_role: RoleToken


class CapabilityClaimScope(FrozenDomainModel):
    dataset_id: DatasetId
    domain_count: DomainCount
    feature_schema_hash: FeatureSchemaDigest


class CapabilityClaimContract(FrozenDomainModel):
    selector: CapabilityClaimSelector
    target_class: ClassLabel
    supported_class_count: ClassCount
    target_f1_minimum: TargetF1
    target_f1_gain_over_anchor_minimum: TargetF1Gain
    supported_macro_f1_drop_maximum: SupportedMacroF1Drop
    benign_false_alarm_rate_increase_maximum: BenignFalseAlarmRateIncrease
    scope: CapabilityClaimScope


def build_capability_claim_contract(
    dataset_manifest_hash: DatasetManifestDigest,
    supported_control_role: RoleToken,
    dataset_id: DatasetId,
    domain_count: DomainCount,
    feature_schema_hash: FeatureSchemaDigest,
    target_class: ClassLabel,
    supported_class_count: ClassCount,
    capability_claim_config: CapabilityClaimConfig,
) -> CapabilityClaimContract:
    return CapabilityClaimContract(
        selector=CapabilityClaimSelector(
            dataset_manifest_hash=dataset_manifest_hash,
            supported_control_role=supported_control_role,
        ),
        target_class=target_class,
        supported_class_count=supported_class_count,
        target_f1_minimum=capability_claim_config.target_f1_minimum,
        target_f1_gain_over_anchor_minimum=(
            capability_claim_config.target_f1_gain_over_anchor_minimum
        ),
        supported_macro_f1_drop_maximum=capability_claim_config.supported_macro_f1_drop_maximum,
        benign_false_alarm_rate_increase_maximum=(
            capability_claim_config.benign_false_alarm_rate_increase_maximum
        ),
        scope=CapabilityClaimScope(
            dataset_id=dataset_id,
            domain_count=domain_count,
            feature_schema_hash=feature_schema_hash,
        ),
    )


def compute_claim_identity(contract: CapabilityClaimContract) -> ArtifactDigest:
    return hashlib.sha256(
        framed_bytes(
            CLAIM_IDENTITY_SEPARATOR,
            contract.selector.dataset_manifest_hash,
            contract.selector.supported_control_role,
            contract.target_class,
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


def reproduction_evidence_is_adequate(
    target_example_count: ExampleCount,
    supported_control_example_count: ExampleCount,
    evidence_minima: EvidenceMinimaConfig,
) -> EvidenceAdequate:
    return (
        target_example_count >= evidence_minima.reproduction_target_examples
        and supported_control_example_count
        >= evidence_minima.reproduction_supported_control_examples
    )


def verification_evidence_is_adequate(
    target_example_count: ExampleCount,
    supported_control_example_count: ExampleCount,
    evidence_minima: EvidenceMinimaConfig,
) -> EvidenceAdequate:
    return (
        target_example_count >= evidence_minima.verification_target_examples
        and supported_control_example_count
        >= evidence_minima.verification_supported_control_examples
    )


def screen_evidence_is_adequate(
    target_example_count: ExampleCount,
    evidence_minima: EvidenceMinimaConfig,
) -> EvidenceAdequate:
    return target_example_count >= evidence_minima.proposal_screen_target_examples


def capability_claim_contract_passes(
    contract: CapabilityClaimContract,
    target_f1: MetricResult,
    target_f1_gain: MetricResult,
    supported_macro_f1_drop: MetricResult,
    benign_far_increase: MetricResult,
) -> CapabilityContractSatisfied:
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


def validate_source_excluded_production_weight(direct_production_weight: ProductionWeight) -> None:
    if direct_production_weight != SOURCE_DIRECT_PRODUCTION_WEIGHT:
        raise ValueError(
            "source artifact must have zero direct production weight in a source-excluded path"
        )
