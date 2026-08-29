from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from fedsira.analysis.comparisons import (
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonState,
)
from fedsira.artifacts.records import ArtifactManifest
from fedsira.artifacts.storage import (
    compute_checksum,
    is_artifact_complete_and_valid,
    publish_artifact_to_disk,
    published_artifact_paths,
    read_published_manifest,
    stage_payload,
)
from fedsira.config.schema import MaterialityConfig
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState, ClaimOpeningMode
from fedsira.domain.records import (
    ArtifactDigest,
    BooleanValue,
    FrozenDomainModel,
    MetricDifference,
    MetricName,
    PValue,
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
    adjusted_p_value: PValue | None
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
                (
                    "externally-verified"
                    if self.external_verification_survives
                    else "unverified-row"
                ),
            )
        )


class CollapseEvaluationInput(FrozenDomainModel):
    proposal_legitimate_admission_degradation: MetricDifference | None
    proposal_malicious_admission_worsening: MetricDifference | None
    plurality_legitimate_admission_degradation: MetricDifference | None
    plurality_supported_harm: MetricDifference | None
    source_exclusion_target_f1_drop: MetricDifference | None
    source_exclusion_supported_harm: MetricDifference | None
    source_exclusion_benign_far_increase: MetricDifference | None
    external_verification_legitimate_admission_degradation: MetricDifference | None


def resolve_core_mapping(
    proposal_survives: BooleanValue,
    plurality_survives: BooleanValue,
    external_verification_survives: BooleanValue,
) -> ResolvedCore:
    opening_mode = (
        ClaimOpeningMode.PROPOSAL_ASSISTED
        if proposal_survives
        else ClaimOpeningMode.CANDIDATE_FREE
    )
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
    return {
        (proposal, plurality, verification): resolve_core_mapping(
            proposal, plurality, verification
        )
        for proposal in (True, False)
        for plurality in (True, False)
        for verification in (True, False)
    }


def _family_comparisons(
    family: ClaimFamily,
    comparison_results: Sequence[ComparisonFamilyResult],
):
    return tuple(
        comparison
        for result in comparison_results
        if result.family is family
        for comparison in result.comparisons
    )


def _best_passed_metric(
    family: ClaimFamily,
    comparison_results: Sequence[ComparisonFamilyResult],
    allowed_metrics: frozenset[ComparisonMetric],
) -> tuple[MetricName | None, PValue | None]:
    passed = tuple(
        comparison
        for comparison in _family_comparisons(family, comparison_results)
        if comparison.definition.metric in allowed_metrics
        and comparison.comparison_state is ComparisonState.PASSED
    )
    if not passed:
        return None, None
    selected = min(
        passed,
        key=lambda comparison: (
            comparison.adjusted_p_value if comparison.adjusted_p_value is not None else 1.0,
            comparison.definition.comparison_name,
        ),
    )
    return selected.definition.metric.value, selected.adjusted_p_value


def _defined_within(value: MetricDifference | None, maximum: float) -> BooleanValue:
    return value is not None and value <= maximum


def _constraints_pass(
    family: ClaimFamily,
    evaluation: CollapseEvaluationInput | None,
    materiality: MaterialityConfig | None,
) -> BooleanValue:
    if evaluation is None or materiality is None:
        return False
    if family is ClaimFamily.PROPOSAL_SCREEN_NECESSITY:
        return _defined_within(
            evaluation.proposal_legitimate_admission_degradation,
            materiality.legitimate_admission_noninferiority_margin,
        ) and _defined_within(
            evaluation.proposal_malicious_admission_worsening,
            materiality.proposal_malicious_admission_worsening_maximum,
        )
    if family is ClaimFamily.PLURALITY_NECESSITY:
        return _defined_within(
            evaluation.plurality_legitimate_admission_degradation,
            materiality.legitimate_admission_noninferiority_margin,
        ) and _defined_within(
            evaluation.plurality_supported_harm,
            materiality.supported_macro_f1_noninferiority_margin,
        )
    if family is ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM:
        return (
            _defined_within(
                evaluation.source_exclusion_target_f1_drop,
                materiality.target_f1_gain_minimum,
            )
            and _defined_within(
                evaluation.source_exclusion_supported_harm,
                materiality.supported_macro_f1_noninferiority_margin,
            )
            and _defined_within(
                evaluation.source_exclusion_benign_far_increase,
                materiality.benign_false_alarm_rate_noninferiority_margin,
            )
        )
    if family is ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY:
        return _defined_within(
            evaluation.external_verification_legitimate_admission_degradation,
            materiality.legitimate_admission_noninferiority_margin,
        )
    raise ValueError(f"{family.value} is not a collapse family")


def _decision_kind(family: ClaimFamily) -> CollapseDecisionKind:
    if family is ClaimFamily.PROPOSAL_SCREEN_NECESSITY:
        return CollapseDecisionKind.PROPOSAL_ASSISTANCE
    if family is ClaimFamily.PLURALITY_NECESSITY:
        return CollapseDecisionKind.PLURALITY
    if family is ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM:
        return CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION
    if family is ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY:
        return CollapseDecisionKind.EXTERNAL_VERIFICATION
    raise ValueError(f"{family.value} is not a collapse family")


def _positive_metrics(family: ClaimFamily) -> frozenset[ComparisonMetric]:
    if family is ClaimFamily.PROPOSAL_SCREEN_NECESSITY:
        return frozenset(
            {
                ComparisonMetric.FALSE_LAUNCH,
                ComparisonMetric.REPRODUCTION_ATTEMPTS,
                ComparisonMetric.POST_EVIDENCE_OVERHEAD,
            }
        )
    if family is ClaimFamily.PLURALITY_NECESSITY:
        return frozenset(
            {
                ComparisonMetric.MALICIOUS_ADMISSION,
                ComparisonMetric.WORST_DOMAIN_TARGET_F1,
            }
        )
    if family is ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM:
        return frozenset({ComparisonMetric.ATTACK_SUCCESS_RATE})
    if family is ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY:
        return frozenset(
            {
                ComparisonMetric.MALICIOUS_ADMISSION,
                ComparisonMetric.WORST_DOMAIN_TARGET_F1,
            }
        )
    raise ValueError(f"{family.value} is not a collapse family")


def collapse_decision_from_comparison_families(
    family: ClaimFamily,
    comparison_results: Sequence[ComparisonFamilyResult],
    evaluation: CollapseEvaluationInput | None,
    materiality_config: MaterialityConfig | None,
) -> CollapseDecision:
    metric, adjusted_p_value = _best_passed_metric(
        family,
        comparison_results,
        _positive_metrics(family),
    )
    constraints_pass = _constraints_pass(family, evaluation, materiality_config)
    survives = metric is not None and constraints_pass
    if evaluation is None or materiality_config is None:
        reason = "mandatory full-precision constraint evidence is unavailable"
    elif metric is None:
        reason = "no preregistered positive comparison passed statistical and materiality gates"
    elif not constraints_pass:
        reason = "mandatory full-precision constraint failed or is undefined"
    else:
        reason = "survival rule passed"
    return CollapseDecision(
        kind=_decision_kind(family),
        survives=survives,
        primary_material_effect=metric,
        adjusted_p_value=adjusted_p_value,
        constraint_passes=constraints_pass,
        reason=reason,
    )


def materialize_resolved_core(decisions: Sequence[CollapseDecision]) -> ResolvedCore:
    by_kind = {decision.kind: decision for decision in decisions}
    proposal = by_kind[CollapseDecisionKind.PROPOSAL_ASSISTANCE]
    plurality = by_kind[CollapseDecisionKind.PLURALITY]
    source_exclusion = by_kind[CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION]
    verification = by_kind[CollapseDecisionKind.EXTERNAL_VERIFICATION]
    core = resolve_core_mapping(
        proposal.survives,
        plurality.survives,
        verification.survives,
    )
    expected = resolve_all_eight_cases()[
        (proposal.survives, plurality.survives, verification.survives)
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


def publish_resolved_core(
    published_directory: Path,
    core: ResolvedCore,
) -> ArtifactManifest:
    payload = core.model_dump_json().encode("utf-8")
    staged_manifest = ArtifactManifest(
        family=RESOLVED_CORE_ARTIFACT_FAMILY,
        identity=RESOLVED_CORE_ARTIFACT_IDENTITY,
        checksum=compute_checksum(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        upstream_identities=(),
    )
    staged_path = stage_payload(published_directory / "staging", payload)
    return publish_artifact_to_disk(
        staged_path,
        published_directory,
        staged_manifest,
        payload,
    )


def read_resolved_core(published_directory: Path) -> ResolvedCore | None:
    if not is_artifact_complete_and_valid(
        published_directory,
        RESOLVED_CORE_ARTIFACT_IDENTITY,
    ):
        return None
    manifest = read_published_manifest(
        published_directory,
        RESOLVED_CORE_ARTIFACT_IDENTITY,
    )
    if manifest is None:
        return None
    payload_path, _manifest_path = published_artifact_paths(
        published_directory,
        manifest.identity,
    )
    return ResolvedCore.model_validate_json(payload_path.read_text())
