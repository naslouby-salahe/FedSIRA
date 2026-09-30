from __future__ import annotations

from fedsira.domain.enums import ClaimId, ClaimState, ComparisonFamily
from fedsira.domain.types import (
    ByzantineOperatingRegionEvidenceVerified,
    FrozenDomainModel,
    SafeDormancyEvidenceVerified,
    TextValue,
)
from fedsira.evaluation.claim_support import (
    ClaimDerivationInputs,
    ClaimSupportEvidence,
    boundary_claim_derivations,
    collapse_decision_matches_family,
)
from fedsira.evaluation.comparisons import (
    ComparisonFamilyResult,
    ComparisonState,
    build_comparison_registry,
)
from fedsira.experiments.collapse import CollapseDecision, CollapseDecisionKind

CLAIM_DECISION_SCHEMA_VERSION: TextValue = "fedsira|claim-decisions|1"
CLAIM_INVENTORY: tuple[ClaimId, ...] = tuple(ClaimId)


class ClaimDecision(FrozenDomainModel):
    claim_id: ClaimId
    state: ClaimState
    basis: TextValue


class ClaimSummary(FrozenDomainModel):
    schema_version: TextValue = CLAIM_DECISION_SCHEMA_VERSION
    decisions: tuple[ClaimDecision, ...]


def _unevaluated_claim_summary() -> ClaimSummary:
    return ClaimSummary(
        decisions=tuple(
            ClaimDecision(
                claim_id=claim_id,
                state=ClaimState.NOT_TESTED,
                basis="Claim-bearing evidence and decision artifacts are not available.",
            )
            for claim_id in CLAIM_INVENTORY
        )
    )


_NECESSITY_EVIDENCE: tuple[
    tuple[ClaimId, CollapseDecisionKind, ComparisonFamily, ClaimState], ...
] = (
    (
        ClaimId.PROPOSAL_ASSISTANCE_VALUE,
        CollapseDecisionKind.PROPOSAL_ASSISTANCE,
        ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
        ClaimState.NULL_RESULT,
    ),
    (
        ClaimId.PLURALITY_NECESSITY,
        CollapseDecisionKind.PLURALITY,
        ComparisonFamily.PLURALITY_NECESSITY,
        ClaimState.NOT_SUPPORTED,
    ),
    (
        ClaimId.EXTERNAL_VERIFICATION_NECESSITY,
        CollapseDecisionKind.EXTERNAL_VERIFICATION,
        ComparisonFamily.EXTERNAL_VERIFICATION_NECESSITY,
        ClaimState.NOT_SUPPORTED,
    ),
)
_NECESSITY_COMPONENT_COUNT = len(_NECESSITY_EVIDENCE)
_NOT_TESTED_BASIS: TextValue = "Claim-bearing evidence and decision artifacts are not available."


def _evidence_for_claim(
    claim_id: ClaimId,
    evidence: list[tuple[ClaimId, ClaimState, TextValue]],
) -> tuple[ClaimState, TextValue]:
    for evidence_id, state, basis in evidence:
        if evidence_id is claim_id:
            return state, basis
    return ClaimState.NOT_TESTED, _NOT_TESTED_BASIS


def claim_summary_from_inputs(inputs: ClaimDerivationInputs) -> ClaimSummary:
    return claim_summary_from_collapse_evidence(
        inputs.collapse_decisions,
        inputs.comparison_results,
        safe_dormancy_verified=inputs.safe_dormancy_verified,
        byzantine_operating_region_verified=inputs.byzantine_operating_region_verified,
        support=inputs.support,
    )


def claim_summary_from_collapse_evidence(
    collapse_decisions: tuple[CollapseDecision, ...] | None,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    *,
    safe_dormancy_verified: SafeDormancyEvidenceVerified = False,
    byzantine_operating_region_verified: ByzantineOperatingRegionEvidenceVerified = False,
    support: ClaimSupportEvidence | None = None,
) -> ClaimSummary:
    derived: list[tuple[ClaimId, ClaimState, TextValue]] = []
    if safe_dormancy_verified:
        derived.append(
            (
                ClaimId.SAFE_DORMANCY,
                ClaimState.SUPPORTED,
                "All registered Evidence Scarcity and Dormancy cells completed; "
                "Permanent Singleton had zero admissions and admission never preceded T_evidence.",
            )
        )
    if byzantine_operating_region_verified:
        derived.append(
            (
                ClaimId.BYZANTINE_OPERATING_REGION,
                ClaimState.CONDITIONAL,
                "All within-bound resolved-core seed evidence passed with zero malicious "
                "admissions and evaluable legitimate/support outcomes.",
            )
        )
    derived.extend(boundary_claim_derivations(collapse_decisions, comparison_results, support))
    if collapse_decisions is None:
        if not derived:
            return _unevaluated_claim_summary()
        return ClaimSummary(
            decisions=tuple(
                ClaimDecision(
                    claim_id=claim_id,
                    state=_evidence_for_claim(claim_id, derived)[0],
                    basis=_evidence_for_claim(claim_id, derived)[1],
                )
                for claim_id in CLAIM_INVENTORY
            )
        )

    valid_states = frozenset((ComparisonState.PASSED, ComparisonState.FAILED))
    for claim_id, kind, family_name, failed_state in _NECESSITY_EVIDENCE:
        decisions = tuple(item for item in collapse_decisions if item.kind is kind)
        families = tuple(item for item in comparison_results if item.family is family_name)
        if len(decisions) != 1 or len(families) != 1:
            continue
        decision = decisions[0]
        family = families[0]
        expected_names = tuple(
            definition.comparison_name
            for definition in build_comparison_registry()
            if definition.family is family_name
        )
        complete = tuple(
            sorted(item.definition.comparison_name for item in family.comparisons)
        ) == tuple(sorted(expected_names)) and all(
            item.comparison_state in valid_states for item in family.comparisons
        )
        if not complete or not collapse_decision_matches_family(decision, family):
            continue
        if decision.survives:
            derived.append(
                (
                    claim_id,
                    ClaimState.SUPPORTED,
                    f"Section 18 survival rule passed; complete {family_name.value} evidence.",
                )
            )
        else:
            derived.append(
                (
                    claim_id,
                    failed_state,
                    "Section 18 survival rule did not pass; "
                    f"complete {family_name.value} evidence.",
                )
            )

    necessity_states = tuple(
        _evidence_for_claim(claim_id, derived)[0]
        for claim_id, _kind, _family, _failed_state in _NECESSITY_EVIDENCE
    )
    supported_count = sum(state is ClaimState.SUPPORTED for state in necessity_states)
    unresolved_count = sum(state is ClaimState.NOT_TESTED for state in necessity_states)
    if supported_count == _NECESSITY_COMPONENT_COUNT:
        mechanism_state = ClaimState.SUPPORTED
    elif supported_count > 0:
        mechanism_state = ClaimState.PARTIALLY_SUPPORTED
    elif unresolved_count == 0 and supported_count == 0:
        mechanism_state = ClaimState.NULL_RESULT
    else:
        mechanism_state = ClaimState.NOT_TESTED
    if mechanism_state is not ClaimState.NOT_TESTED:
        derived.append(
            (
                ClaimId.MECHANISM_NECESSITY,
                mechanism_state,
                "Derived mechanically from the available Section 18 component decisions.",
            )
        )

    return ClaimSummary(
        decisions=tuple(
            ClaimDecision(
                claim_id=claim_id,
                state=_evidence_for_claim(claim_id, derived)[0],
                basis=_evidence_for_claim(claim_id, derived)[1],
            )
            for claim_id in CLAIM_INVENTORY
        )
    )
