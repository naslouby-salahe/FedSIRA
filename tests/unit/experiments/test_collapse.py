from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.config.schema import MaterialityConfig, MultiplicityConfig
from fedsira.domain.enums import ClaimOpeningMode
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    CollapseEvaluationInput,
    evaluate_external_verification_survival,
    evaluate_plurality_survival,
    evaluate_proposal_survival,
    evaluate_source_exclusion_survival,
    materialize_resolved_core,
    resolve_all_eight_cases,
    resolve_core_mapping,
)


def _config() -> tuple[MaterialityConfig, MultiplicityConfig]:
    config = load_scientific_config(PRODUCTION_CONFIG_PATH)
    return config.metrics_and_statistics.materiality, config.metrics_and_statistics.multiplicity


def test_all_eight_cases_have_exact_section_18_7_mapping() -> None:
    cases = resolve_all_eight_cases()
    assert set(cases) == {
        (True, True, True),
        (False, True, True),
        (True, True, False),
        (False, True, False),
        (True, False, True),
        (False, False, True),
        (True, False, False),
        (False, False, False),
    }
    assert cases[(True, True, True)].opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED
    assert (
        cases[(True, True, True)].reproduction_row_requirement
        == "first 5 certified non-source rows"
    )
    assert (
        cases[(True, True, True)].row_verification_mode
        == "ordinary 3-verifier 2-of-3 certification for each row"
    )
    assert cases[(True, True, True)].production_update_rule == "Krum over first 5 certified rows"
    assert cases[(False, True, True)].opening_mode is ClaimOpeningMode.CANDIDATE_FREE
    assert cases[(True, True, False)].row_verification_mode == "none"
    assert cases[(True, True, False)].production_update_rule == "Krum over first 5 committed rows"
    assert (
        cases[(True, False, True)].reproduction_row_requirement
        == "first adequate non-source row that passes one fresh verifier"
    )
    assert cases[(True, False, False)].production_update_rule == "that reproduction update directly"
    assert all(core.final_gate_required for core in cases.values())
    assert all(core.source_excluded for core in cases.values())


def test_resolve_core_mapping_identity_token_matches_prv() -> None:
    assert resolve_core_mapping(True, True, True).identity_token == "P|R|V"
    assert resolve_core_mapping(False, True, True).identity_token == "p|R|V"
    assert resolve_core_mapping(True, True, False).identity_token == "P|R|v"
    assert resolve_core_mapping(False, False, False).identity_token == "p|r|v"


def test_proposal_survival_passes_with_material_effect_and_constraints() -> None:
    materiality, multiplicity = _config()
    evaluation = CollapseEvaluationInput(
        false_launch_reduction=0.20,
        reproduction_attempt_reduction=None,
        post_evidence_overhead_reduction=None,
        proposal_legitimate_admission_degradation=0.01,
        proposal_malicious_admission_worsening=0.0,
        plurality_malicious_admission_reduction=None,
        plurality_worst_domain_target_f1_gain=None,
        plurality_legitimate_admission_degradation=None,
        plurality_supported_harm=None,
        source_exclusion_asr_reduction=None,
        source_exclusion_target_f1_drop=None,
        source_exclusion_supported_harm=None,
        source_exclusion_benign_far_increase=None,
        external_verification_malicious_admission_reduction=None,
        external_verification_worst_domain_target_f1_gain=None,
        external_verification_legitimate_admission_degradation=None,
    )
    decision = evaluate_proposal_survival(
        evaluation,
        materiality,
        multiplicity,
        (("false-launch superiority", 0.001),),
    )
    assert decision.survives
    assert decision.kind is CollapseDecisionKind.PROPOSAL_ASSISTANCE


def test_proposal_survival_fails_without_material_effect() -> None:
    materiality, multiplicity = _config()
    evaluation = CollapseEvaluationInput(
        false_launch_reduction=0.01,
        reproduction_attempt_reduction=None,
        post_evidence_overhead_reduction=None,
        proposal_legitimate_admission_degradation=0.01,
        proposal_malicious_admission_worsening=0.0,
        plurality_malicious_admission_reduction=None,
        plurality_worst_domain_target_f1_gain=None,
        plurality_legitimate_admission_degradation=None,
        plurality_supported_harm=None,
        source_exclusion_asr_reduction=None,
        source_exclusion_target_f1_drop=None,
        source_exclusion_supported_harm=None,
        source_exclusion_benign_far_increase=None,
        external_verification_malicious_admission_reduction=None,
        external_verification_worst_domain_target_f1_gain=None,
        external_verification_legitimate_admission_degradation=None,
    )
    decision = evaluate_proposal_survival(
        evaluation,
        materiality,
        multiplicity,
        (("false-launch superiority", 0.9),),
    )
    assert not decision.survives


def test_plurality_survival_requires_mar_or_worst_domain_gain() -> None:
    materiality, multiplicity = _config()
    evaluation = CollapseEvaluationInput(
        false_launch_reduction=None,
        reproduction_attempt_reduction=None,
        post_evidence_overhead_reduction=None,
        proposal_legitimate_admission_degradation=None,
        proposal_malicious_admission_worsening=None,
        plurality_malicious_admission_reduction=0.20,
        plurality_worst_domain_target_f1_gain=None,
        plurality_legitimate_admission_degradation=0.02,
        plurality_supported_harm=0.01,
        source_exclusion_asr_reduction=None,
        source_exclusion_target_f1_drop=None,
        source_exclusion_supported_harm=None,
        source_exclusion_benign_far_increase=None,
        external_verification_malicious_admission_reduction=None,
        external_verification_worst_domain_target_f1_gain=None,
        external_verification_legitimate_admission_degradation=None,
    )
    decision = evaluate_plurality_survival(
        evaluation,
        materiality,
        multiplicity,
        (("plurality primary effect", 0.001),),
    )
    assert decision.survives


def test_source_exclusion_survival_requires_asr_reduction_and_constraints() -> None:
    materiality, multiplicity = _config()
    evaluation = CollapseEvaluationInput(
        false_launch_reduction=None,
        reproduction_attempt_reduction=None,
        post_evidence_overhead_reduction=None,
        proposal_legitimate_admission_degradation=None,
        proposal_malicious_admission_worsening=None,
        plurality_malicious_admission_reduction=None,
        plurality_worst_domain_target_f1_gain=None,
        plurality_legitimate_admission_degradation=None,
        plurality_supported_harm=None,
        source_exclusion_asr_reduction=0.30,
        source_exclusion_target_f1_drop=0.01,
        source_exclusion_supported_harm=0.01,
        source_exclusion_benign_far_increase=0.005,
        external_verification_malicious_admission_reduction=None,
        external_verification_worst_domain_target_f1_gain=None,
        external_verification_legitimate_admission_degradation=None,
    )
    decision = evaluate_source_exclusion_survival(
        evaluation,
        materiality,
        multiplicity,
        (("source-exclusion ASR", 0.001),),
    )
    assert decision.survives


def test_external_verification_survival_requires_material_reduction() -> None:
    materiality, multiplicity = _config()
    evaluation = CollapseEvaluationInput(
        false_launch_reduction=None,
        reproduction_attempt_reduction=None,
        post_evidence_overhead_reduction=None,
        proposal_legitimate_admission_degradation=None,
        proposal_malicious_admission_worsening=None,
        plurality_malicious_admission_reduction=None,
        plurality_worst_domain_target_f1_gain=None,
        plurality_legitimate_admission_degradation=None,
        plurality_supported_harm=None,
        source_exclusion_asr_reduction=None,
        source_exclusion_target_f1_drop=None,
        source_exclusion_supported_harm=None,
        source_exclusion_benign_far_increase=None,
        external_verification_malicious_admission_reduction=0.15,
        external_verification_worst_domain_target_f1_gain=None,
        external_verification_legitimate_admission_degradation=0.02,
    )
    decision = evaluate_external_verification_survival(
        evaluation,
        materiality,
        multiplicity,
        (("external-verification primary effect", 0.001),),
    )
    assert decision.survives


def test_materialize_resolved_core_uses_decision_states() -> None:
    decisions = (
        CollapseDecision(
            kind=CollapseDecisionKind.PROPOSAL_ASSISTANCE,
            survives=True,
            primary_material_effect="false-launch",
            adjusted_p_value=0.001,
            constraint_passes=True,
            reason="passed",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.PLURALITY,
            survives=True,
            primary_material_effect="malicious-admission",
            adjusted_p_value=0.001,
            constraint_passes=True,
            reason="passed",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
            survives=True,
            primary_material_effect="asr",
            adjusted_p_value=0.001,
            constraint_passes=True,
            reason="passed",
        ),
        CollapseDecision(
            kind=CollapseDecisionKind.EXTERNAL_VERIFICATION,
            survives=True,
            primary_material_effect="malicious-admission",
            adjusted_p_value=0.001,
            constraint_passes=True,
            reason="passed",
        ),
    )
    core = materialize_resolved_core(decisions)
    assert core.identity_token == "P|R|V"
    assert core.direct_source_exclusion_survives
