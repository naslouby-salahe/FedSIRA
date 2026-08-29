from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from fedsira.analysis.comparisons import ComparisonFamilyResult
from fedsira.artifacts.records import ArtifactManifest
from fedsira.artifacts.storage import (
    compute_checksum,
    is_artifact_complete_and_valid,
    publish_artifact_to_disk,
    published_artifact_paths,
    read_published_manifest,
    stage_payload,
)
from fedsira.config.schema import MaterialityConfig, MultiplicityConfig
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState, ClaimOpeningMode
from fedsira.domain.records import (
    ArtifactDigest,
    BooleanValue,
    ComparisonName,
    FrozenDomainModel,
    MetricDifference,
    MetricName,
    Probability,
    TextValue,
)
from fedsira.experiments.registry import ClaimFamily


class CollapseDecisionKind(StrEnum):
    PROPOSAL_ASSISTANCE = "proposal assistance"
    PLURALITY = "plurality"
    DIRECT_SOURCE_EXCLUSION = "direct source exclusion"
    EXTERNAL_VERIFICATION = "external reproduction verification"


class ReproductionRowRequirement(StrEnum):
    FIVE_CERTIFIED_NON_SOURCE_ROWS = "first 5 certified non-source rows"
    FIVE_COMMITTED_NON_SOURCE_ROWS = "first 5 adequate committed non-source rows"
    FIRST_FRESH_VERIFIED_NON_SOURCE_ROW = (
        "first adequate non-source row that passes one fresh verifier"
    )
    FIRST_COMMITTED_NON_SOURCE_ROW = "first adequate committed non-source row"


class RowVerificationMode(StrEnum):
    THREE_VERIFIER_TWO_OF_THREE = "ordinary 3-verifier 2-of-3 certification for each row"
    ONE_FRESH_POSITIVE = (
        "one verifier: first adequate eligible verifier in post-commitment Verifier Assignment "
        "order; Positive required"
    )
    NONE = "none"


class ProductionUpdateRule(StrEnum):
    KRUM_CERTIFIED_ROWS = "Krum over first 5 certified rows"
    KRUM_COMMITTED_ROWS = "Krum over first 5 committed rows"
    DIRECT_REPRODUCTION_UPDATE = "that reproduction update directly"


class CollapseDecision(FrozenDomainModel):
    kind: CollapseDecisionKind
    survives: BooleanValue
    primary_material_effect: MetricName | None
    adjusted_p_value: Probability | None
    constraint_passes: BooleanValue
    reason: TextValue


class ResolvedCore(FrozenDomainModel):
    proposal_assistance_survives: BooleanValue
    plurality_survives: BooleanValue
    direct_source_exclusion_survives: BooleanValue
    external_verification_survives: BooleanValue
    opening_mode: ClaimOpeningMode
    reproduction_row_requirement: ReproductionRowRequirement
    row_verification_mode: RowVerificationMode
    production_update_rule: ProductionUpdateRule
    final_gate_required: BooleanValue = True
    source_excluded: BooleanValue = True

    @property
    def decision_identity(self) -> TextValue:
        return "|".join(
            (
                "proposal-assisted" if self.proposal_assistance_survives else "candidate-free",
                "plurality" if self.plurality_survives else "single-reproduction",
                "externally-verified"
                if self.external_verification_survives
                else "unverified-row",
            )
        )


_OPENING_BY_PROPOSAL_SURVIVAL: dict[BooleanValue, ClaimOpeningMode] = {
    True: ClaimOpeningMode.PROPOSAL_ASSISTED,
    False: ClaimOpeningMode.CANDIDATE_FREE,
}


def resolve_core_mapping(
    proposal_survives: BooleanValue,
    plurality_survives: BooleanValue,
    external_verification_survives: BooleanValue,
) -> ResolvedCore:
    opening_mode = _OPENING_BY_PROPOSAL_SURVIVAL[proposal_survives]
    if plurality_survives and external_verification_survives:
        return ResolvedCore(
            proposal_assistance_survives=proposal_survives,
            plurality_survives=True,
            direct_source_exclusion_survives=True,
            external_verification_survives=True,
            opening_mode=opening_mode,
            reproduction_row_requirement=ReproductionRowRequirement.FIVE_CERTIFIED_NON_SOURCE_ROWS,
            row_verification_mode=RowVerificationMode.THREE_VERIFIER_TWO_OF_THREE,
            production_update_rule=ProductionUpdateRule.KRUM_CERTIFIED_ROWS,
        )
    if plurality_survives:
        return ResolvedCore(
            proposal_assistance_survives=proposal_survives,
            plurality_survives=True,
            direct_source_exclusion_survives=True,
            external_verification_survives=False,
            opening_mode=opening_mode,
            reproduction_row_requirement=ReproductionRowRequirement.FIVE_COMMITTED_NON_SOURCE_ROWS,
            row_verification_mode=RowVerificationMode.NONE,
            production_update_rule=ProductionUpdateRule.KRUM_COMMITTED_ROWS,
        )
    if external_verification_survives:
        return ResolvedCore(
            proposal_assistance_survives=proposal_survives,
            plurality_survives=False,
            direct_source_exclusion_survives=True,
            external_verification_survives=True,
            opening_mode=opening_mode,
            reproduction_row_requirement=(
                ReproductionRowRequirement.FIRST_FRESH_VERIFIED_NON_SOURCE_ROW
            ),
            row_verification_mode=RowVerificationMode.ONE_FRESH_POSITIVE,
            production_update_rule=ProductionUpdateRule.DIRECT_REPRODUCTION_UPDATE,
        )
    return ResolvedCore(
        proposal_assistance_survives=proposal_survives,
        plurality_survives=False,
        direct_source_exclusion_survives=True,
        external_verification_survives=False,
        opening_mode=opening_mode,
        reproduction_row_requirement=ReproductionRowRequirement.FIRST_COMMITTED_NON_SOURCE_ROW,
        row_verification_mode=RowVerificationMode.NONE,
        production_update_rule=ProductionUpdateRule.DIRECT_REPRODUCTION_UPDATE,
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


class CollapseEvaluationInput(FrozenDomainModel):
    false_launch_reduction: MetricDifference | None
    reproduction_attempt_reduction: MetricDifference | None
    post_evidence_overhead_reduction: MetricDifference | None
    proposal_legitimate_admission_degradation: MetricDifference | None
    proposal_malicious_admission_worsening: MetricDifference | None
    plurality_malicious_admission_reduction: MetricDifference | None
    plurality_worst_domain_target_f1_gain: MetricDifference | None
    plurality_legitimate_admission_degradation: MetricDifference | None
    plurality_supported_harm: MetricDifference | None
    source_exclusion_asr_reduction: MetricDifference | None
    source_exclusion_target_f1_drop: MetricDifference | None
    source_exclusion_supported_harm: MetricDifference | None
    source_exclusion_benign_far_increase: MetricDifference | None
    external_verification_malicious_admission_reduction: MetricDifference | None
    external_verification_worst_domain_target_f1_gain: MetricDifference | None
    external_verification_legitimate_admission_degradation: MetricDifference | None


def _reduction_passes(value: MetricDifference | None, minimum: float) -> bool:
    return value is not None and value >= minimum


def evaluate_proposal_survival(
    evaluation: CollapseEvaluationInput,
    materiality_config: MaterialityConfig,
    multiplicity_config: MultiplicityConfig,
    adjusted_p_values: Sequence[tuple[ComparisonName, Probability]],
) -> CollapseDecision:
    adjusted_by_name = dict(adjusted_p_values)
    effects: list[tuple[bool, MetricName]] = []
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
                "reproduction-attempts",
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
    adjusted_p_values: Sequence[tuple[ComparisonName, Probability]],
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
        primary_material_effect="malicious-admission",
        adjusted_p_value=p_value,
        constraint_passes=legitimate_degradation_ok and supported_harm_ok,
        reason="plurality-survival rule passed" if survives else "plurality-survival rule failed",
    )


def evaluate_source_exclusion_survival(
    evaluation: CollapseEvaluationInput,
    materiality_config: MaterialityConfig,
    multiplicity_config: MultiplicityConfig,
    adjusted_p_values: Sequence[tuple[ComparisonName, Probability]],
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
        primary_material_effect="asr",
        adjusted_p_value=p_value,
        constraint_passes=target_non_inferior_ok and supported_harm_ok and benign_far_ok,
        reason="source-exclusion gate passed" if survives else "source-exclusion gate failed",
    )


def evaluate_external_verification_survival(
    evaluation: CollapseEvaluationInput,
    materiality_config: MaterialityConfig,
    multiplicity_config: MultiplicityConfig,
    adjusted_p_values: Sequence[tuple[ComparisonName, Probability]],
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
        primary_material_effect="malicious-admission",
        adjusted_p_value=p_value,
        constraint_passes=legitimate_degradation_ok,
        reason=(
            "external-verification survival rule passed"
            if survives
            else "external-verification survival rule failed"
        ),
    )


def materialize_resolved_core(decisions: Sequence[CollapseDecision]) -> ResolvedCore:
    decision_by_kind = {decision.kind: decision for decision in decisions}
    proposal = decision_by_kind[CollapseDecisionKind.PROPOSAL_ASSISTANCE]
    plurality = decision_by_kind[CollapseDecisionKind.PLURALITY]
    source_exclusion = decision_by_kind[CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION]
    external_verification = decision_by_kind[CollapseDecisionKind.EXTERNAL_VERIFICATION]
    core = resolve_core_mapping(
        proposal.survives, plurality.survives, external_verification.survives
    )
    expected = resolve_all_eight_cases()[
        (proposal.survives, plurality.survives, external_verification.survives)
    ]
    if expected.decision_identity != core.decision_identity:
        raise ValueError("resolved-core mapping deviates from the fixed Section 18.7 table")
    return core.model_copy(
        update={"direct_source_exclusion_survives": source_exclusion.survives}
    )


RESOLVED_CORE_ARTIFACT_FAMILY = ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION
RESOLVED_CORE_ARTIFACT_IDENTITY: ArtifactDigest = compute_checksum(
    b"RESOLVED_FEDSIRA_CORE_SECTION_18_7"
)


def _resolved_core_payload(core: ResolvedCore) -> bytes:
    return core.model_dump_json().encode("utf-8")


def publish_resolved_core(published_directory: Path, core: ResolvedCore) -> ArtifactManifest:
    payload = _resolved_core_payload(core)
    staged_manifest = ArtifactManifest(
        family=RESOLVED_CORE_ARTIFACT_FAMILY,
        identity=RESOLVED_CORE_ARTIFACT_IDENTITY,
        checksum=compute_checksum(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        upstream_identities=(),
    )
    staged_path = stage_payload(published_directory / "staging", payload)
    return publish_artifact_to_disk(
        staged_path, published_directory, staged_manifest, payload
    )


def read_resolved_core(published_directory: Path) -> ResolvedCore | None:
    if not is_artifact_complete_and_valid(
        published_directory, RESOLVED_CORE_ARTIFACT_IDENTITY
    ):
        return None
    manifest = read_published_manifest(
        published_directory, RESOLVED_CORE_ARTIFACT_IDENTITY
    )
    if manifest is None:
        return None
    payload_path, _manifest_path = published_artifact_paths(
        published_directory, manifest.identity
    )
    return ResolvedCore.model_validate_json(payload_path.read_text())


_FAMILY_TO_DECISION_KIND: dict[ClaimFamily, CollapseDecisionKind] = {
    ClaimFamily.PROPOSAL_SCREEN_NECESSITY: CollapseDecisionKind.PROPOSAL_ASSISTANCE,
    ClaimFamily.PLURALITY_NECESSITY: CollapseDecisionKind.PLURALITY,
    ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM: CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
    ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY: CollapseDecisionKind.EXTERNAL_VERIFICATION,
}


def collapse_decision_from_comparison_families(
    family: ClaimFamily,
    comparison_results: Sequence[ComparisonFamilyResult],
    alpha: Probability,
    evaluation: CollapseEvaluationInput | None = None,
    materiality_config: MaterialityConfig | None = None,
    multiplicity_config: MultiplicityConfig | None = None,
) -> CollapseDecision:
    kind = _FAMILY_TO_DECISION_KIND[family]
    primary_effect: MetricName | None = None
    adjusted_p_value: Probability | None = None
    for family_result in comparison_results:
        if family_result.family is not family:
            continue
        for comparison in family_result.comparisons:
            if comparison.adjusted_p_value is None:
                continue
            if adjusted_p_value is None or comparison.adjusted_p_value < adjusted_p_value:
                adjusted_p_value = comparison.adjusted_p_value
                primary_effect = comparison.definition.metric.value
    survives = adjusted_p_value is not None and adjusted_p_value < alpha
    constraint_passes = True
    if (
        evaluation is not None
        and materiality_config is not None
        and multiplicity_config is not None
    ):
        named_p_values = tuple(
            (comparison.definition.canonical_name, comparison.adjusted_p_value)
            for family_result in comparison_results
            for comparison in family_result.comparisons
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
