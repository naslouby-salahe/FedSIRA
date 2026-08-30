from fedsira.analysis.claims import (
    ClaimEvidence,
    ClaimEvidenceRecord,
    ClaimStateResult,
    FinalClaimState,
    derive_claim_states,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.experiments.planning import build_plan
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    ExperimentLifecycleRecord,
    ExperimentTerminalCount,
    verify_claim_states_derivable,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_no_stale_ancestors,
    verify_planned_cell_count_satisfied,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def test_verify_planned_cell_count_satisfied_matches_plan() -> None:
    plan = build_plan()
    counts = tuple(
        ExperimentTerminalCount(
            experiment=planned.definition.name,
            count=len(planned.cells),
        )
        for planned in plan.experiments
    )
    result = verify_planned_cell_count_satisfied(plan, counts)
    assert result.passed
    assert result.failures == ()


def test_verify_planned_cell_count_satisfied_reports_missing_records() -> None:
    plan = build_plan()
    result = verify_planned_cell_count_satisfied(plan, ())
    assert not result.passed
    assert len(result.failures) == len(plan.experiments)


def test_verify_experiments_completed_accepts_only_completed() -> None:
    states = (
        ExperimentLifecycleRecord(
            experiment="Data and Domain Evidence Validation",
            state=ExperimentLifecycleState.COMPLETED,
        ),
        ExperimentLifecycleRecord(
            experiment="Protocol Invariant Validation",
            state=ExperimentLifecycleState.RUNNING,
        ),
    )
    result = verify_experiments_completed(states, ("Data and Domain Evidence Validation",))
    assert result.passed
    failed = verify_experiments_completed(
        states,
        ("Data and Domain Evidence Validation", "Protocol Invariant Validation"),
    )
    assert not failed.passed
    assert "Protocol Invariant Validation" in failed.failures[0]


def test_verify_experiments_reached_terminal_state() -> None:
    states = (
        ExperimentLifecycleRecord(
            experiment="Data and Domain Evidence Validation",
            state=ExperimentLifecycleState.FAILED,
        ),
        ExperimentLifecycleRecord(
            experiment="Protocol Invariant Validation",
            state=ExperimentLifecycleState.RUNNING,
        ),
    )
    result = verify_experiments_reached_terminal_state(
        states,
        ("Data and Domain Evidence Validation",),
    )
    assert result.passed
    failed = verify_experiments_reached_terminal_state(
        states,
        ("Data and Domain Evidence Validation", "Protocol Invariant Validation"),
    )
    assert not failed.passed


def test_verify_no_stale_ancestors_passes_when_empty() -> None:
    assert verify_no_stale_ancestors(()).passed
    assert not verify_no_stale_ancestors(("a" * 64,)).passed


def test_verify_claim_states_derivable_rejects_not_tested_claims() -> None:
    unresolved = (
        ClaimStateResult(
            claim_id="Safe Dormancy",
            state=FinalClaimState.NOT_TESTED,
            scope="scope",
            reason="missing evidence",
        ),
    )
    result = verify_claim_states_derivable(unresolved, 1)
    assert not result.passed
    assert "lack complete verified evidence" in result.failures[0]


def test_verify_claim_states_derivable_accepts_terminal_scientific_outcome() -> None:
    supported = (
        ClaimStateResult(
            claim_id="Safe Dormancy",
            state=FinalClaimState.NULL_RESULT,
            scope="scope",
            reason="verified null result",
        ),
    )
    assert verify_claim_states_derivable(supported, 1).passed


def _base_evidence(completed_experiments: frozenset[str]) -> ClaimEvidence:
    return ClaimEvidence(
        completed_experiments=completed_experiments,
        comparison_p_values=(),
        mechanism_survival=(),
        malicious_admissions=(0,),
        legitimate_admissions=(1,),
        permanent_singleton_admissions=0,
        false_same_capability_rates=(),
        clean_oracle_material_degradations=(),
        source_exclusion_gate_passed=None,
        heterogeneity_boundary_passes=None,
        secondary_generalization_passes=None,
    )


def test_derive_claim_states_missing_evidence_is_not_tested() -> None:
    states = derive_claim_states(
        (),
        CONFIG.claim_support_thresholds,
        CONFIG.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        CONFIG.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    assert all(state.state is FinalClaimState.NOT_TESTED for state in states)
    assert len(frozenset(state.claim_id for state in states)) == len(states)


def test_derive_claim_states_incomplete_evidence_is_not_tested() -> None:
    evidence = _base_evidence(frozenset())
    states = derive_claim_states(
        (ClaimEvidenceRecord(claim_id="Proposal Assistance Value", evidence=evidence),),
        CONFIG.claim_support_thresholds,
        CONFIG.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        CONFIG.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    state = next(item for item in states if item.claim_id == "Proposal Assistance Value")
    assert state.state is FinalClaimState.NOT_TESTED


def test_derive_claim_states_structural_claim_supported_when_evidence_complete() -> None:
    evidence = _base_evidence(frozenset(("Protocol Invariant Validation",)))
    states = derive_claim_states(
        (ClaimEvidenceRecord(claim_id="Direct Source Exclusion", evidence=evidence),),
        CONFIG.claim_support_thresholds,
        CONFIG.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        CONFIG.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    state = next(item for item in states if item.claim_id == "Direct Source Exclusion")
    assert state.state is FinalClaimState.SUPPORTED


def test_verification_result_exposes_explicit_passed_state() -> None:
    assert CompletenessVerificationResult(passed=True, failures=()).passed
    assert not CompletenessVerificationResult(passed=False, failures=("x",)).passed
