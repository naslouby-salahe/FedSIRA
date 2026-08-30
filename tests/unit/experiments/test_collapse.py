from pathlib import Path

from fedsira.analysis.comparisons import (
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonResult,
    ComparisonState,
    build_comparison_registry,
)
from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import ClaimOpeningMode
from fedsira.experiments.collapse import (
    CollapseDecision,
    CollapseDecisionKind,
    CollapseEvaluationInput,
    ProductionUpdateRule,
    ReproductionRowRequirement,
    RowVerificationMode,
    collapse_decision_from_comparison_families,
    materialize_resolved_core,
    publish_resolved_core,
    read_resolved_core,
    resolve_all_eight_cases,
    resolve_core_mapping,
)
from fedsira.experiments.registry import ClaimFamily

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
MATERIALITY = CONFIG.metrics_and_statistics.materiality


def _definition(family: ClaimFamily, metric: ComparisonMetric):
    return next(
        definition
        for definition in build_comparison_registry(CONFIG)
        if definition.family is family and definition.metric is metric
    )


def _passed_family(
    family: ClaimFamily,
    metric: ComparisonMetric,
) -> tuple[ComparisonFamilyResult, ...]:
    definition = _definition(family, metric)
    result = ComparisonResult(
        definition=definition,
        paired_differences=(0.2,) * 10,
        complete_seed_count=10,
        mean_paired_difference=0.2,
        median_paired_difference=0.2,
        paired_standardized_effect=1.0,
        raw_p_value=0.001,
        adjusted_p_value=0.001,
        confidence_interval=(0.1, 0.3),
        materiality_passes=True,
        comparison_state=ComparisonState.PASSED,
    )
    return (ComparisonFamilyResult(family=family, comparisons=(result,)),)


def _failed_family(
    family: ClaimFamily,
    metric: ComparisonMetric,
) -> tuple[ComparisonFamilyResult, ...]:
    definition = _definition(family, metric)
    result = ComparisonResult(
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
        comparison_state=ComparisonState.FAILED,
    )
    return (ComparisonFamilyResult(family=family, comparisons=(result,)),)


def _evaluation(
    *,
    proposal_legitimate: float | None = None,
    proposal_malicious: float | None = None,
    plurality_legitimate: float | None = None,
    plurality_supported: float | None = None,
    source_target: float | None = None,
    source_supported: float | None = None,
    source_far: float | None = None,
    external_legitimate: float | None = None,
) -> CollapseEvaluationInput:
    return CollapseEvaluationInput(
        proposal_legitimate_admission_degradation=proposal_legitimate,
        proposal_malicious_admission_worsening=proposal_malicious,
        plurality_legitimate_admission_degradation=plurality_legitimate,
        plurality_supported_harm=plurality_supported,
        source_exclusion_target_f1_drop=source_target,
        source_exclusion_supported_harm=source_supported,
        source_exclusion_benign_far_increase=source_far,
        external_verification_legitimate_admission_degradation=external_legitimate,
    )


def _case(proposal: bool, plurality: bool, verification: bool):
    return next(
        case.core
        for case in resolve_all_eight_cases()
        if case.proposal_survives is proposal
        and case.plurality_survives is plurality
        and case.external_verification_survives is verification
    )


def test_all_eight_cases_have_exact_section_18_7_mapping() -> None:
    cases = resolve_all_eight_cases()
    coordinates = frozenset(
        (
            case.proposal_survives,
            case.plurality_survives,
            case.external_verification_survives,
        )
        for case in cases
    )
    assert len(cases) == 8
    assert len(coordinates) == 8
    full = _case(True, True, True)
    assert full.opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED
    assert (
        full.reproduction_row_requirement
        is ReproductionRowRequirement.FIVE_CERTIFIED_NON_SOURCE_ROWS
    )
    assert full.row_verification_mode is RowVerificationMode.THREE_VERIFIER_TWO_OF_THREE
    assert full.production_update_rule is ProductionUpdateRule.KRUM_CERTIFIED_ROWS
    assert _case(False, True, True).opening_mode is ClaimOpeningMode.CANDIDATE_FREE
    assert _case(True, True, False).row_verification_mode is RowVerificationMode.NONE
    assert (
        _case(True, True, False).production_update_rule is ProductionUpdateRule.KRUM_COMMITTED_ROWS
    )
    assert (
        _case(True, False, True).reproduction_row_requirement
        is ReproductionRowRequirement.FIRST_FRESH_VERIFIED_NON_SOURCE_ROW
    )
    assert (
        _case(True, False, False).production_update_rule
        is ProductionUpdateRule.DIRECT_REPRODUCTION_UPDATE
    )
    assert all(case.core.final_gate_required for case in cases)
    assert all(case.core.source_excluded for case in cases)


def test_resolved_core_decision_identity_is_descriptive() -> None:
    assert resolve_core_mapping(True, True, True).decision_identity == (
        "proposal-assisted|plurality|externally-verified"
    )
    assert resolve_core_mapping(False, False, False).decision_identity == (
        "candidate-free|single-reproduction|unverified-row"
    )


def test_proposal_survival_requires_passed_effect_and_constraints() -> None:
    family = ClaimFamily.PROPOSAL_SCREEN_NECESSITY
    decision = collapse_decision_from_comparison_families(
        family,
        _passed_family(family, ComparisonMetric.FALSE_LAUNCH),
        evaluation=_evaluation(proposal_legitimate=0.01, proposal_malicious=0.0),
        materiality_config=MATERIALITY,
    )
    assert decision.survives
    assert decision.kind is CollapseDecisionKind.PROPOSAL_ASSISTANCE


def test_proposal_survival_fails_when_positive_comparison_failed() -> None:
    family = ClaimFamily.PROPOSAL_SCREEN_NECESSITY
    decision = collapse_decision_from_comparison_families(
        family,
        _failed_family(family, ComparisonMetric.FALSE_LAUNCH),
        evaluation=_evaluation(proposal_legitimate=0.01, proposal_malicious=0.0),
        materiality_config=MATERIALITY,
    )
    assert not decision.survives


def test_plurality_survival_requires_mar_or_worst_domain_gain_and_constraints() -> None:
    family = ClaimFamily.PLURALITY_NECESSITY
    decision = collapse_decision_from_comparison_families(
        family,
        _passed_family(family, ComparisonMetric.MALICIOUS_ADMISSION),
        evaluation=_evaluation(plurality_legitimate=0.02, plurality_supported=0.01),
        materiality_config=MATERIALITY,
    )
    assert decision.survives


def test_source_exclusion_survival_requires_asr_and_all_constraints() -> None:
    family = ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM
    decision = collapse_decision_from_comparison_families(
        family,
        _passed_family(family, ComparisonMetric.ATTACK_SUCCESS_RATE),
        evaluation=_evaluation(source_target=0.01, source_supported=0.01, source_far=0.005),
        materiality_config=MATERIALITY,
    )
    assert decision.survives


def test_source_exclusion_survival_fails_when_a_constraint_is_missing() -> None:
    family = ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM
    decision = collapse_decision_from_comparison_families(
        family,
        _passed_family(family, ComparisonMetric.ATTACK_SUCCESS_RATE),
        evaluation=_evaluation(source_target=0.01, source_supported=0.01),
        materiality_config=MATERIALITY,
    )
    assert not decision.survives


def test_external_verification_survival_requires_effect_and_liveness_constraint() -> None:
    family = ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY
    decision = collapse_decision_from_comparison_families(
        family,
        _passed_family(family, ComparisonMetric.MALICIOUS_ADMISSION),
        evaluation=_evaluation(external_legitimate=0.02),
        materiality_config=MATERIALITY,
    )
    assert decision.survives


def _decision(kind: CollapseDecisionKind, survives: bool) -> CollapseDecision:
    return CollapseDecision(
        kind=kind,
        survives=survives,
        primary_material_effect="malicious-admission" if survives else None,
        adjusted_p_value=0.001 if survives else None,
        constraint_passes=survives,
        reason="test fixture",
    )


def test_materialize_resolved_core_uses_decision_states() -> None:
    decisions = (
        _decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True),
        _decision(CollapseDecisionKind.PLURALITY, True),
        _decision(CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION, True),
        _decision(CollapseDecisionKind.EXTERNAL_VERIFICATION, True),
    )
    core = materialize_resolved_core(decisions)
    assert core.decision_identity == "proposal-assisted|plurality|externally-verified"
    assert core.direct_source_exclusion_survives


def test_materialize_resolved_core_preserves_source_exclusion_decision() -> None:
    decisions = (
        _decision(CollapseDecisionKind.PROPOSAL_ASSISTANCE, True),
        _decision(CollapseDecisionKind.PLURALITY, True),
        _decision(CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION, False),
        _decision(CollapseDecisionKind.EXTERNAL_VERIFICATION, True),
    )
    core = materialize_resolved_core(decisions)
    assert not core.direct_source_exclusion_survives


def test_publish_and_read_resolved_core_round_trips(tmp_path: Path) -> None:
    core = resolve_core_mapping(True, False, True)
    publish_resolved_core(tmp_path, core)
    reloaded = read_resolved_core(tmp_path)
    assert reloaded is not None
    assert reloaded.decision_identity == core.decision_identity
    assert reloaded.opening_mode is core.opening_mode
    assert reloaded.reproduction_row_requirement is core.reproduction_row_requirement
    assert reloaded.row_verification_mode is core.row_verification_mode
    assert reloaded.production_update_rule is core.production_update_rule


def test_read_resolved_core_returns_none_without_a_published_artifact(tmp_path: Path) -> None:
    assert read_resolved_core(tmp_path) is None


def test_publish_resolved_core_overwrites_a_prior_publish(tmp_path: Path) -> None:
    publish_resolved_core(tmp_path, resolve_core_mapping(True, True, True))
    publish_resolved_core(tmp_path, resolve_core_mapping(False, False, False))
    reloaded = read_resolved_core(tmp_path)
    assert reloaded is not None
    assert reloaded.decision_identity == "candidate-free|single-reproduction|unverified-row"
