from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from fedsira.analysis.comparisons import ComparisonFamilyResult
from fedsira.config.schema import MaterialityConfig, MultiplicityConfig
from fedsira.domain.enums import ClaimOpeningMode
from fedsira.domain.records import CanonicalToken, Probability
from fedsira.experiments.registry import ClaimFamily


class CollapseDecisionKind(StrEnum):
    PROPOSAL_ASSISTANCE = "proposal assistance"
    PLURALITY = "plurality"
    DIRECT_SOURCE_EXCLUSION = "direct source exclusion"
    EXTERNAL_VERIFICATION = "external reproduction verification"


@dataclass(frozen=True)
class CollapseDecision:
    kind: CollapseDecisionKind
    survives: bool
    primary_material_effect: CanonicalToken | None
    adjusted_p_value: Probability | None
    constraint_passes: bool
    reason: CanonicalToken


@dataclass(frozen=True)
class ResolvedCore:
    proposal_assistance_survives: bool
    plurality_survives: bool
    direct_source_exclusion_survives: bool
    external_verification_survives: bool
    opening_mode: ClaimOpeningMode
    reproduction_row_requirement: CanonicalToken
    row_verification_mode: CanonicalToken
    production_update_rule: CanonicalToken
    final_gate_required: bool = True
    source_excluded: bool = True

    @property
    def identity_token(self) -> CanonicalToken:
        return "|".join(
            (
                "P" if self.proposal_assistance_survives else "p",
                "R" if self.plurality_survives else "r",
                "V" if self.external_verification_survives else "v",
            )
        )


_OPENING_BY_P: dict[bool, ClaimOpeningMode] = {
    True: ClaimOpeningMode.PROPOSAL_ASSISTED,
    False: ClaimOpeningMode.CANDIDATE_FREE,
}


def resolve_core_mapping(
    proposal_survives: bool, plurality_survives: bool, external_verification_survives: bool
) -> ResolvedCore:
    opening_mode = _OPENING_BY_P[proposal_survives]
    if plurality_survives:
        if external_verification_survives:
            return ResolvedCore(
                proposal_assistance_survives=proposal_survives,
                plurality_survives=True,
                direct_source_exclusion_survives=True,
                external_verification_survives=True,
                opening_mode=opening_mode,
                reproduction_row_requirement="first 5 certified non-source rows",
                row_verification_mode="ordinary 3-verifier 2-of-3 certification for each row",
                production_update_rule="Krum over first 5 certified rows",
            )
        return ResolvedCore(
            proposal_assistance_survives=proposal_survives,
            plurality_survives=True,
            direct_source_exclusion_survives=True,
            external_verification_survives=False,
            opening_mode=opening_mode,
            reproduction_row_requirement="first 5 adequate committed non-source rows",
            row_verification_mode="none",
            production_update_rule="Krum over first 5 committed rows",
        )
    if external_verification_survives:
        return ResolvedCore(
            proposal_assistance_survives=proposal_survives,
            plurality_survives=False,
            direct_source_exclusion_survives=True,
            external_verification_survives=True,
            opening_mode=opening_mode,
            reproduction_row_requirement=(
                "first adequate non-source row that passes one fresh verifier"
            ),
            row_verification_mode=(
                "one verifier: first adequate eligible verifier in post-commitment "
                "Verifier Assignment order; Positive required"
            ),
            production_update_rule="that reproduction update directly",
        )
    return ResolvedCore(
        proposal_assistance_survives=proposal_survives,
        plurality_survives=False,
        direct_source_exclusion_survives=True,
        external_verification_survives=False,
        opening_mode=opening_mode,
        reproduction_row_requirement="first adequate committed non-source row",
        row_verification_mode="none",
        production_update_rule="that reproduction update directly",
    )


def resolve_all_eight_cases() -> dict[tuple[bool, bool, bool], ResolvedCore]:
    cases: dict[tuple[bool, bool, bool], ResolvedCore] = {}
    for proposal in (True, False):
        for plurality in (True, False):
            for external_verification in (True, False):
                cases[(proposal, plurality, external_verification)] = resolve_core_mapping(
                    proposal, plurality, external_verification
                )
    return cases


@dataclass(frozen=True)
class CollapseEvaluationInput:
    false_launch_reduction: float | None
    reproduction_attempt_reduction: float | None
    post_evidence_overhead_reduction: float | None
    proposal_legitimate_admission_degradation: float | None
    proposal_malicious_admission_worsening: float | None
    plurality_malicious_admission_reduction: float | None
    plurality_worst_domain_target_f1_gain: float | None
    plurality_legitimate_admission_degradation: float | None
    plurality_supported_harm: float | None
    source_exclusion_asr_reduction: float | None
    source_exclusion_target_f1_drop: float | None
    source_exclusion_supported_harm: float | None
    source_exclusion_benign_far_increase: float | None
    external_verification_malicious_admission_reduction: float | None
    external_verification_worst_domain_target_f1_gain: float | None
    external_verification_legitimate_admission_degradation: float | None


def _reduction_passes(value: float | None, minimum: float) -> bool:
    return value is not None and value >= minimum


def evaluate_proposal_survival(
    evaluation: CollapseEvaluationInput,
    materiality_config: MaterialityConfig,
    multiplicity_config: MultiplicityConfig,
    adjusted_p_values: Sequence[tuple[CanonicalToken, Probability]],
) -> CollapseDecision:
    adjusted_by_name = dict(adjusted_p_values)
    effects: list[tuple[bool, str]] = []
    if evaluation.false_launch_reduction is not None:
        p_value = adjusted_by_name.get("false-launch superiority")
        effects.append(
            (
                _reduction_passes(
                    evaluation.false_launch_reduction,
                    materiality_config.false_launch_reduction_minimum,
                )
                and p_value is not None
                and p_value < multiplicity_config.family_wise_alpha,
                "false-launch",
            )
        )
    if evaluation.reproduction_attempt_reduction is not None:
        p_value = adjusted_by_name.get("reproduction-attempt superiority")
        effects.append(
            (
                _reduction_passes(
                    evaluation.reproduction_attempt_reduction,
                    materiality_config.reproduction_attempt_relative_reduction_minimum,
                )
                and p_value is not None
                and p_value < multiplicity_config.family_wise_alpha,
                "reproduction-attempt",
            )
        )
    if evaluation.post_evidence_overhead_reduction is not None:
        p_value = adjusted_by_name.get("post-evidence-overhead superiority")
        effects.append(
            (
                _reduction_passes(
                    evaluation.post_evidence_overhead_reduction,
                    materiality_config.post_evidence_overhead_relative_reduction_minimum,
                )
                and p_value is not None
                and p_value < multiplicity_config.family_wise_alpha,
                "post-evidence-overhead",
            )
        )
    positive_evidence = any(passes for passes, _ in effects)
    legitimate_degradation_ok = (
        evaluation.proposal_legitimate_admission_degradation is None
        or evaluation.proposal_legitimate_admission_degradation
        <= materiality_config.legitimate_admission_noninferiority_margin
    )
    malicious_worsening_ok = (
        evaluation.proposal_malicious_admission_worsening is None
        or evaluation.proposal_malicious_admission_worsening
        <= materiality_config.proposal_malicious_admission_worsening_maximum
    )
    survives = positive_evidence and legitimate_degradation_ok and malicious_worsening_ok
    return CollapseDecision(
        kind=CollapseDecisionKind.PROPOSAL_ASSISTANCE,
        survives=survives,
        primary_material_effect=effects[0][1] if effects else None,
        adjusted_p_value=None,
        constraint_passes=legitimate_degradation_ok and malicious_worsening_ok,
        reason="proposal-survival rule passed" if survives else "proposal-survival rule failed",
    )


def evaluate_plurality_survival(
    evaluation: CollapseEvaluationInput,
    materiality_config: MaterialityConfig,
    multiplicity_config: MultiplicityConfig,
    adjusted_p_values: Sequence[tuple[CanonicalToken, Probability]],
) -> CollapseDecision:
    adjusted_by_name = dict(adjusted_p_values)
    mar_passes = _reduction_passes(
        evaluation.plurality_malicious_admission_reduction,
        materiality_config.malicious_admission_reduction_minimum,
    )
    worst_domain_passes = _reduction_passes(
        evaluation.plurality_worst_domain_target_f1_gain,
        materiality_config.worst_domain_target_f1_gain_minimum,
    )
    p_value = adjusted_by_name.get("plurality primary effect")
    statistical_pass = p_value is not None and p_value < multiplicity_config.family_wise_alpha
    positive_evidence = (mar_passes or worst_domain_passes) and statistical_pass
    legitimate_degradation_ok = (
        evaluation.plurality_legitimate_admission_degradation is None
        or evaluation.plurality_legitimate_admission_degradation
        <= materiality_config.legitimate_admission_noninferiority_margin
    )
    supported_harm_ok = (
        evaluation.plurality_supported_harm is None
        or evaluation.plurality_supported_harm
        <= materiality_config.supported_macro_f1_noninferiority_margin
    )
    survives = positive_evidence and legitimate_degradation_ok and supported_harm_ok
    return CollapseDecision(
        kind=CollapseDecisionKind.PLURALITY,
        survives=survives,
        primary_material_effect="malicious-admission or worst-domain target-F1",
        adjusted_p_value=p_value,
        constraint_passes=legitimate_degradation_ok and supported_harm_ok,
        reason="plurality-survival rule passed" if survives else "plurality-survival rule failed",
    )


def evaluate_source_exclusion_survival(
    evaluation: CollapseEvaluationInput,
    materiality_config: MaterialityConfig,
    multiplicity_config: MultiplicityConfig,
    adjusted_p_values: Sequence[tuple[CanonicalToken, Probability]],
) -> CollapseDecision:
    adjusted_by_name = dict(adjusted_p_values)
    asr_reduction_passes = _reduction_passes(
        evaluation.source_exclusion_asr_reduction,
        materiality_config.source_exclusion_asr_reduction_minimum,
    )
    p_value = adjusted_by_name.get("source-exclusion ASR")
    statistical_pass = p_value is not None and p_value < multiplicity_config.family_wise_alpha
    target_non_inferior_ok = (
        evaluation.source_exclusion_target_f1_drop is None
        or evaluation.source_exclusion_target_f1_drop <= materiality_config.target_f1_gain_minimum
    )
    supported_harm_ok = (
        evaluation.source_exclusion_supported_harm is None
        or evaluation.source_exclusion_supported_harm
        <= materiality_config.supported_macro_f1_noninferiority_margin
    )
    benign_far_ok = (
        evaluation.source_exclusion_benign_far_increase is None
        or evaluation.source_exclusion_benign_far_increase
        <= materiality_config.benign_false_alarm_rate_noninferiority_margin
    )
    survives = (
        asr_reduction_passes
        and statistical_pass
        and target_non_inferior_ok
        and supported_harm_ok
        and benign_far_ok
    )
    return CollapseDecision(
        kind=CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
        survives=survives,
        primary_material_effect="post-production ASR reduction",
        adjusted_p_value=p_value,
        constraint_passes=target_non_inferior_ok and supported_harm_ok and benign_far_ok,
        reason=("source-exclusion gate passed" if survives else "source-exclusion gate failed"),
    )


def evaluate_external_verification_survival(
    evaluation: CollapseEvaluationInput,
    materiality_config: MaterialityConfig,
    multiplicity_config: MultiplicityConfig,
    adjusted_p_values: Sequence[tuple[CanonicalToken, Probability]],
) -> CollapseDecision:
    adjusted_by_name = dict(adjusted_p_values)
    mar_passes = _reduction_passes(
        evaluation.external_verification_malicious_admission_reduction,
        materiality_config.malicious_admission_reduction_minimum,
    )
    worst_domain_passes = _reduction_passes(
        evaluation.external_verification_worst_domain_target_f1_gain,
        materiality_config.worst_domain_target_f1_gain_minimum,
    )
    p_value = adjusted_by_name.get("external-verification primary effect")
    statistical_pass = p_value is not None and p_value < multiplicity_config.family_wise_alpha
    positive_evidence = (mar_passes or worst_domain_passes) and statistical_pass
    legitimate_degradation_ok = (
        evaluation.external_verification_legitimate_admission_degradation is None
        or evaluation.external_verification_legitimate_admission_degradation
        <= materiality_config.legitimate_admission_noninferiority_margin
    )
    survives = positive_evidence and legitimate_degradation_ok
    return CollapseDecision(
        kind=CollapseDecisionKind.EXTERNAL_VERIFICATION,
        survives=survives,
        primary_material_effect="malicious-admission or worst-domain target-F1",
        adjusted_p_value=p_value,
        constraint_passes=legitimate_degradation_ok,
        reason=(
            "external-verification survival rule passed"
            if survives
            else "external-verification survival rule failed"
        ),
    )


def materialize_resolved_core(
    decisions: Sequence[CollapseDecision],
) -> ResolvedCore:
    decision_by_kind = {decision.kind: decision for decision in decisions}
    proposal = decision_by_kind[CollapseDecisionKind.PROPOSAL_ASSISTANCE]
    plurality = decision_by_kind[CollapseDecisionKind.PLURALITY]
    source_exclusion = decision_by_kind[CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION]
    external_verification = decision_by_kind[CollapseDecisionKind.EXTERNAL_VERIFICATION]
    core = resolve_core_mapping(
        proposal.survives, plurality.survives, external_verification.survives
    )
    expected_cases = resolve_all_eight_cases()
    expected = expected_cases[
        (proposal.survives, plurality.survives, external_verification.survives)
    ]
    if expected.identity_token != core.identity_token:
        raise ValueError("resolved-core mapping deviates from the fixed Section 18.7 table")
    return ResolvedCore(
        proposal_assistance_survives=core.proposal_assistance_survives,
        plurality_survives=core.plurality_survives,
        direct_source_exclusion_survives=source_exclusion.survives,
        external_verification_survives=core.external_verification_survives,
        opening_mode=core.opening_mode,
        reproduction_row_requirement=core.reproduction_row_requirement,
        row_verification_mode=core.row_verification_mode,
        production_update_rule=core.production_update_rule,
        final_gate_required=core.final_gate_required,
        source_excluded=core.source_excluded,
    )


_FAMILY_TO_DECISION_KIND: dict[CanonicalToken, CollapseDecisionKind] = {
    ClaimFamily.PROPOSAL_SCREEN_NECESSITY.value: CollapseDecisionKind.PROPOSAL_ASSISTANCE,
    ClaimFamily.PLURALITY_NECESSITY.value: CollapseDecisionKind.PLURALITY,
    ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM.value: CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
    ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY.value: CollapseDecisionKind.EXTERNAL_VERIFICATION,
}


def collapse_decision_from_comparison_families(
    family_name: CanonicalToken,
    comparison_results: Sequence[ComparisonFamilyResult],
    alpha: Probability,
    evaluation: CollapseEvaluationInput | None = None,
    materiality_config: MaterialityConfig | None = None,
    multiplicity_config: MultiplicityConfig | None = None,
) -> CollapseDecision:
    kind = _FAMILY_TO_DECISION_KIND[family_name]
    primary_effect: CanonicalToken | None = None
    adjusted_p_value: Probability | None = None
    for family in comparison_results:
        if family.family.value != family_name:
            continue
        for comparison in family.comparisons:
            if comparison.adjusted_p_value is None:
                continue
            if adjusted_p_value is None or comparison.adjusted_p_value < adjusted_p_value:
                adjusted_p_value = comparison.adjusted_p_value
                primary_effect = comparison.definition.metric
    survives = adjusted_p_value is not None and adjusted_p_value < alpha
    constraint_passes = True
    if (
        evaluation is not None
        and materiality_config is not None
        and multiplicity_config is not None
    ):
        named_p_values = tuple(
            (comparison.definition.canonical_name, comparison.adjusted_p_value)
            for family in comparison_results
            for comparison in family.comparisons
            if comparison.adjusted_p_value is not None
        )
        if kind is CollapseDecisionKind.PROPOSAL_ASSISTANCE:
            decision = evaluate_proposal_survival(
                evaluation, materiality_config, multiplicity_config, named_p_values
            )
        elif kind is CollapseDecisionKind.PLURALITY:
            decision = evaluate_plurality_survival(
                evaluation, materiality_config, multiplicity_config, named_p_values
            )
        elif kind is CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION:
            decision = evaluate_source_exclusion_survival(
                evaluation, materiality_config, multiplicity_config, named_p_values
            )
        else:
            decision = evaluate_external_verification_survival(
                evaluation, materiality_config, multiplicity_config, named_p_values
            )
        survives = decision.survives
        primary_effect = decision.primary_material_effect
        adjusted_p_value = decision.adjusted_p_value
        constraint_passes = decision.constraint_passes
    return CollapseDecision(
        kind=kind,
        survives=survives,
        primary_material_effect=primary_effect,
        adjusted_p_value=adjusted_p_value,
        constraint_passes=constraint_passes,
        reason="mechanical collapse rule",
    )
