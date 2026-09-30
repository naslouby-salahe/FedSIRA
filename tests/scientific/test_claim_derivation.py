from fedsira.domain.enums import (
    CapabilityContractScope,
    ClaimId,
    ClaimState,
    ComparisonFamily,
    ComparisonMetric,
    CoreMethodIdentity,
    HeterogeneityRegime,
    OpeningMode,
)
from fedsira.evaluation.claim_support import (
    AuthorityTransitionEvidence,
    ClaimSupportEvidence,
    ConditionalNonInterferenceEvidence,
    DirectSourceExclusionEvidence,
    InformationArrivalEvidence,
    IotIdsApplicationEvidence,
    PostEvidenceEfficiencyEvidence,
    PreEvidenceLimitEvidence,
    UnsupportedCapabilityEvidence,
)
from fedsira.evaluation.comparisons import (
    ComparisonDefinition,
    ComparisonFamilyResult,
    ComparisonResult,
    ComparisonState,
    build_comparison_registry,
)
from fedsira.evaluation.summaries import claim_summary_from_collapse_evidence
from fedsira.experiments.collapse import CollapseDecision, CollapseDecisionKind
from fedsira.experiments.definitions import (
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
)
from fedsira.runtime import current_application_context


def _states(
    collapse_decisions: tuple[CollapseDecision, ...] | None = None,
    comparison_results: tuple[ComparisonFamilyResult, ...] = (),
    support: ClaimSupportEvidence | None = None,
) -> dict[ClaimId, ClaimState]:
    summary = claim_summary_from_collapse_evidence(
        collapse_decisions,
        comparison_results,
        support=support,
    )
    return {decision.claim_id: decision.state for decision in summary.decisions}


def _comparison(
    definition: ComparisonDefinition,
    state: ComparisonState,
    mean: float,
    adjusted_p: float,
) -> ComparisonResult:
    return ComparisonResult(
        definition=definition,
        paired_differences=(mean,),
        complete_seed_count=1,
        mean_paired_difference=mean,
        median_paired_difference=mean,
        paired_standardized_effect=0.0,
        raw_p_value=adjusted_p,
        adjusted_p_value=adjusted_p,
        confidence_interval=(mean, mean),
        materiality_passes=state is ComparisonState.PASSED,
        comparison_state=state,
    )


def _heterogeneity_basis(results: tuple[ComparisonResult, ...]) -> str:
    decision = next(
        item
        for item in claim_summary_from_collapse_evidence(None, _families(results)).decisions
        if item.claim_id is ClaimId.HETEROGENEITY_BOUNDARY
    )
    assert decision.state is ClaimState.CONDITIONAL
    return decision.basis


def _families(results: tuple[ComparisonResult, ...]) -> tuple[ComparisonFamilyResult, ...]:
    grouped: dict[ComparisonFamily, list[ComparisonResult]] = {}
    for result in results:
        grouped.setdefault(result.definition.family, []).append(result)
    return tuple(
        ComparisonFamilyResult(family=family, comparisons=tuple(items))
        for family, items in grouped.items()
    )


def test_structural_claim_rules_follow_section_35() -> None:
    supported = ClaimSupportEvidence(
        unsupported_capability=UnsupportedCapabilityEvidence(
            checked=True,
            target_absent_from_anchor_train=True,
            target_absent_from_anchor_validation=True,
            target_present_in_required_roles=True,
            source_byzantine_setting_instantiated=True,
            anchor_role_leakage=False,
            missing_target_blocks_primary=False,
        ),
        pre_evidence_limit=PreEvidenceLimitEvidence(
            assumptions_map_to_implementation=True,
            fixture_passed=True,
            trusted_side_information_declared=True,
            transcript_law_changed_without_narrowing=False,
        ),
        authority_transition=AuthorityTransitionEvidence(
            source_is_honest_path_input=False,
            provenance_violation_count=0,
            complete_primary_seed_count=current_application_context().scientific_config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_inference,
            legitimate_admitted_count=1,
        ),
        direct_source_exclusion=DirectSourceExclusionEvidence(
            cells_checked=True,
            provenance_violation_count=0,
        ),
        conditional_non_interference=ConditionalNonInterferenceEvidence(
            fixture_executed=True,
            source_commitments_differ=True,
            honest_updates_identical=True,
            production_update_identical=True,
        ),
        information_arrival=InformationArrivalEvidence(
            records_complete=True,
            admission_before_t_evidence=False,
            five_row_path_active=True,
            synthesis_before_t_reproduction_evidence=False,
            wall_clock_components_recorded=True,
        ),
        post_evidence_efficiency=PostEvidenceEfficiencyEvidence(
            measurement_executed=True,
            all_repetitions_complete=True,
            median_iqr_valid=True,
        ),
        iot_ids_application=IotIdsApplicationEvidence(
            primary_executed=True,
            primary_valid=True,
            secondary_executed=False,
            secondary_valid=False,
            secondary_blocked_by_data=True,
        ),
    )
    states = _states(support=supported)
    assert states[ClaimId.UNSUPPORTED_CAPABILITY_PROBLEM] is ClaimState.SUPPORTED
    assert states[ClaimId.PRE_EVIDENCE_INFORMATION_LIMIT] is ClaimState.SUPPORTED
    assert states[ClaimId.AUTHORITY_TRANSITION] is ClaimState.SUPPORTED
    assert states[ClaimId.DIRECT_SOURCE_EXCLUSION] is ClaimState.SUPPORTED
    assert states[ClaimId.CONDITIONAL_NON_INTERFERENCE] is ClaimState.SUPPORTED
    assert states[ClaimId.INFORMATION_ARRIVAL_DELAY] is ClaimState.SUPPORTED
    assert states[ClaimId.POST_EVIDENCE_EFFICIENCY] is ClaimState.SUPPORTED
    assert states[ClaimId.IOT_IDS_APPLICATION] is ClaimState.PARTIALLY_SUPPORTED

    failed = supported.model_copy(
        update={
            "authority_transition": AuthorityTransitionEvidence(
                source_is_honest_path_input=True,
                provenance_violation_count=0,
                complete_primary_seed_count=0,
                legitimate_admitted_count=0,
            ),
            "direct_source_exclusion": DirectSourceExclusionEvidence(
                cells_checked=False,
                provenance_violation_count=1,
            ),
            "conditional_non_interference": ConditionalNonInterferenceEvidence(
                fixture_executed=True,
                source_commitments_differ=True,
                honest_updates_identical=False,
                production_update_identical=True,
            ),
            "information_arrival": InformationArrivalEvidence(
                records_complete=True,
                admission_before_t_evidence=True,
                five_row_path_active=False,
                synthesis_before_t_reproduction_evidence=False,
                wall_clock_components_recorded=True,
            ),
            "iot_ids_application": IotIdsApplicationEvidence(
                primary_executed=True,
                primary_valid=False,
                secondary_executed=False,
                secondary_valid=False,
                secondary_blocked_by_data=False,
            ),
        }
    )
    failed_states = _states(support=failed)
    assert failed_states[ClaimId.AUTHORITY_TRANSITION] is ClaimState.NOT_SUPPORTED
    assert failed_states[ClaimId.DIRECT_SOURCE_EXCLUSION] is ClaimState.NOT_SUPPORTED
    assert failed_states[ClaimId.CONDITIONAL_NON_INTERFERENCE] is ClaimState.NOT_SUPPORTED
    assert failed_states[ClaimId.INFORMATION_ARRIVAL_DELAY] is ClaimState.NOT_SUPPORTED
    assert failed_states[ClaimId.IOT_IDS_APPLICATION] is ClaimState.NOT_SUPPORTED
    assert (
        _states(
            support=ClaimSupportEvidence(
                pre_evidence_limit=PreEvidenceLimitEvidence(
                    assumptions_map_to_implementation=True,
                    fixture_passed=True,
                    trusted_side_information_declared=True,
                    transcript_law_changed_without_narrowing=True,
                )
            )
        )[ClaimId.PRE_EVIDENCE_INFORMATION_LIMIT]
        is ClaimState.NOT_SUPPORTED
    )


def test_comparison_backed_boundary_claims_follow_registered_families() -> None:
    registry = build_comparison_registry()
    evidence_thresholds = current_application_context().scientific_config.evidence_thresholds
    granularity = evidence_thresholds.capability_granularity_boundary
    threshold = granularity.false_same_capability_certification_rate_minimum
    capability = tuple(
        definition
        for definition in registry
        if definition.experiment == CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME
        and definition.metric is ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE
        and definition.method is CapabilityContractScope.BROAD_TARGET_ONLY
    )
    capability_results = tuple(
        _comparison(
            definition,
            ComparisonState.PASSED if index == 0 else ComparisonState.FAILED,
            threshold if index == 0 else 0.0,
            0.0 if index == 0 else 1.0,
        )
        for index, definition in enumerate(capability)
    )
    supported = _states(comparison_results=_families(capability_results))
    assert supported[ClaimId.CAPABILITY_GRANULARITY_BOUNDARY] is ClaimState.SUPPORTED
    null_results = tuple(
        _comparison(definition, ComparisonState.FAILED, 0.0, 1.0) for definition in capability
    )
    assert (
        _states(comparison_results=_families(null_results))[ClaimId.CAPABILITY_GRANULARITY_BOUNDARY]
        is ClaimState.NULL_RESULT
    )
    assert (
        _states(comparison_results=_families(capability_results[:1]))[
            ClaimId.CAPABILITY_GRANULARITY_BOUNDARY
        ]
        is ClaimState.NOT_TESTED
    )

    heterogeneity = tuple(
        definition
        for definition in registry
        if definition.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME
        and definition.method is CoreMethodIdentity.RESOLVED_FEDSIRA_CORE
        and definition.scientific_scenario == HeterogeneityRegime.FEATURE_SHIFT_1_0
        and definition.metric
        in (ComparisonMetric.LEGITIMATE_ADMISSION, ComparisonMetric.WORST_DOMAIN_TARGET_F1)
    )
    assert len(heterogeneity) == 2
    conditional = _states(
        comparison_results=_families(
            tuple(
                _comparison(definition, ComparisonState.PASSED, 0.0, 0.0)
                for definition in heterogeneity
            )
        )
    )
    decision = next(
        item
        for item in claim_summary_from_collapse_evidence(
            None,
            _families(
                tuple(
                    _comparison(definition, ComparisonState.PASSED, 0.0, 0.0)
                    for definition in heterogeneity
                )
            ),
        ).decisions
        if item.claim_id is ClaimId.HETEROGENEITY_BOUNDARY
    )
    assert conditional[ClaimId.HETEROGENEITY_BOUNDARY] is ClaimState.CONDITIONAL
    assert HeterogeneityRegime.FEATURE_SHIFT_1_0.value in decision.basis
    within_margin = _heterogeneity_basis(
        tuple(
            _comparison(definition, ComparisonState.FAILED, -0.01, 0.20)
            for definition in heterogeneity
        )
    )
    assert HeterogeneityRegime.FEATURE_SHIFT_1_0.value in within_margin
    beyond_margin = _heterogeneity_basis(
        tuple(
            _comparison(definition, ComparisonState.FAILED, -0.20, 0.20)
            for definition in heterogeneity
        )
    )
    assert HeterogeneityRegime.NATURAL.value in beyond_margin
    assert HeterogeneityRegime.FEATURE_SHIFT_1_0.value not in beyond_margin
    split_margin = _heterogeneity_basis(
        tuple(
            _comparison(
                definition,
                ComparisonState.FAILED,
                -0.01 if definition.metric is ComparisonMetric.LEGITIMATE_ADMISSION else -0.20,
                0.20,
            )
            for definition in heterogeneity
        )
    )
    assert HeterogeneityRegime.NATURAL.value in split_margin
    assert HeterogeneityRegime.FEATURE_SHIFT_1_0.value not in split_margin

    secondary = tuple(
        definition
        for definition in registry
        if definition.family is ComparisonFamily.SECONDARY_GENERALIZATION
    )
    assert (
        _states(
            comparison_results=_families(
                tuple(
                    _comparison(definition, ComparisonState.PASSED, 0.0, 0.0)
                    for definition in secondary
                )
            )
        )[ClaimId.SECONDARY_GENERALIZATION]
        is ClaimState.SUPPORTED
    )
    assert (
        _states(
            comparison_results=_families(
                tuple(
                    _comparison(
                        definition,
                        ComparisonState.FAILED if index == 0 else ComparisonState.PASSED,
                        0.0,
                        1.0 if index == 0 else 0.0,
                    )
                    for index, definition in enumerate(secondary)
                )
            )
        )[ClaimId.SECONDARY_GENERALIZATION]
        is ClaimState.NOT_SUPPORTED
    )

    epistemic = tuple(
        definition
        for definition in registry
        if definition.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME
    )
    assert (
        _states(
            comparison_results=_families(
                (_comparison(epistemic[0], ComparisonState.PASSED, 0.2, 0.0),)
            ),
            support=ClaimSupportEvidence(shared_failure_certified=True),
        )[ClaimId.REPRODUCIBILITY_IS_NOT_TRUTH]
        is ClaimState.SUPPORTED
    )
    assert (
        _states(
            comparison_results=_families(
                tuple(
                    _comparison(definition, ComparisonState.FAILED, 0.0, 1.0)
                    for definition in epistemic
                )
            ),
            support=ClaimSupportEvidence(shared_failure_certified=True),
        )[ClaimId.REPRODUCIBILITY_IS_NOT_TRUTH]
        is ClaimState.NOT_SUPPORTED
    )


def test_malicious_source_salvage_requires_survival_and_non_source_admission() -> None:
    registry = build_comparison_registry()
    definitions = tuple(
        definition
        for definition in registry
        if definition.family is ComparisonFamily.SOURCE_EXCLUSION_CENTRAL_EFFECT
    )
    results = tuple(
        _comparison(definition, ComparisonState.PASSED, 0.0, 1.0) for definition in definitions
    )
    decision = CollapseDecision(
        kind=CollapseDecisionKind.DIRECT_SOURCE_EXCLUSION,
        comparator=OpeningMode.CANDIDATE_FREE,
        survives=True,
        primary_material_effect=definitions[0].metric,
        adjusted_p_value=1.0,
        constraint_passes=True,
        reason="fixture",
    )
    family = _families(results)
    assert (
        _states(
            collapse_decisions=(decision,),
            comparison_results=family,
            support=ClaimSupportEvidence(legitimate_admission_without_source=True),
        )[ClaimId.MALICIOUS_SOURCE_SALVAGE]
        is ClaimState.SUPPORTED
    )
    assert (
        _states(
            collapse_decisions=(decision,),
            comparison_results=family,
            support=ClaimSupportEvidence(legitimate_admission_without_source=False),
        )[ClaimId.MALICIOUS_SOURCE_SALVAGE]
        is ClaimState.NOT_SUPPORTED
    )
    rejected = decision.model_copy(
        update={
            "survives": False,
            "primary_material_effect": None,
            "adjusted_p_value": None,
            "constraint_passes": False,
        }
    )
    assert (
        _states(
            collapse_decisions=(rejected,),
            comparison_results=family,
            support=ClaimSupportEvidence(legitimate_admission_without_source=True),
        )[ClaimId.MALICIOUS_SOURCE_SALVAGE]
        is ClaimState.NOT_SUPPORTED
    )
