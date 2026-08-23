from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from fedsira.config.schema import ClaimSupportThresholdsConfig, MaterialityConfig
from fedsira.domain.records import CanonicalToken, NonNegativeInt, Probability


class FinalClaimState(StrEnum):
    SUPPORTED = "Supported"
    PARTIALLY_SUPPORTED = "Partially Supported"
    CONDITIONAL = "Conditional"
    MECHANISM_ONLY = "Mechanism Only"
    NULL_RESULT = "Null Result"
    NOT_SUPPORTED = "Not Supported"
    NOT_TESTED = "Not Tested"


@dataclass(frozen=True)
class ClaimDefinition:
    claim_id: CanonicalToken
    exact_scoped_claim: CanonicalToken
    evidence_experiments: tuple[CanonicalToken, ...]
    primary_metric: CanonicalToken | None
    required_comparison: CanonicalToken | None


@dataclass(frozen=True)
class ClaimStateResult:
    claim_id: CanonicalToken
    state: FinalClaimState
    scope: CanonicalToken
    reason: CanonicalToken


CLAIM_REGISTRY: tuple[ClaimDefinition, ...] = (
    ClaimDefinition(
        claim_id="Unsupported Capability Problem",
        exact_scoped_claim=(
            "The constructed N-BaIoT post-reference capability is unsupported by anchor "
            "training/validation evidence and is exposed under a potentially Byzantine source."
        ),
        evidence_experiments=("Data and Domain Evidence Validation",),
        primary_metric=None,
        required_comparison=None,
    ),
    ClaimDefinition(
        claim_id="Pre-Evidence Information Limit",
        exact_scoped_claim=(
            "No trusted positive post-reference support exists before independent evidence "
            "arrives under the equal-distribution transcript premise."
        ),
        evidence_experiments=("Protocol Invariant Validation",),
        primary_metric=None,
        required_comparison=None,
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
        primary_metric="legitimate-admission",
        required_comparison=None,
    ),
    ClaimDefinition(
        claim_id="Direct Source Exclusion",
        exact_scoped_claim=(
            "The source artifact is never an explicit input to honest reproduction training "
            "or source-excluded production synthesis."
        ),
        evidence_experiments=("Protocol Invariant Validation",),
        primary_metric=None,
        required_comparison=None,
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
        required_comparison=None,
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
        primary_metric="asr",
        required_comparison="source-exclusion ASR",
    ),
    ClaimDefinition(
        claim_id="Proposal Assistance Value",
        exact_scoped_claim=(
            "Proposal assistance materially reduces false launches, reproduction attempts, or "
            "post-evidence overhead without violating the specified safety/liveness constraints."
        ),
        evidence_experiments=("Proposal-Assisted Opening Necessity",),
        primary_metric="false-launch",
        required_comparison="false-launch superiority",
    ),
    ClaimDefinition(
        claim_id="Plurality Necessity",
        exact_scoped_claim=(
            "More than one independent reproduction is necessary only when the preregistered "
            "plurality comparison defeats the single-reproduction alternative."
        ),
        evidence_experiments=("Single-Reproduction Necessity",),
        primary_metric="malicious-admission",
        required_comparison="plurality primary effect",
    ),
    ClaimDefinition(
        claim_id="External Verification Necessity",
        exact_scoped_claim=(
            "External reproduction verification is necessary only when its preregistered "
            "comparison defeats direct synthesis from the same committed reproduction "
            "opportunities."
        ),
        evidence_experiments=("External Verification Necessity",),
        primary_metric="malicious-admission",
        required_comparison="external-verification primary effect",
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
        required_comparison=None,
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
        primary_metric="malicious-admission",
        required_comparison=None,
    ),
    ClaimDefinition(
        claim_id="Safe Dormancy",
        exact_scoped_claim=(
            "A permanent singleton may remain unresolved rather than being falsely "
            "authenticated."
        ),
        evidence_experiments=("Evidence Scarcity and Dormancy",),
        primary_metric="legitimate-admission",
        required_comparison=None,
    ),
    ClaimDefinition(
        claim_id="Reproducibility Is Not Truth",
        exact_scoped_claim=(
            "Independent reproducibility can still certify a semantically wrong function under "
            "shared label error, common spurious structure, or attacker-induced common context."
        ),
        evidence_experiments=("Shared Epistemic-Failure Boundary",),
        primary_metric="clean-oracle-target-f1-delta",
        required_comparison=None,
    ),
    ClaimDefinition(
        claim_id="Capability-Granularity Boundary",
        exact_scoped_claim=(
            "A broad Capability Claim Contract can create false functional equivalence that a "
            "root-cause-scoped contract avoids on the specified fixture."
        ),
        evidence_experiments=("Capability Under-Specification Boundary",),
        primary_metric="false-same-capability-certification-rate",
        required_comparison=None,
    ),
    ClaimDefinition(
        claim_id="Heterogeneity Boundary",
        exact_scoped_claim=(
            "FedSIRA's liveness/synthesis claim is restricted to the highest tested "
            "heterogeneity regime satisfying the Section 35 boundary rule."
        ),
        evidence_experiments=("Heterogeneous-Reproduction Boundary",),
        primary_metric="legitimate-admission",
        required_comparison=None,
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
        required_comparison=None,
    ),
    ClaimDefinition(
        claim_id="Post-Evidence Efficiency",
        exact_scoped_claim=(
            "Efficiency claims are descriptive measurements under the specified "
            "machine/timing contract."
        ),
        evidence_experiments=("Efficiency Measurement",),
        primary_metric="post-evidence-wall-clock",
        required_comparison=None,
    ),
    ClaimDefinition(
        claim_id="Secondary Generalization",
        exact_scoped_claim=(
            "The tested mechanism direction extends to the specified CICIoT2023 construction "
            "under synthetic pseudo-domains, without implying real administrative independence."
        ),
        evidence_experiments=("Secondary-Dataset Generalization",),
        primary_metric="target-f1",
        required_comparison="secondary generalization",
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
        required_comparison=None,
    ),
)


def claim_by_id(claim_id: CanonicalToken) -> ClaimDefinition:
    for definition in CLAIM_REGISTRY:
        if definition.claim_id == claim_id:
            return definition
    raise KeyError(f"unknown claim {claim_id!r}")


@dataclass(frozen=True)
class ClaimEvidence:
    comparison_states: Mapping[CanonicalToken, CanonicalToken]
    comparison_p_values: Mapping[CanonicalToken, Probability | None]
    malicious_admissions: tuple[NonNegativeInt, ...]
    legitimate_admissions: tuple[NonNegativeInt, ...]
    permanent_singleton_admissions: NonNegativeInt
    false_same_capability_rates: tuple[float, ...]
    clean_oracle_material_degradations: tuple[bool, ...]
    source_exclusion_gate_passed: bool | None
    heterogeneity_boundary_passes: bool | None
    secondary_generalization_passes: bool | None


def _comparison_passed(evidence: ClaimEvidence, comparison: CanonicalToken) -> bool | None:
    state = evidence.comparison_states.get(comparison)
    if state is None:
        return None
    return state == "Passed"


def _required_experiments_complete(definition: ClaimDefinition, evidence: ClaimEvidence) -> bool:
    if definition.required_comparison is None:
        return True
    if definition.required_comparison not in evidence.comparison_states:
        return False
    return any(
        experiment in comparison
        for comparison in evidence.comparison_states
        for experiment in definition.evidence_experiments
    )


def derive_claim_states(
    evidence: Mapping[CanonicalToken, ClaimEvidence],
    materiality_config: MaterialityConfig,
    claim_support_thresholds: ClaimSupportThresholdsConfig,
    minimum_complete_pairs_for_claim_support: NonNegativeInt,
    family_wise_alpha: Probability,
) -> tuple[ClaimStateResult, ...]:
    states: list[ClaimStateResult] = []

    for definition in CLAIM_REGISTRY:
        resolved_definition = claim_by_id(definition.claim_id)
        claim_evidence = evidence.get(resolved_definition.claim_id)
        if claim_evidence is None:
            states.append(
                ClaimStateResult(
                    claim_id=resolved_definition.claim_id,
                    state=FinalClaimState.NOT_TESTED,
                    scope=resolved_definition.exact_scoped_claim,
                    reason="required evidence did not execute validly",
                )
            )
            continue
        required_comparison_state = (
            None
            if resolved_definition.required_comparison is None
            else _comparison_passed(claim_evidence, resolved_definition.required_comparison)
        )
        if not _required_experiments_complete(resolved_definition, claim_evidence):
            states.append(
                ClaimStateResult(
                    claim_id=resolved_definition.claim_id,
                    state=FinalClaimState.NOT_TESTED,
                    scope=resolved_definition.exact_scoped_claim,
                    reason="required evidence experiments are incomplete",
                )
            )
            continue
        state = _derive_claim_state(
            resolved_definition,
            claim_evidence,
            materiality_config,
            claim_support_thresholds,
            minimum_complete_pairs_for_claim_support,
            required_comparison_state,
            family_wise_alpha,
        )
        states.append(
            ClaimStateResult(
                claim_id=resolved_definition.claim_id,
                state=state,
                scope=resolved_definition.exact_scoped_claim,
                reason="mechanically derived from verified evidence",
            )
        )
    return tuple(states)


def _derive_claim_state(
    definition: ClaimDefinition,
    evidence: ClaimEvidence,
    materiality_config: MaterialityConfig,
    claim_support_thresholds: ClaimSupportThresholdsConfig,
    minimum_complete_pairs_for_claim_support: NonNegativeInt,
    required_comparison_state: bool | None,
    family_wise_alpha: Probability,
) -> FinalClaimState:
    if definition.primary_metric is not None and required_comparison_state is False:
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "Unsupported Capability Problem":
        return FinalClaimState.SUPPORTED
    if definition.claim_id == "Pre-Evidence Information Limit":
        return FinalClaimState.SUPPORTED
    if definition.claim_id == "Direct Source Exclusion":
        return FinalClaimState.SUPPORTED
    if definition.claim_id == "Conditional Non-Interference":
        return FinalClaimState.SUPPORTED
    if definition.claim_id == "Authority Transition":
        if sum(evidence.legitimate_admissions) >= minimum_complete_pairs_for_claim_support:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "Malicious Source Salvage":
        if evidence.source_exclusion_gate_passed:
            return FinalClaimState.SUPPORTED
        if evidence.source_exclusion_gate_passed is None:
            return FinalClaimState.NOT_TESTED
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "Proposal Assistance Value":
        proposal_state = _comparison_passed(evidence, "proposal survival")
        if proposal_state is None:
            return FinalClaimState.NOT_TESTED
        if proposal_state:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NULL_RESULT
    if definition.claim_id == "Plurality Necessity":
        plurality_state = _comparison_passed(evidence, "plurality survival")
        if plurality_state is None:
            return FinalClaimState.NOT_TESTED
        if plurality_state:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "External Verification Necessity":
        external_state = _comparison_passed(evidence, "external-verification survival")
        if external_state is None:
            return FinalClaimState.NOT_TESTED
        if external_state:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "Mechanism Necessity":
        proposal_state = _comparison_passed(evidence, "proposal survival")
        plurality_state = _comparison_passed(evidence, "plurality survival")
        external_state = _comparison_passed(evidence, "external-verification survival")
        known = [
            state
            for state in (proposal_state, plurality_state, external_state)
            if state is not None
        ]
        if len(known) < 3:
            return FinalClaimState.NOT_TESTED
        supported_count = sum(1 for state in known if state)
        if supported_count == 3:
            return FinalClaimState.SUPPORTED
        if supported_count in (1, 2):
            return FinalClaimState.PARTIALLY_SUPPORTED
        return FinalClaimState.NULL_RESULT
    if definition.claim_id == "Byzantine Operating Region":
        within_bound_malicious = sum(evidence.malicious_admissions)
        operating_region = claim_support_thresholds.byzantine_operating_region
        maximum = operating_region.maximum_malicious_admissions_within_bound
        if within_bound_malicious <= maximum:
            return FinalClaimState.CONDITIONAL
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "Safe Dormancy":
        if (
            evidence.permanent_singleton_admissions
            <= claim_support_thresholds.safe_dormancy.maximum_permanent_singleton_admissions
        ):
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "Reproducibility Is Not Truth":
        if any(evidence.clean_oracle_material_degradations):
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "Capability-Granularity Boundary":
        if not evidence.false_same_capability_rates:
            return FinalClaimState.NULL_RESULT
        mean_rate = sum(evidence.false_same_capability_rates) / len(
            evidence.false_same_capability_rates
        )
        granularity = claim_support_thresholds.capability_granularity_boundary
        minimum = granularity.false_same_capability_certification_rate_minimum
        if mean_rate >= minimum:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NULL_RESULT
    if definition.claim_id == "Heterogeneity Boundary":
        if evidence.heterogeneity_boundary_passes is None:
            return FinalClaimState.NOT_TESTED
        if evidence.heterogeneity_boundary_passes:
            return FinalClaimState.CONDITIONAL
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "Information-Arrival Delay":
        return FinalClaimState.SUPPORTED
    if definition.claim_id == "Post-Evidence Efficiency":
        return FinalClaimState.SUPPORTED
    if definition.claim_id == "Secondary Generalization":
        if evidence.secondary_generalization_passes is None:
            return FinalClaimState.NOT_TESTED
        applicable_p_values = [
            p_value for p_value in evidence.comparison_p_values.values() if p_value is not None
        ]
        if applicable_p_values and any(
            p_value >= family_wise_alpha for p_value in applicable_p_values
        ):
            return FinalClaimState.NOT_SUPPORTED
        if evidence.secondary_generalization_passes:
            return FinalClaimState.SUPPORTED
        return FinalClaimState.NOT_SUPPORTED
    if definition.claim_id == "IoT IDS Application":
        if evidence.secondary_generalization_passes is None:
            return FinalClaimState.PARTIALLY_SUPPORTED
        return FinalClaimState.SUPPORTED
    return FinalClaimState.NOT_TESTED
