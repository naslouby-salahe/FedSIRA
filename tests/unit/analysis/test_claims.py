from fedsira.analysis.claims import (
    CLAIM_REGISTRY,
    ClaimEvidence,
    FinalClaimState,
    claim_by_id,
    derive_claim_states,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config


def test_registry_contains_all_19_section_35_claims() -> None:
    claim_ids = {definition.claim_id for definition in CLAIM_REGISTRY}
    assert claim_ids == {
        "Unsupported Capability Problem",
        "Pre-Evidence Information Limit",
        "Authority Transition",
        "Direct Source Exclusion",
        "Conditional Non-Interference",
        "Malicious Source Salvage",
        "Proposal Assistance Value",
        "Plurality Necessity",
        "External Verification Necessity",
        "Mechanism Necessity",
        "Byzantine Operating Region",
        "Safe Dormancy",
        "Reproducibility Is Not Truth",
        "Capability-Granularity Boundary",
        "Heterogeneity Boundary",
        "Information-Arrival Delay",
        "Post-Evidence Efficiency",
        "Secondary Generalization",
        "IoT IDS Application",
    }


def test_missing_evidence_yields_not_tested() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    states = derive_claim_states(
        {},
        config.metrics_and_statistics.materiality,
        config.claim_support_thresholds,
        config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        config.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    assert all(state.state is FinalClaimState.NOT_TESTED for state in states)


def test_authority_transition_supported_with_9_legitimate_admissions() -> None:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    evidence = ClaimEvidence(
        comparison_states={},
        comparison_p_values={},
        malicious_admissions=(),
        legitimate_admissions=(1,) * 10,
        permanent_singleton_admissions=0,
        false_same_capability_rates=(),
        clean_oracle_material_degradations=(),
        source_exclusion_gate_passed=None,
        heterogeneity_boundary_passes=None,
        secondary_generalization_passes=None,
    )
    states = derive_claim_states(
        {"Authority Transition": evidence},
        config.metrics_and_statistics.materiality,
        config.claim_support_thresholds,
        config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support,
        config.metrics_and_statistics.multiplicity.family_wise_alpha,
    )
    authority = next(state for state in states if state.claim_id == "Authority Transition")
    assert authority.state is FinalClaimState.SUPPORTED


def test_claim_by_id_lookup() -> None:
    assert claim_by_id("Safe Dormancy").claim_id == "Safe Dormancy"
