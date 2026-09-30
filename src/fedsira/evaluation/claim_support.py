from __future__ import annotations

from collections.abc import Callable

from fedsira.domain.enums import (
    CapabilityContractScope,
    ClaimId,
    ClaimState,
    ComparisonFamily,
    ComparisonMetric,
    CoreMethodIdentity,
    HeterogeneityRegime,
)
from fedsira.domain.types import (
    AdmissionCount,
    BooleanValue,
    CollapseDecisionMatchesFamily,
    CompleteSeedCount,
    FamilyWiseAlpha,
    FrozenDomainModel,
    MinimumCompletePairCount,
    Probability,
    ProvenanceViolationCount,
    TextValue,
)
from fedsira.evaluation.comparisons import (
    ComparisonDefinition,
    ComparisonFamilyResult,
    ComparisonResult,
    ComparisonState,
    build_comparison_registry,
)
from fedsira.experiments.collapse import CollapseDecision, CollapseDecisionKind
from fedsira.experiments.definitions import (
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
)
from fedsira.runtime import current_application_context

ClaimDerivation = tuple[ClaimId, ClaimState, TextValue]


class UnsupportedCapabilityEvidence(FrozenDomainModel):
    checked: BooleanValue
    target_absent_from_anchor_train: BooleanValue
    target_absent_from_anchor_validation: BooleanValue
    target_present_in_required_roles: BooleanValue
    source_byzantine_setting_instantiated: BooleanValue
    anchor_role_leakage: BooleanValue
    missing_target_blocks_primary: BooleanValue


class PreEvidenceLimitEvidence(FrozenDomainModel):
    assumptions_map_to_implementation: BooleanValue
    fixture_passed: BooleanValue
    trusted_side_information_declared: BooleanValue
    transcript_law_changed_without_narrowing: BooleanValue


class AuthorityTransitionEvidence(FrozenDomainModel):
    source_is_honest_path_input: BooleanValue
    provenance_violation_count: ProvenanceViolationCount
    complete_primary_seed_count: CompleteSeedCount
    legitimate_admitted_count: AdmissionCount


class DirectSourceExclusionEvidence(FrozenDomainModel):
    cells_checked: BooleanValue
    provenance_violation_count: ProvenanceViolationCount


class ConditionalNonInterferenceEvidence(FrozenDomainModel):
    fixture_executed: BooleanValue
    source_commitments_differ: BooleanValue
    honest_updates_identical: BooleanValue
    production_update_identical: BooleanValue


class InformationArrivalEvidence(FrozenDomainModel):
    records_complete: BooleanValue
    admission_before_t_evidence: BooleanValue
    five_row_path_active: BooleanValue
    synthesis_before_t_reproduction_evidence: BooleanValue
    wall_clock_components_recorded: BooleanValue


class PostEvidenceEfficiencyEvidence(FrozenDomainModel):
    measurement_executed: BooleanValue
    all_repetitions_complete: BooleanValue
    median_iqr_valid: BooleanValue


class IotIdsApplicationEvidence(FrozenDomainModel):
    primary_executed: BooleanValue
    primary_valid: BooleanValue
    secondary_executed: BooleanValue
    secondary_valid: BooleanValue
    secondary_blocked_by_data: BooleanValue


class ClaimSupportEvidence(FrozenDomainModel):
    unsupported_capability: UnsupportedCapabilityEvidence | None = None
    pre_evidence_limit: PreEvidenceLimitEvidence | None = None
    authority_transition: AuthorityTransitionEvidence | None = None
    direct_source_exclusion: DirectSourceExclusionEvidence | None = None
    conditional_non_interference: ConditionalNonInterferenceEvidence | None = None
    legitimate_admission_without_source: BooleanValue | None = None
    shared_failure_certified: BooleanValue | None = None
    information_arrival: InformationArrivalEvidence | None = None
    post_evidence_efficiency: PostEvidenceEfficiencyEvidence | None = None
    iot_ids_application: IotIdsApplicationEvidence | None = None


class ClaimDerivationInputs(FrozenDomainModel):
    collapse_decisions: tuple[CollapseDecision, ...] | None
    comparison_results: tuple[ComparisonFamilyResult, ...]
    safe_dormancy_verified: BooleanValue = False
    byzantine_operating_region_verified: BooleanValue = False
    support: ClaimSupportEvidence | None = None


def collapse_decision_matches_family(
    decision: CollapseDecision,
    family: ComparisonFamilyResult,
) -> CollapseDecisionMatchesFamily:
    if decision.survives != (
        decision.primary_material_effect is not None and decision.constraint_passes
    ):
        return False
    if decision.primary_material_effect is None:
        return decision.adjusted_p_value is None
    return decision.adjusted_p_value is not None and any(
        comparison.definition.metric == decision.primary_material_effect
        and comparison.adjusted_p_value == decision.adjusted_p_value
        and comparison.comparison_state is ComparisonState.PASSED
        for comparison in family.comparisons
    )


def boundary_claim_derivations(
    collapse_decisions: tuple[CollapseDecision, ...] | None,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    support: ClaimSupportEvidence | None,
) -> tuple[ClaimDerivation, ...]:
    derived: list[ClaimDerivation] = []
    if support is not None:
        derived.extend(_structural_claims(support))
    derived.extend(_comparison_claims(collapse_decisions, comparison_results, support))
    return tuple(derived)


def _family_wise_alpha() -> FamilyWiseAlpha:
    config = current_application_context().scientific_config
    return config.metrics_and_statistics.multiplicity.family_wise_alpha


def _minimum_complete_pairs() -> MinimumCompletePairCount:
    config = current_application_context().scientific_config
    return config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_inference


def _false_same_rate_minimum() -> Probability:
    config = current_application_context().scientific_config
    boundary = config.evidence_thresholds.capability_granularity_boundary
    return boundary.false_same_capability_certification_rate_minimum


def _registered(
    predicate: Callable[[ComparisonDefinition], BooleanValue],
) -> tuple[ComparisonDefinition, ...]:
    return tuple(definition for definition in build_comparison_registry() if predicate(definition))


def _unique_comparison(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    definition: ComparisonDefinition,
) -> ComparisonResult | None:
    matches = tuple(
        comparison
        for family in comparison_results
        for comparison in family.comparisons
        if comparison.definition.comparison_name == definition.comparison_name
        and comparison.definition.experiment == definition.experiment
    )
    if len(matches) != 1:
        return None
    return matches[0]


def _is_resolved(comparison: ComparisonResult | None) -> BooleanValue:
    return comparison is not None and comparison.comparison_state in (
        ComparisonState.PASSED,
        ComparisonState.FAILED,
    )


def _statistically_supported(comparison: ComparisonResult) -> BooleanValue:
    return (
        comparison.comparison_state is ComparisonState.PASSED
        and comparison.adjusted_p_value is not None
        and comparison.adjusted_p_value < _family_wise_alpha()
    )


def _heterogeneity_limit(metric: ComparisonMetric) -> Probability:
    thresholds = current_application_context().scientific_config.evidence_thresholds
    boundary = thresholds.heterogeneity_boundary
    if metric is ComparisonMetric.LEGITIMATE_ADMISSION:
        return boundary.legitimate_admission_change_from_natural_maximum
    if metric is ComparisonMetric.WORST_DOMAIN_TARGET_F1:
        return boundary.worst_domain_target_f1_change_from_natural_maximum
    raise ValueError(f"heterogeneity boundary has no limit for {metric}")


def _within_heterogeneity_tolerance(comparison: ComparisonResult) -> BooleanValue:
    difference = comparison.mean_paired_difference
    if difference is None:
        return False
    return difference >= -_heterogeneity_limit(comparison.definition.metric)


def _structural_claims(support: ClaimSupportEvidence) -> tuple[ClaimDerivation, ...]:
    derived: list[ClaimDerivation] = []
    unsupported = support.unsupported_capability
    if unsupported is not None:
        derived.append(_unsupported_capability_claim(unsupported))
    pre_evidence = support.pre_evidence_limit
    if pre_evidence is not None:
        derived.append(_pre_evidence_claim(pre_evidence))
    authority = support.authority_transition
    if authority is not None:
        derived.append(_authority_transition_claim(authority))
    exclusion = support.direct_source_exclusion
    if exclusion is not None:
        derived.append(_direct_source_exclusion_claim(exclusion))
    non_interference = support.conditional_non_interference
    if non_interference is not None:
        derived.append(_conditional_non_interference_claim(non_interference))
    arrival = support.information_arrival
    if arrival is not None:
        derived.append(_information_arrival_claim(arrival))
    efficiency = support.post_evidence_efficiency
    if efficiency is not None:
        derived.append(_post_evidence_efficiency_claim(efficiency))
    application = support.iot_ids_application
    if application is not None:
        derived.append(_iot_ids_application_claim(application))
    return tuple(derived)


def _unsupported_capability_claim(evidence: UnsupportedCapabilityEvidence) -> ClaimDerivation:
    if not evidence.checked:
        return _not_tested(ClaimId.UNSUPPORTED_CAPABILITY_PROBLEM)
    failed = (
        evidence.anchor_role_leakage
        or evidence.missing_target_blocks_primary
        or not evidence.source_byzantine_setting_instantiated
        or not evidence.target_absent_from_anchor_train
        or not evidence.target_absent_from_anchor_validation
        or not evidence.target_present_in_required_roles
    )
    if failed:
        return (
            ClaimId.UNSUPPORTED_CAPABILITY_PROBLEM,
            ClaimState.NOT_SUPPORTED,
            "Anchor-role leakage, missing target support, or the source-Byzantine "
            "setting is not instantiated.",
        )
    return (
        ClaimId.UNSUPPORTED_CAPABILITY_PROBLEM,
        ClaimState.SUPPORTED,
        "Target rows are absent from anchor roles, present in the required "
        "post-reference roles, and the declared source-Byzantine setting is instantiated.",
    )


def _pre_evidence_claim(evidence: PreEvidenceLimitEvidence) -> ClaimDerivation:
    if evidence.transcript_law_changed_without_narrowing:
        return (
            ClaimId.PRE_EVIDENCE_INFORMATION_LIMIT,
            ClaimState.NOT_SUPPORTED,
            "Trusted side information changes the transcript law without narrowing the premise.",
        )
    if (
        evidence.assumptions_map_to_implementation
        and evidence.fixture_passed
        and evidence.trusted_side_information_declared
    ):
        return (
            ClaimId.PRE_EVIDENCE_INFORMATION_LIMIT,
            ClaimState.SUPPORTED,
            "The equal-transcript premise maps to the implementation and the "
            "executable fixture passes with declared side information.",
        )
    return _not_tested(ClaimId.PRE_EVIDENCE_INFORMATION_LIMIT)


def _authority_transition_claim(evidence: AuthorityTransitionEvidence) -> ClaimDerivation:
    if evidence.source_is_honest_path_input or evidence.provenance_violation_count > 0:
        return (
            ClaimId.AUTHORITY_TRANSITION,
            ClaimState.NOT_SUPPORTED,
            "A source artifact is an honest-path production input.",
        )
    if evidence.complete_primary_seed_count >= _minimum_complete_pairs():
        if evidence.legitimate_admitted_count > 0:
            return (
                ClaimId.AUTHORITY_TRANSITION,
                ClaimState.SUPPORTED,
                "Completed primary seeds admit at least one legitimate target through "
                "the non-source path with no source-artifact production input.",
            )
        return (
            ClaimId.AUTHORITY_TRANSITION,
            ClaimState.NOT_SUPPORTED,
            "Complete primary seeds contain no legitimate non-source admission.",
        )
    return _not_tested(ClaimId.AUTHORITY_TRANSITION)


def _direct_source_exclusion_claim(evidence: DirectSourceExclusionEvidence) -> ClaimDerivation:
    if evidence.provenance_violation_count > 0:
        return (
            ClaimId.DIRECT_SOURCE_EXCLUSION,
            ClaimState.NOT_SUPPORTED,
            "A source artifact or source-derived checkpoint appears in an honest "
            "production input.",
        )
    if evidence.cells_checked:
        return (
            ClaimId.DIRECT_SOURCE_EXCLUSION,
            ClaimState.SUPPORTED,
            "Checked source-excluded production inputs contain no source artifact.",
        )
    return _not_tested(ClaimId.DIRECT_SOURCE_EXCLUSION)


def _conditional_non_interference_claim(
    evidence: ConditionalNonInterferenceEvidence,
) -> ClaimDerivation:
    if not evidence.fixture_executed or not evidence.source_commitments_differ:
        return _not_tested(ClaimId.CONDITIONAL_NON_INTERFERENCE)
    if evidence.honest_updates_identical and evidence.production_update_identical:
        return (
            ClaimId.CONDITIONAL_NON_INTERFERENCE,
            ClaimState.SUPPORTED,
            "Distinct source commitments leave honest reproduction updates and the "
            "source-excluded production update unchanged.",
        )
    return (
        ClaimId.CONDITIONAL_NON_INTERFERENCE,
        ClaimState.NOT_SUPPORTED,
        "An honest reproduction or source-excluded production update changes with the source.",
    )


def _information_arrival_claim(evidence: InformationArrivalEvidence) -> ClaimDerivation:
    if evidence.admission_before_t_evidence or (
        evidence.five_row_path_active and evidence.synthesis_before_t_reproduction_evidence
    ):
        return (
            ClaimId.INFORMATION_ARRIVAL_DELAY,
            ClaimState.NOT_SUPPORTED,
            "Admission or five-row synthesis occurs before its evidence time.",
        )
    if evidence.records_complete and evidence.wall_clock_components_recorded:
        return (
            ClaimId.INFORMATION_ARRIVAL_DELAY,
            ClaimState.SUPPORTED,
            "No admission precedes T_evidence, five-row synthesis waits for reproduction "
            "evidence, and post-evidence wall-clock components are recorded separately.",
        )
    return _not_tested(ClaimId.INFORMATION_ARRIVAL_DELAY)


def _post_evidence_efficiency_claim(evidence: PostEvidenceEfficiencyEvidence) -> ClaimDerivation:
    if not evidence.measurement_executed:
        return _not_tested(ClaimId.POST_EVIDENCE_EFFICIENCY)
    if evidence.all_repetitions_complete and evidence.median_iqr_valid:
        return (
            ClaimId.POST_EVIDENCE_EFFICIENCY,
            ClaimState.SUPPORTED,
            "Prescribed timing repetitions completed and median/IQR resource measures are valid.",
        )
    return (
        ClaimId.POST_EVIDENCE_EFFICIENCY,
        ClaimState.NOT_SUPPORTED,
        "Efficiency repetitions or median/IQR resource measures are incomplete.",
    )


def _iot_ids_application_claim(evidence: IotIdsApplicationEvidence) -> ClaimDerivation:
    if not evidence.primary_executed:
        return _not_tested(ClaimId.IOT_IDS_APPLICATION)
    if not evidence.primary_valid:
        return (
            ClaimId.IOT_IDS_APPLICATION,
            ClaimState.NOT_SUPPORTED,
            "The primary IoT IDS program is invalid.",
        )
    if evidence.secondary_executed and evidence.secondary_valid:
        return (
            ClaimId.IOT_IDS_APPLICATION,
            ClaimState.SUPPORTED,
            "Primary and secondary IoT IDS programs completed inside their declared boundaries.",
        )
    if evidence.secondary_blocked_by_data and not evidence.secondary_executed:
        return (
            ClaimId.IOT_IDS_APPLICATION,
            ClaimState.PARTIALLY_SUPPORTED,
            "The primary IoT IDS program is valid and the secondary program is untested "
            "for data availability or schema reasons.",
        )
    if evidence.secondary_executed and not evidence.secondary_valid:
        return (
            ClaimId.IOT_IDS_APPLICATION,
            ClaimState.NOT_SUPPORTED,
            "The secondary IoT IDS program executed and is invalid.",
        )
    return _not_tested(ClaimId.IOT_IDS_APPLICATION)


def _comparison_claims(
    collapse_decisions: tuple[CollapseDecision, ...] | None,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    support: ClaimSupportEvidence | None,
) -> tuple[ClaimDerivation, ...]:
    derived: list[ClaimDerivation] = []
    salvage = _malicious_source_salvage_claim(collapse_decisions, comparison_results, support)
    if salvage is not None:
        derived.append(salvage)
    granularity = _capability_granularity_claim(comparison_results)
    if granularity is not None:
        derived.append(granularity)
    heterogeneity = _heterogeneity_claim(comparison_results)
    if heterogeneity is not None:
        derived.append(heterogeneity)
    generalization = _secondary_generalization_claim(comparison_results)
    if generalization is not None:
        derived.append(generalization)
    reproducibility = _reproducibility_claim(comparison_results, support)
    if reproducibility is not None:
        derived.append(reproducibility)
    return tuple(derived)


def _malicious_source_salvage_claim(
    collapse_decisions: tuple[CollapseDecision, ...] | None,
    comparison_results: tuple[ComparisonFamilyResult, ...],
    support: ClaimSupportEvidence | None,
) -> ClaimDerivation | None:
    decisions = tuple(
        decision
        for decision in collapse_decisions or ()
        if decision.kind is CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION
    )
    families = tuple(
        family
        for family in comparison_results
        if family.family is ComparisonFamily.SOURCE_EXCLUSION_CENTRAL_EFFECT
    )
    if len(decisions) != 1 or len(families) != 1:
        return None
    decision = decisions[0]
    family = families[0]
    expected = _registered(lambda item: item.family is family.family)
    observed_names = tuple(sorted(item.definition.comparison_name for item in family.comparisons))
    expected_names = tuple(sorted(item.comparison_name for item in expected))
    complete = observed_names == expected_names and all(
        _is_resolved(item) for item in family.comparisons
    )
    if not complete or not collapse_decision_matches_family(decision, family):
        return None
    admitted = None if support is None else support.legitimate_admission_without_source
    if not decision.survives:
        return (
            ClaimId.MALICIOUS_SOURCE_SALVAGE,
            ClaimState.NOT_SUPPORTED,
            "The direct source-exclusion survival rule fails.",
        )
    if admitted is True:
        return (
            ClaimId.MALICIOUS_SOURCE_SALVAGE,
            ClaimState.SUPPORTED,
            "Source exclusion survives and a legitimate target is admitted without the source.",
        )
    if admitted is False:
        return (
            ClaimId.MALICIOUS_SOURCE_SALVAGE,
            ClaimState.NOT_SUPPORTED,
            "Source exclusion survives but no legitimate target is admitted without the source.",
        )
    return _not_tested(ClaimId.MALICIOUS_SOURCE_SALVAGE)


def _capability_granularity_claim(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> ClaimDerivation | None:
    definitions = _registered(
        lambda item: (
            item.experiment == CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME
            and item.metric is ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE
            and item.method is CapabilityContractScope.BROAD_TARGET_ONLY
        )
    )
    if not definitions:
        return None
    resolved: list[ComparisonResult] = []
    for definition in definitions:
        comparison = _unique_comparison(comparison_results, definition)
        if comparison is None or not _is_resolved(comparison):
            return None
        resolved.append(comparison)
    threshold = _false_same_rate_minimum()
    if any(
        _statistically_supported(comparison)
        and comparison.mean_paired_difference is not None
        and comparison.mean_paired_difference >= threshold
        for comparison in resolved
    ):
        return (
            ClaimId.CAPABILITY_GRANULARITY_BOUNDARY,
            ClaimState.SUPPORTED,
            "At least one broad-contract mixture exceeds the false-equivalence minimum "
            "with a significant paired test.",
        )
    return (
        ClaimId.CAPABILITY_GRANULARITY_BOUNDARY,
        ClaimState.NULL_RESULT,
        "Completed broad-contract mixtures do not establish the false-equivalence boundary.",
    )


def _heterogeneity_claim(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> ClaimDerivation | None:
    any_resolved = False
    highest: HeterogeneityRegime | None = None
    required_metrics = (
        ComparisonMetric.LEGITIMATE_ADMISSION,
        ComparisonMetric.WORST_DOMAIN_TARGET_F1,
    )
    for regime in reversed(tuple(HeterogeneityRegime)):
        if regime is HeterogeneityRegime.NATURAL:
            continue
        pair = tuple(
            _unique_comparison(
                comparison_results,
                definition,
            )
            for definition in _registered(
                lambda item, regime=regime: (
                    item.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME
                    and item.method is CoreMethodIdentity.RESOLVED_FEDSIRA_CORE
                    and item.scientific_scenario == regime
                    and item.metric in required_metrics
                )
            )
        )
        if len(pair) != len(required_metrics) or any(
            item is None or not _is_resolved(item) for item in pair
        ):
            continue
        any_resolved = True
        if highest is None and all(
            item is not None and _within_heterogeneity_tolerance(item) for item in pair
        ):
            highest = regime
    if highest is not None:
        return (
            ClaimId.HETEROGENEITY_BOUNDARY,
            ClaimState.CONDITIONAL,
            f"Highest passing tested heterogeneity regime is {highest.value}.",
        )
    if any_resolved:
        return (
            ClaimId.HETEROGENEITY_BOUNDARY,
            ClaimState.CONDITIONAL,
            f"Highest passing tested heterogeneity regime is {HeterogeneityRegime.NATURAL}.",
        )
    return None


def _secondary_generalization_claim(
    comparison_results: tuple[ComparisonFamilyResult, ...],
) -> ClaimDerivation | None:
    definitions = _registered(lambda item: item.family is ComparisonFamily.SECONDARY_GENERALIZATION)
    resolved: list[ComparisonResult] = []
    for definition in definitions:
        comparison = _unique_comparison(comparison_results, definition)
        if comparison is None or not _is_resolved(comparison):
            return None
        resolved.append(comparison)
    if not resolved:
        return None
    if all(_statistically_supported(comparison) for comparison in resolved):
        return (
            ClaimId.SECONDARY_GENERALIZATION,
            ClaimState.SUPPORTED,
            "Both secondary scenarios are non-inferior to the predeclared simple comparators.",
        )
    return (
        ClaimId.SECONDARY_GENERALIZATION,
        ClaimState.NOT_SUPPORTED,
        "A completed secondary comparison misses the non-inferiority rule.",
    )


def _reproducibility_claim(
    comparison_results: tuple[ComparisonFamilyResult, ...],
    support: ClaimSupportEvidence | None,
) -> ClaimDerivation | None:
    definitions = _registered(
        lambda item: item.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
    )
    if not definitions:
        return None
    certified = None if support is None else support.shared_failure_certified
    resolved: list[ComparisonResult] = []
    incomplete = False
    for definition in definitions:
        comparison = _unique_comparison(comparison_results, definition)
        if comparison is None or not _is_resolved(comparison):
            incomplete = True
            continue
        resolved.append(comparison)
    degraded = any(_statistically_supported(comparison) for comparison in resolved)
    if certified is True and degraded:
        return (
            ClaimId.REPRODUCIBILITY_IS_NOT_TRUTH,
            ClaimState.SUPPORTED,
            "A shared-failure fixture certifies while a clean-oracle degradation "
            "exceeds its material threshold.",
        )
    if certified is False and degraded:
        return (
            ClaimId.REPRODUCIBILITY_IS_NOT_TRUTH,
            ClaimState.NOT_SUPPORTED,
            "Clean-oracle degradation is present but the shared-failure fixture "
            "does not certify.",
        )
    if not incomplete and resolved and not degraded:
        return (
            ClaimId.REPRODUCIBILITY_IS_NOT_TRUTH,
            ClaimState.NOT_SUPPORTED,
            "Completed shared-failure comparisons do not produce a material "
            "clean-oracle degradation.",
        )
    return None


def _not_tested(claim_id: ClaimId) -> ClaimDerivation:
    return (
        claim_id,
        ClaimState.NOT_TESTED,
        "Claim-bearing evidence and decision artifacts are not available.",
    )
