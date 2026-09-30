from fedsira.domain.enums import ClaimId, ClaimState, ComparisonFamily, OpeningMode
from fedsira.evaluation.comparisons import (
    ComparisonFamilyResult,
    ComparisonResult,
    ComparisonState,
    build_comparison_registry,
)
from fedsira.evaluation.summaries import (
    CLAIM_INVENTORY,
    claim_summary_from_collapse_evidence,
)
from fedsira.experiments.collapse import CollapseDecision, CollapseDecisionKind


def test_claim_summary_without_evidence_emits_exact_canonical_inventory() -> None:
    summary = claim_summary_from_collapse_evidence(None, ())

    assert tuple(decision.claim_id for decision in summary.decisions) == tuple(ClaimId)
    assert len(CLAIM_INVENTORY) == 19
    assert all(decision.state is ClaimState.NOT_TESTED for decision in summary.decisions)
    assert all(
        decision.basis == "Claim-bearing evidence and decision artifacts are not available."
        for decision in summary.decisions
    )


def _collapse_decision(kind: CollapseDecisionKind, survives: bool) -> CollapseDecision:
    family = {
        CollapseDecisionKind.PROPOSAL_ASSISTANCE: ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
        CollapseDecisionKind.PLURALITY: ComparisonFamily.PLURALITY_NECESSITY,
        CollapseDecisionKind.EXTERNAL_VERIFICATION: (
            ComparisonFamily.EXTERNAL_VERIFICATION_NECESSITY
        ),
    }[kind]
    effect = next(
        definition.metric
        for definition in build_comparison_registry()
        if definition.family is family
    )
    return CollapseDecision(
        kind=kind,
        comparator=OpeningMode.CANDIDATE_FREE,
        survives=survives,
        primary_material_effect=effect if survives else None,
        adjusted_p_value=1.0 if survives else None,
        constraint_passes=survives,
        reason="fixture",
    )


def _family_result(family: ComparisonFamily, state: ComparisonState) -> ComparisonFamilyResult:
    definitions = tuple(item for item in build_comparison_registry() if item.family is family)
    return ComparisonFamilyResult(
        family=family,
        comparisons=tuple(
            ComparisonResult(
                definition=definition,
                paired_differences=(0.0,) * 10,
                complete_seed_count=10,
                mean_paired_difference=0.0,
                median_paired_difference=0.0,
                paired_standardized_effect=0.0,
                raw_p_value=1.0,
                adjusted_p_value=1.0,
                confidence_interval=(0.0, 0.0),
                materiality_passes=False,
                comparison_state=state,
            )
            for definition in definitions
        ),
    )


def test_mechanism_claims_derive_from_complete_collapse_evidence() -> None:
    collapse = (
        _collapse_decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True),
        _collapse_decision(CollapseDecisionKind.PLURALITY, False),
        _collapse_decision(CollapseDecisionKind.EXTERNAL_VERIFICATION, True),
    )
    comparisons = (
        _family_result(ComparisonFamily.PROPOSAL_SCREEN_NECESSITY, ComparisonState.PASSED),
        _family_result(ComparisonFamily.PLURALITY_NECESSITY, ComparisonState.FAILED),
        _family_result(
            ComparisonFamily.EXTERNAL_VERIFICATION_NECESSITY,
            ComparisonState.PASSED,
        ),
    )

    summary = claim_summary_from_collapse_evidence(collapse, comparisons)
    states = {decision.claim_id: decision.state for decision in summary.decisions}

    assert states[ClaimId.PROPOSAL_ASSISTANCE_VALUE] is ClaimState.SUPPORTED
    assert states[ClaimId.PLURALITY_NECESSITY] is ClaimState.NOT_SUPPORTED
    assert states[ClaimId.EXTERNAL_VERIFICATION_NECESSITY] is ClaimState.SUPPORTED
    assert states[ClaimId.MECHANISM_NECESSITY] is ClaimState.PARTIALLY_SUPPORTED


def test_inconclusive_necessity_comparison_remains_not_tested() -> None:
    collapse = (_collapse_decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, False),)
    comparisons = (
        _family_result(
            ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
            ComparisonState.INCONCLUSIVE_TECHNICAL,
        ),
    )

    summary = claim_summary_from_collapse_evidence(collapse, comparisons)
    states = {decision.claim_id: decision.state for decision in summary.decisions}

    assert states[ClaimId.PROPOSAL_ASSISTANCE_VALUE] is ClaimState.NOT_TESTED
    assert states[ClaimId.MECHANISM_NECESSITY] is ClaimState.NOT_TESTED


def test_mechanism_partial_state_can_be_resolved_despite_one_missing_component() -> None:
    collapse = (
        _collapse_decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True),
        _collapse_decision(CollapseDecisionKind.PLURALITY, False),
    )
    comparisons = (
        _family_result(ComparisonFamily.PROPOSAL_SCREEN_NECESSITY, ComparisonState.PASSED),
        _family_result(ComparisonFamily.PLURALITY_NECESSITY, ComparisonState.FAILED),
    )

    summary = claim_summary_from_collapse_evidence(collapse, comparisons)
    states = {decision.claim_id: decision.state for decision in summary.decisions}

    assert states[ClaimId.EXTERNAL_VERIFICATION_NECESSITY] is ClaimState.NOT_TESTED
    assert states[ClaimId.MECHANISM_NECESSITY] is ClaimState.PARTIALLY_SUPPORTED


def test_mechanism_partial_state_preserves_two_supported_components_with_one_unresolved() -> None:
    collapse = (
        _collapse_decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True),
        _collapse_decision(CollapseDecisionKind.PLURALITY, True),
    )
    comparisons = (
        _family_result(ComparisonFamily.PROPOSAL_SCREEN_NECESSITY, ComparisonState.PASSED),
        _family_result(ComparisonFamily.PLURALITY_NECESSITY, ComparisonState.PASSED),
    )

    summary = claim_summary_from_collapse_evidence(collapse, comparisons)
    states = {decision.claim_id: decision.state for decision in summary.decisions}

    assert states[ClaimId.EXTERNAL_VERIFICATION_NECESSITY] is ClaimState.NOT_TESTED
    assert states[ClaimId.MECHANISM_NECESSITY] is ClaimState.PARTIALLY_SUPPORTED


def test_mechanism_partial_state_is_narrowed_to_one_supported_unresolved_component() -> None:
    collapse = (_collapse_decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True),)
    comparisons = (
        _family_result(ComparisonFamily.PROPOSAL_SCREEN_NECESSITY, ComparisonState.PASSED),
    )

    summary = claim_summary_from_collapse_evidence(collapse, comparisons)
    states = {decision.claim_id: decision.state for decision in summary.decisions}

    assert states[ClaimId.MECHANISM_NECESSITY] is ClaimState.PARTIALLY_SUPPORTED


def test_partial_comparison_family_does_not_support_a_necessity_claim() -> None:
    collapse = (_collapse_decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True),)
    complete_family = _family_result(
        ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
        ComparisonState.PASSED,
    )
    partial_family = ComparisonFamilyResult(
        family=complete_family.family,
        comparisons=complete_family.comparisons[:1],
    )

    summary = claim_summary_from_collapse_evidence(collapse, (partial_family,))
    states = {decision.claim_id: decision.state for decision in summary.decisions}

    assert states[ClaimId.PROPOSAL_ASSISTANCE_VALUE] is ClaimState.NOT_TESTED


def test_necessity_claim_rejects_a_collapse_metric_absent_from_its_family() -> None:
    decision = _collapse_decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True).model_copy(
        update={"primary_material_effect": "unregistered-metric"}
    )
    family = _family_result(
        ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
        ComparisonState.PASSED,
    )

    summary = claim_summary_from_collapse_evidence((decision,), (family,))
    states = {item.claim_id: item.state for item in summary.decisions}

    assert states[ClaimId.PROPOSAL_ASSISTANCE_VALUE] is ClaimState.NOT_TESTED
    assert states[ClaimId.MECHANISM_NECESSITY] is ClaimState.NOT_TESTED
    valid_decision = _collapse_decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True)
    duplicated = claim_summary_from_collapse_evidence(
        (valid_decision, valid_decision),
        (family,),
    )
    assert (
        next(
            item.state
            for item in duplicated.decisions
            if item.claim_id is ClaimId.PROPOSAL_ASSISTANCE_VALUE
        )
        is ClaimState.NOT_TESTED
    )


def test_structural_claim_states_require_the_report_verifier_evidence() -> None:
    unverified = claim_summary_from_collapse_evidence(None, ())
    verified = claim_summary_from_collapse_evidence(
        None,
        (),
        safe_dormancy_verified=True,
        byzantine_operating_region_verified=True,
    )

    assert (
        next(item.state for item in unverified.decisions if item.claim_id is ClaimId.SAFE_DORMANCY)
        is ClaimState.NOT_TESTED
    )
    assert (
        next(item.state for item in verified.decisions if item.claim_id is ClaimId.SAFE_DORMANCY)
        is ClaimState.SUPPORTED
    )
    assert (
        next(
            item.state
            for item in unverified.decisions
            if item.claim_id is ClaimId.BYZANTINE_OPERATING_REGION
        )
        is ClaimState.NOT_TESTED
    )
    assert (
        next(
            item.state
            for item in verified.decisions
            if item.claim_id is ClaimId.BYZANTINE_OPERATING_REGION
        )
        is ClaimState.CONDITIONAL
    )
