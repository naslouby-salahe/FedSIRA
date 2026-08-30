from __future__ import annotations

from enum import StrEnum

from fedsira.analysis.comparisons import ComparisonMetric
from fedsira.config.schema import ClaimSupportThresholdsConfig
from fedsira.domain.records import (
    AdmissionCount,
    CapabilityCertificationRate,
    ClaimGateDecision,
    ClaimId,
    ClaimReason,
    ClaimScopeText,
    ComparisonName,
    ExperimentName,
    FamilyWiseAlpha,
    FrozenDomainModel,
    MaterialityDecision,
    MetricName,
    MinimumCompletePairCount,
    PValue,
)
from fedsira.experiments.registry import ClaimFamily


class FinalClaimState(StrEnum):
    SUPPORTED = "Supported"
    PARTIALLY_SUPPORTED = "Partially Supported"
    CONDITIONAL = "Conditional"
    MECHANISM_ONLY = "Mechanism Only"
    NULL_RESULT = "Null Result"
    NOT_SUPPORTED = "Not Supported"
    NOT_TESTED = "Not Tested"


class ClaimDefinition(FrozenDomainModel):
    claim_id: ClaimId
    exact_scoped_claim: ClaimScopeText
    evidence_experiments: tuple[ExperimentName, ...]
    primary_metric: MetricName | None
    required_family: ClaimFamily | None = None


class ClaimStateResult(FrozenDomainModel):
    claim_id: ClaimId
    state: FinalClaimState
    scope: ClaimScopeText
    reason: ClaimReason


class ComparisonPValueEvidence(FrozenDomainModel):
    comparison: ComparisonName
    p_value: PValue | None


class MechanismSurvivalEvidence(FrozenDomainModel):
    family: ClaimFamily
    survived: ClaimGateDecision


class ClaimEvidence(FrozenDomainModel):
    completed_experiments: frozenset[ExperimentName]
    comparison_p_values: tuple[ComparisonPValueEvidence, ...]
    mechanism_survival: tuple[MechanismSurvivalEvidence, ...]
    malicious_admissions: tuple[AdmissionCount, ...]
    legitimate_admissions: tuple[AdmissionCount, ...]
    permanent_singleton_admissions: AdmissionCount
    false_same_capability_rates: tuple[CapabilityCertificationRate, ...]
    clean_oracle_material_degradations: tuple[MaterialityDecision, ...]
    source_exclusion_gate_passed: ClaimGateDecision | None
    heterogeneity_boundary_passes: ClaimGateDecision | None
    secondary_generalization_passes: ClaimGateDecision | None


class ClaimEvidenceRecord(FrozenDomainModel):
    claim_id: ClaimId
    evidence: ClaimEvidence


CLAIM_DEFINITIONS: tuple[ClaimDefinition, ...] = (
    ClaimDefinition(
        claim_id="Unsupported Capability Problem",
        exact_scoped_claim=(
            "The constructed N-BaIoT post-reference capability is unsupported by anchor "
            "training/validation evidence and is exposed under a potentially Byzantine source."
        ),
        evidence_experiments=("Data and Domain Evidence Validation",),
        primary_metric=None,
    ),
    ClaimDefinition(
        claim_id="Pre-Evidence Information Limit",
        exact_scoped_claim=(
            "No trusted positive post-reference support exists before independent evidence "
            "arrives under the equal-distribution transcript premise."
        ),
        evidence_experiments=("Protocol Invariant Validation",),
        primary_metric=None,
    ),
    ClaimDefinition(
        claim_id="Authority Transition",
        exact_scoped_claim=(
            "FedSIRA changes the authority object from a source-model approval decision to "
            "independently constructed and externally re-demonstrated functionality."
        ),
        evidence_experiments=(
            "Protocol Invariant Validation",
            "Source-Artifact Exclusion Necessity",
            "Primary Confirmatory Evaluation",
        ),
        primary_metric=ComparisonMetric.LEGITIMATE_ADMISSION.value,
    ),
    ClaimDefinition(
        claim_id="Direct Source Exclusion",
        exact_scoped_claim=(
            "The source artifact is never an explicit input to honest reproduction training "
            "or source-excluded production synthesis."
        ),
        evidence_experiments=("Protocol Invariant Validation",),
        primary_metric=None,
    ),
    ClaimDefinition(
        claim_id="Conditional Non-Interference",
        exact_scoped_claim=(
            "Conditional on the same fixed Capability Claim Contract and honest authority-path "
            "execution, changing the source artifact does not change honest reproduction or "
            "source-excluded production-update computations."
        ),
        evidence_experiments=("Protocol Invariant Validation",),
        primary_metric=None,
    ),
    ClaimDefinition(
        claim_id="Malicious Source Salvage",
        exact_scoped_claim=(
            "Useful functionality first exposed by a malicious source can be learned without "
            "directly deploying that source artifact when enough independent honest domains "
            "can construct the same capability."
        ),
        evidence_experiments=(
            "Source-Artifact Exclusion Necessity",
            "Primary Confirmatory Evaluation",
        ),
        primary_metric=ComparisonMetric.ATTACK_SUCCESS_RATE.value,
        required_family=ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM,
    ),
    ClaimDefinition(
        claim_id="Proposal Assistance Value",
        exact_scoped_claim=(
            "Proposal assistance materially reduces false launches, reproduction attempts, or "
            "post-evidence overhead without violating the specified safety/liveness constraints."
        ),
        evidence_experiments=("Proposal-Assisted Opening Necessity",),
        primary_metric=ComparisonMetric.FALSE_LAUNCH.value,
        required_family=ClaimFamily.PROPOSAL_SCREEN_NECESSITY,
    ),
    ClaimDefinition(
        claim_id="Plurality Necessity",
        exact_scoped_claim=(
            "More than one independent reproduction is necessary only when the preregistered "
            "plurality comparison defeats the single-reproduction alternative."
        ),
        evidence_experiments=("Single-Reproduction Necessity",),
        primary_metric=ComparisonMetric.MALICIOUS_ADMISSION.value,
        required_family=ClaimFamily.PLURALITY_NECESSITY,
    ),
    ClaimDefinition(
        claim_id="External Verification Necessity",
        exact_scoped_claim=(
            "External reproduction verification is necessary only when its preregistered "
            "comparison defeats direct synthesis from the same committed reproduction "
            "opportunities."
        ),
        evidence_experiments=("External Verification Necessity",),
        primary_metric=ComparisonMetric.MALICIOUS_ADMISSION.value,
        required_family=ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY,
    ),
    ClaimDefinition(
        claim_id="Mechanism Necessity",
        exact_scoped_claim=(
            "Necessity is component-specific and is stated only for proposal assistance, "
            "plurality, or external verification when the corresponding Section 18 survival "
            "rule passes."
        ),
        evidence_experiments=(
            "Proposal-Assisted Opening Necessity",
            "Single-Reproduction Necessity",
            "External Verification Necessity",
        ),
        primary_metric=None,
    ),
    ClaimDefinition(
        claim_id="Byzantine Operating Region",
        exact_scoped_claim=(
            "Security/liveness claims are conditional on the tested f_R=1, f_V=1 primary "
            "profile and are not extrapolated above the declared bound."
        ),
        evidence_experiments=(
            "Compromised-Reproducer Robustness",
            "Compromised-Verifier Robustness",
            "Byzantine-Bound Violation",
        ),
        primary_metric=ComparisonMetric.MALICIOUS_ADMISSION.value,
    ),
    ClaimDefinition(
        claim_id="Safe Dormancy",
        exact_scoped_claim=(
            "A permanent singleton may remain unresolved rather than being falsely authenticated."
        ),
        evidence_experiments=("Evidence Scarcity and Dormancy",),
        primary_metric=ComparisonMetric.LEGITIMATE_ADMISSION.value,
    ),
    ClaimDefinition(
        claim_id="Reproducibility Is Not Truth",
        exact_scoped_claim=(
            "Independent reproducibility can still certify a semantically wrong function under "
            "shared label error, common spurious structure, or attacker-induced common context."
        ),
        evidence_experiments=("Shared Epistemic-Failure Boundary",),
        primary_metric="clean-oracle-target-f1-delta",
    ),
    ClaimDefinition(
        claim_id="Capability-Granularity Boundary",
        exact_scoped_claim=(
            "A broad Capability Claim Contract can create false functional equivalence that a "
            "root-cause-scoped contract avoids on the specified fixture."
        ),
        evidence_experiments=("Capability Under-Specification Boundary",),
        primary_metric=ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE.value,
    ),
    ClaimDefinition(
        claim_id="Heterogeneity Boundary",
        exact_scoped_claim=(
            "FedSIRA's liveness/synthesis claim is restricted to the highest tested "
            "heterogeneity regime satisfying the Section 35 boundary rule."
        ),
        evidence_experiments=("Heterogeneous-Reproduction Boundary",),
        primary_metric=ComparisonMetric.LEGITIMATE_ADMISSION.value,
    ),
    ClaimDefinition(
        claim_id="Information-Arrival Delay",
        exact_scoped_claim=(
            "Part of admission delay is an information-arrival cost; FedSIRA's post-evidence "
            "overhead is separately measurable."
        ),
        evidence_experiments=(
            "Evidence Scarcity and Dormancy",
            "Admission-Delay Decomposition",
        ),
        primary_metric="t_evidence",
    ),
    ClaimDefinition(
        claim_id="Post-Evidence Efficiency",
        exact_scoped_claim=(
            "Efficiency claims are descriptive measurements under the specified "
            "machine/timing contract."
        ),
        evidence_experiments=("Efficiency Measurement",),
        primary_metric="post-evidence-wall-clock",
    ),
    ClaimDefinition(
        claim_id="Secondary Generalization",
        exact_scoped_claim=(
            "The tested mechanism direction extends to the specified CICIoT2023 construction "
            "under synthetic pseudo-domains, without implying real administrative independence."
        ),
        evidence_experiments=("Secondary-Dataset Generalization",),
        primary_metric=ComparisonMetric.TARGET_F1.value,
        required_family=ClaimFamily.SECONDARY_GENERALIZATION,
    ),
    ClaimDefinition(
        claim_id="IoT IDS Application",
        exact_scoped_claim=(
            "The tested mechanism applies to the explicitly specified IoT intrusion-detection "
            "contexts; no broader deployment claim is implied."
        ),
        evidence_experiments=(
            "Data and Domain Evidence Validation",
            "Secondary-Dataset Generalization",
        ),
        primary_metric=None,
    ),
)


def _claim_evidence(
    evidence_records: tuple[ClaimEvidenceRecord, ...],
    claim_id: ClaimId,
) -> ClaimEvidence | None:
    for record in evidence_records:
        if record.claim_id == claim_id:
            return record.evidence
    return None


def _family_survival(
    evidence: ClaimEvidence,
    family: ClaimFamily,
) -> ClaimGateDecision | None:
    for result in evidence.mechanism_survival:
        if result.family is family:
            return result.survived
    return None


def _required_evidence_available(
    definition: ClaimDefinition,
    evidence: ClaimEvidence,
) -> ClaimGateDecision:
    if not all(
        experiment in evidence.completed_experiments
        for experiment in definition.evidence_experiments
    ):
        return False
    if definition.required_family is None:
        return True
    return _family_survival(evidence, definition.required_family) is not None


def derive_claim_states(
    evidence_records: tuple[ClaimEvidenceRecord, ...],
    claim_support_thresholds: ClaimSupportThresholdsConfig,
    minimum_complete_pairs_for_claim_support: MinimumCompletePairCount,
    family_wise_alpha: FamilyWiseAlpha,
) -> tuple[ClaimStateResult, ...]:
    states: list[ClaimStateResult] = []
    for definition in CLAIM_DEFINITIONS:
        evidence = _claim_evidence(evidence_records, definition.claim_id)
        if evidence is None or not _required_evidence_available(definition, evidence):
            states.append(
                ClaimStateResult(
                    claim_id=definition.claim_id,
                    state=FinalClaimState.NOT_TESTED,
                    scope=definition.exact_scoped_claim,
                    reason="required verified evidence is incomplete",
                )
            )
            continue
        states.append(
            ClaimStateResult(
                claim_id=definition.claim_id,
                state=_derive_claim_state(
                    definition,
                    evidence,
                    claim_support_thresholds,
                    minimum_complete_pairs_for_claim_support,
                    family_wise_alpha,
                ),
                scope=definition.exact_scoped_claim,
                reason="mechanically derived from verified evidence",
            )
        )
    return tuple(states)


def _derive_claim_state(
    definition: ClaimDefinition,
    evidence: ClaimEvidence,
    claim_support_thresholds: ClaimSupportThresholdsConfig,
    minimum_complete_pairs_for_claim_support: MinimumCompletePairCount,
    family_wise_alpha: FamilyWiseAlpha,
) -> FinalClaimState:
    claim_id = definition.claim_id
    if claim_id in {
        "Unsupported Capability Problem",
        "Pre-Evidence Information Limit",
        "Direct Source Exclusion",
        "Conditional Non-Interference",
    }:
        return FinalClaimState.SUPPORTED
    if claim_id == "Authority Transition":
        if sum(evidence.legitimate_admissions) >= minimum_complete_pairs_for_claim_support:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if claim_id == "Malicious Source Salvage":
        if evidence.source_exclusion_gate_passed is None:
            return FinalClaimState.NOT_TESTED
        if evidence.source_exclusion_gate_passed:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if claim_id == "Proposal Assistance Value":
        survives = _family_survival(evidence, ClaimFamily.PROPOSAL_SCREEN_NECESSITY)
        if survives is None:
            return FinalClaimState.NOT_TESTED
        return FinalClaimState.SUPPORTED if survives else FinalClaimState.NULL_RESULT
    if claim_id == "Plurality Necessity":
        survives = _family_survival(evidence, ClaimFamily.PLURALITY_NECESSITY)
        if survives is None:
            return FinalClaimState.NOT_TESTED
        return FinalClaimState.SUPPORTED if survives else FinalClaimState.NOT_SUPPORTED
    if claim_id == "External Verification Necessity":
        survives = _family_survival(evidence, ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY)
        if survives is None:
            return FinalClaimState.NOT_TESTED
        return FinalClaimState.SUPPORTED if survives else FinalClaimState.NOT_SUPPORTED
    if claim_id == "Mechanism Necessity":
        families = (
            ClaimFamily.PROPOSAL_SCREEN_NECESSITY,
            ClaimFamily.PLURALITY_NECESSITY,
            ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY,
        )
        survival = tuple(_family_survival(evidence, family) for family in families)
        if any(state is None for state in survival):
            return FinalClaimState.NOT_TESTED
        supported_count = sum(state is True for state in survival)
        if supported_count == len(families):
            return FinalClaimState.SUPPORTED
        if supported_count > 0:
            return FinalClaimState.PARTIALLY_SUPPORTED
        return FinalClaimState.NULL_RESULT
    if claim_id == "Byzantine Operating Region":
        byzantine_thresholds = claim_support_thresholds.byzantine_operating_region
        maximum = byzantine_thresholds.maximum_malicious_admissions_within_bound
        if sum(evidence.malicious_admissions) <= maximum:
            return FinalClaimState.CONDITIONAL
        return FinalClaimState.NOT_SUPPORTED
    if claim_id == "Safe Dormancy":
        maximum = claim_support_thresholds.safe_dormancy.maximum_permanent_singleton_admissions
        if evidence.permanent_singleton_admissions <= maximum:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if claim_id == "Reproducibility Is Not Truth":
        if any(evidence.clean_oracle_material_degradations):
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if claim_id == "Capability-Granularity Boundary":
        if not evidence.false_same_capability_rates:
            return FinalClaimState.NULL_RESULT
        mean_rate = sum(evidence.false_same_capability_rates) / len(
            evidence.false_same_capability_rates
        )
        granularity_thresholds = claim_support_thresholds.capability_granularity_boundary
        minimum = granularity_thresholds.false_same_capability_certification_rate_minimum
        return FinalClaimState.SUPPORTED if mean_rate >= minimum else FinalClaimState.NULL_RESULT
    if claim_id == "Heterogeneity Boundary":
        if evidence.heterogeneity_boundary_passes is None:
            return FinalClaimState.NOT_TESTED
        if evidence.heterogeneity_boundary_passes:
            return FinalClaimState.CONDITIONAL
        return FinalClaimState.NOT_SUPPORTED
    if claim_id in {"Information-Arrival Delay", "Post-Evidence Efficiency"}:
        return FinalClaimState.SUPPORTED
    if claim_id == "Secondary Generalization":
        if evidence.secondary_generalization_passes is None:
            return FinalClaimState.NOT_TESTED
        p_values = tuple(
            item.p_value for item in evidence.comparison_p_values if item.p_value is not None
        )
        if p_values and any(p_value >= family_wise_alpha for p_value in p_values):
            return FinalClaimState.NOT_SUPPORTED
        if evidence.secondary_generalization_passes:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if claim_id == "IoT IDS Application":
        if evidence.secondary_generalization_passes is None:
            return FinalClaimState.PARTIALLY_SUPPORTED
        return FinalClaimState.SUPPORTED
    return FinalClaimState.NOT_TESTED
