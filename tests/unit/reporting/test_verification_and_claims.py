from fedsira.analysis.claims import (
    ClaimEvidence,
    FinalClaimState,
    claim_by_id,
    derive_claim_states,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ExperimentLifecycleState
from fedsira.experiments.planning import build_plan
from fedsira.reporting.verification import (
    CompletenessVerificationResult,
    verify_claim_states_derivable,
    verify_experiments_completed,
    verify_experiments_reached_terminal_state,
    verify_no_stale_ancestors,
    verify_planned_cell_count_satisfied,
)

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)


def test_verify_planned_cell_count_satisfied_matches_plan() -> None:
    plan = build_plan()
    counts = {planned.definition.name: len(planned.cells) for planned in plan.experiments}
    result = verify_planned_cell_count_satisfied(plan, counts)
    assert result.passed
    assert result.failures == ()


def test_verify_planned_cell_count_satisfied_reports_missing_records() -> None:
    plan = build_plan()
    result = verify_planned_cell_count_satisfied(plan, {})
    assert not result.passed
    assert len(result.failures) == len(plan.experiments)


def test_verify_experiments_completed_accepts_only_completed() -> None:
    states = {
        "Data and Domain Evidence Validation": ExperimentLifecycleState.COMPLETED,
        "Protocol Invariant Validation": ExperimentLifecycleState.RUNNING,
    }
    result = verify_experiments_completed(states, ("Data and Domain Evidence Validation",))
    assert result.passed
    failed = verify_experiments_completed(
        states, ("Data and Domain Evidence Validation", "Protocol Invariant Validation")
    )
    assert not failed.passed
    assert "Protocol Invariant Validation" in failed.failures[0]


def test_verify_experiments_reached_terminal_state() -> None:
    states = {
        "Data and Domain Evidence Validation": ExperimentLifecycleState.FAILED,
        "Protocol Invariant Validation": ExperimentLifecycleState.RUNNING,
    }
    result = verify_experiments_reached_terminal_state(
        states, ("Data and Domain Evidence Validation",)
    )
    assert result.passed
    failed = verify_experiments_reached_terminal_state(
        states, ("Data and Domain Evidence Validation", "Protocol Invariant Validation")
    )
    assert not failed.passed


def test_verify_no_stale_ancestors_passes_when_empty() -> None:
    assert verify_no_stale_ancestors(())
    assert not verify_no_stale_ancestors(("stale-artifact",))


def test_verify_claim_states_derivable_matches_count() -> None:
    assert verify_claim_states_derivable(19, 19)
    assert not verify_claim_states_derivable(3, 19)


def test_claim_by_id_returns_registered_definition() -> None:
    definition = claim_by_id("Direct Source Exclusion")
    assert definition.claim_id == "Direct Source Exclusion"
    assert definition.evidence_experiments


def test_claim_by_id_rejects_unknown() -> None:
    try:
        claim_by_id("Not-A-Real-Claim")
    except KeyError:
        return
    raise AssertionError("expected KeyError for unknown claim")


def test_derive_claim_states_missing_evidence_is_not_tested() -> None:
    states = derive_claim_states(
        {},
        CONFIG.metrics_and_statistics.materiality,
        CONFIG.claim_support_thresholds,
        CONFIG.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        CONFIG.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    by_id = {state.claim_id: state for state in states}
    assert all(state.state is FinalClaimState.NOT_TESTED for state in states)
    assert len(by_id) == len(states)


def test_derive_claim_states_incomplete_evidence_is_not_tested() -> None:
    evidence = ClaimEvidence(
        comparison_states={"proposal-survival": "Passed"},
        comparison_p_values={"proposal-survival": 0.001},
        malicious_admissions=(0,),
        legitimate_admissions=(1,),
        permanent_singleton_admissions=0,
        false_same_capability_rates=(),
        clean_oracle_material_degradations=(),
        source_exclusion_gate_passed=None,
        heterogeneity_boundary_passes=None,
        secondary_generalization_passes=None,
    )
    states = derive_claim_states(
        {"Proposal Assistance Value": evidence},
        CONFIG.metrics_and_statistics.materiality,
        CONFIG.claim_support_thresholds,
        CONFIG.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        CONFIG.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    by_id = {state.claim_id: state for state in states}
    assert by_id["Proposal Assistance Value"].state is FinalClaimState.NOT_TESTED


def test_derive_claim_states_unsupported_capability_is_supported_when_evidence_complete() -> None:
    evidence = ClaimEvidence(
        comparison_states={},
        comparison_p_values={},
        malicious_admissions=(0,),
        legitimate_admissions=(1,),
        permanent_singleton_admissions=0,
        false_same_capability_rates=(),
        clean_oracle_material_degradations=(),
        source_exclusion_gate_passed=None,
        heterogeneity_boundary_passes=None,
        secondary_generalization_passes=None,
    )
    states = derive_claim_states(
        {"Unsupported Capability Problem": evidence},
        CONFIG.metrics_and_statistics.materiality,
        CONFIG.claim_support_thresholds,
        CONFIG.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        CONFIG.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    by_id = {state.claim_id: state for state in states}
    assert by_id["Unsupported Capability Problem"].state is FinalClaimState.SUPPORTED


def test_derive_claim_states_direct_source_exclusion_is_structural() -> None:
    evidence = ClaimEvidence(
        comparison_states={},
        comparison_p_values={},
        malicious_admissions=(1,),
        legitimate_admissions=(),
        permanent_singleton_admissions=0,
        false_same_capability_rates=(),
        clean_oracle_material_degradations=(),
        source_exclusion_gate_passed=None,
        heterogeneity_boundary_passes=None,
        secondary_generalization_passes=None,
    )
    states = derive_claim_states(
        {"Direct Source Exclusion": evidence},
        CONFIG.metrics_and_statistics.materiality,
        CONFIG.claim_support_thresholds,
        CONFIG.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        CONFIG.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    by_id = {state.claim_id: state for state in states}
    assert by_id["Direct Source Exclusion"].state is FinalClaimState.SUPPORTED


def test_verification_result_bool_reflects_passed() -> None:
    assert CompletenessVerificationResult(passed=True, failures=())
    assert not CompletenessVerificationResult(passed=False, failures=("x",))
