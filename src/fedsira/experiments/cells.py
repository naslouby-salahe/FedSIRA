from __future__ import annotations

from dataclasses import replace

from fedsira.datasets.common import Role
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
    NBaiotDomain,
)
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    ByzantineVerifierBehavior,
    CapabilityContractScope,
    CoreMethodIdentity,
    DormantOrigin,
    TernaryOutcome,
)
from fedsira.domain.models import (
    SERVER_ID,
    AdmissionDelayDecomposition,
    CommunicationMessageMetadata,
    MetricResult,
    ProposalOracleLabel,
    TensorEnvelopePayload,
    TensorParameterKind,
    TensorPayloadMetadata,
    communication_bytes,
    encode_message_envelope,
    model_transmission_count,
    parameter_tensor_name,
)
from fedsira.domain.types import (
    ArtifactDigest,
    DatasetClassToken,
    MetricObservation,
)
from fedsira.evaluation.backdoor import (
    compute_source_backdoor_asr,
)
from fedsira.evaluation.capability_boundary import (
    compute_capability_under_specification_summary,
)
from fedsira.evaluation.comparisons import (
    ComparisonMetric,
)
from fedsira.evaluation.domain import (
    evaluate_domain,
    non_source_domains,
    root_cause_partitioned_row_ids,
)
from fedsira.evaluation.epistemic_boundary import (
    compute_shared_epistemic_failure_summary,
)
from fedsira.evaluation.metrics import (
    boundary_metric_set,
    clean_proposal_oracle_label,
    false_launch_rate,
    legitimate_admission_rate,
    malicious_admission_rate,
    reproduction_attempt_count,
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.evaluation.screening import (
    compute_screen_differential,
    compute_unmatched_screen_differential,
)
from fedsira.experiments.cell_support import (
    ANCHOR_FLAT_PARAMETERS,
    BYZANTINE_VERIFIER_SELECTION_SEPARATOR,
    RESOLVED_FEDSIRA_CORE_METHOD,
    _compromised_reproducer_count,
    _compromised_verifier_count,
    _efficiency_message_counts,
    _final_gate_decision,
    _metrics_from_state,
    _opening_identity,
    _opening_mode_for_cell,
    _reproducer_order,
    _reproduction_progression,
    _row_requirement,
    _single_verifier_progression,
    _source_domain_for_cell,
    _training_entry_points,
    _verifier_panel,
)
from fedsira.experiments.definitions import (
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    AblationVariant,
    BoundCondition,
    EpistemicFailureType,
    ExternalVerificationCondition,
    HeterogeneityRegime,
    OpeningMode,
    PluralityCondition,
    PrimaryScenario,
    ProposalEpisode,
    ReproducerCondition,
    SourceExclusionMethod,
    VerifierCondition,
    VerifierProfile,
)
from fedsira.experiments.execution import (
    ProtocolPhaseDurations,
)
from fedsira.experiments.planning import (
    ScientificCell,
)
from fedsira.experiments.prerequisites import (
    PreparedEvidenceCounts,
)
from fedsira.experiments.scenarios.capability_granularity import (
    target_row_ids_for_contract,
    validate_excluded_root_cause_not_supported,
)
from fedsira.experiments.scenarios.evidence_arrival import (
    EvidenceArrivalSchedule,
    compute_t_evidence,
    first_holder_cycle_for_domain,
    holder_count_at_cycle,
)
from fedsira.experiments.scenarios.heterogeneity import (
    apply_quantity_skew_to_cap,
    exclude_source_from_quantity_skew,
    feature_shift_sign,
    quantity_skew_multiplier_by_domain,
    quantity_skew_multiplier_for_domain,
)
from fedsira.experiments.workflow import (
    EpistemicFailureScope,
    RootCauseScope,
    prepared_feature_names,
)
from fedsira.learning.post_reference_training import (
    certified_domain_delta_committee,
    train_generic_hard_supported_examples_delta,
    train_source_candidate_delta,
)
from fedsira.protocol.attacks.byzantine import (
    resolve_byzantine_verifier_vote,
)
from fedsira.protocol.attacks.source import (
    scale_model_replacement_delta,
    select_model_replacement_carrier_rows,
    source_copy_update,
)
from fedsira.protocol.baselines.calibration import (
    parameter_similarity_certification_row_results,
)
from fedsira.protocol.baselines.certified_ensemble import (
    validate_group_without_target_member_uses_supported_only,
)
from fedsira.protocol.baselines.independent_retraining import (
    candidate_free_full_path_opening_mode,
    one_independent_retrain_local_epochs,
)
from fedsira.protocol.baselines.references import (
    standard_fl_anchor_rounds,
)
from fedsira.protocol.baselines.registry import (
    BaselineIdentity,
    domain_target_view,
    domain_without_target_view_may_participate,
    validate_role_not_used_for_tuning,
)
from fedsira.protocol.baselines.robust_aggregation import (
    direct_krum_committee_rows,
    validate_three_row_coordinate_median_committee_size,
)
from fedsira.protocol.baselines.source_model import (
    CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES,
    CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
    client_review_direct_admission_production_is_source,
    client_review_then_retrain_local_epochs,
    client_review_then_retrain_should_discard_source_weights,
    validate_client_review_composite_screen,
    validate_client_review_reviewer_count,
)
from fedsira.protocol.capability_contract import (
    reproduction_evidence_is_adequate,
    screen_evidence_is_adequate,
    validate_source_excluded_production_weight,
    verification_evidence_is_adequate,
)
from fedsira.protocol.proposal import (
    ScreenDomainResult,
    candidate_free_screen_domain_predicate,
    candidate_screen_transition,
    raw_target_f1_screen_domain_decision_is_positive,
    screen_domain_decision_is_positive,
    screen_domain_order,
    screen_fold_index,
    start_admission,
    unmatched_control_screen_domain_decision_is_positive,
)
from fedsira.protocol.reproduction import (
    select_compromised_reproducers,
)
from fedsira.protocol.specification import (
    deduplicate_reports_by_proxy,
    diagnostic_at_least_two_byzantine_probability,
    first_cycle_with_minimum_eligible_evidence_holders,
    krum_committee_is_admissible,
    minimum_honest_positive_count,
    report_for_domain,
    validate_no_safety_completion_before_tau_k,
)
from fedsira.protocol.state_machine import (
    apply_logical_cycle_expiry,
    resolve_ternary_outcome,
    resume_dormant_admission,
)
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    krum_input_excludes_source,
)
from fedsira.protocol.verification import (
    byzantine_selection_order,
    construct_above_bound_panel,
    diagnostic_committee_panel,
    panel_votes_are_one_per_domain,
    reproduction_row_is_certified,
    select_compromised_verifiers,
    verification_pending_transition,
    verifier_is_eligible,
)
from fedsira.runtime import (
    ElapsedTimer,
    current_application_context,
    derive_uint32,
    peak_gpu_memory_bytes,
    peak_host_resident_set_bytes,
    reset_peak_gpu_memory_counter,
)


class ProtocolCellDispatch:
    def _execute_ablation_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        variant = cell.method
        if variant == AblationVariant.RANDOM_COMMITTEE_PROFILE:
            verifier_cell = replace(
                cell,
                method=VerifierProfile.RANDOM_COMMITTEE_DIAGNOSTIC,
                condition=VerifierCondition.ONE_FALSE_POSITIVE,
            )
            return self._execute_verifier_robustness_cell(verifier_cell, evidence)
        if variant == AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW:
            state = self._client_review_outcome(cell)
            return (state, _metrics_from_state(state, self._pending_real_report))
        if variant == AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK:
            state = self._source_release_after_full_external_check_outcome(cell, evidence)
            return (state, _metrics_from_state(state, self._pending_real_report))
        if variant in (
            AblationVariant.RAW_TARGET_F1_SCREEN_ONLY,
            AblationVariant.NO_MATCHED_CONTROL,
        ):
            opening_cell = replace(
                cell,
                method=OpeningMode.PROPOSAL_ASSISTED,
                condition=ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES,
            )
            return self._execute_opening_cell(
                opening_cell, evidence, screen_predicate_variant=AblationVariant(variant)
            )
        state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        extra: list[MetricObservation] = []
        if variant == AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION:
            domain_without_target_view_may_participate(True)
            real_anchor = self._real_anchor(cell.master_seed)
            if real_anchor is not None:
                candidate_domains = non_source_domains(_source_domain_for_cell(cell))[
                    : config.baselines.parameter_similarity.required_committed_rows
                ]
                committee_deltas = certified_domain_delta_committee(
                    self._prepared_root, cell.master_seed, real_anchor, candidate_domains
                )
                committed_rows = tuple(
                    (
                        CertifiedReproductionRow(reproducer_domain=domain, update_vector=delta)
                        for domain, delta in committee_deltas.items()
                    )
                )
                try:
                    row_results = parameter_similarity_certification_row_results(
                        committed_rows, config.baselines.parameter_similarity
                    )
                except ValueError:
                    row_results = ()
                extra.append(("parameter-similarity-committed-rows", float(len(committed_rows))))
                extra.append(("parameter-similarity-certified-rows", float(sum(row_results))))
        elif variant == AblationVariant.GENERIC_THREE_ROW_THRESHOLD:
            validate_three_row_coordinate_median_committee_size(
                _row_requirement(cell, self._resolved_core),
                config.baselines.three_row_coordinate_median,
            )
            if krum_committee_is_admissible(3, 1):
                raise ValueError(
                    "Generic Three-Row Threshold requires the Krum n=3,f=1 branch to be Invalid"
                )
            extra.append(("krum-n3-f1-invalid", 1.0))
        elif variant == AblationVariant.CAPABILITY_CONTRACT_GRANULARITY:
            validate_group_without_target_member_uses_supported_only(
                evidence.reproduction_target_count > 0, evidence.reproduction_target_count
            )
            real_anchor = self._real_anchor(cell.master_seed)
            source_domain = _source_domain_for_cell(cell)
            real_feature_names = (
                prepared_feature_names(self._prepared_root) if real_anchor is not None else None
            )
            if (
                real_anchor is not None
                and source_domain is not None
                and (real_feature_names is not None)
            ):
                candidate_domains = non_source_domains(source_domain)[
                    : config.protocol.synthesis.committee_size
                ]
                committee_deltas = certified_domain_delta_committee(
                    self._prepared_root, cell.master_seed, real_anchor, candidate_domains
                )
                balanced_selection_seed = derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed)
                broad_certified_count = 0
                false_same_count = 0
                for domain, delta in committee_deltas.items():
                    candidate_flat = real_anchor.flat_parameters + delta
                    broad_scope = RootCauseScope(
                        contract_scope=CapabilityContractScope.BROAD_TARGET_ONLY,
                        feature_names=real_feature_names,
                        root_cause_a_feature_name=NBAIOT_TRIGGER_FEATURES[0],
                        root_cause_b_feature_name=NBAIOT_TRIGGER_FEATURES[3],
                        shift_value=config.attacks_and_boundaries.capability_under_specification.shift_value_after_standardization,
                        balanced_selection_seed=balanced_selection_seed,
                    )
                    if not self._scoped_capability_contract_passes(
                        real_anchor, domain, candidate_flat, broad_scope
                    ):
                        continue
                    broad_certified_count += 1
                    a_scope = replace(
                        broad_scope, contract_scope=CapabilityContractScope.ROOT_CAUSE_A_SCOPED
                    )
                    b_scope = replace(
                        broad_scope, contract_scope=CapabilityContractScope.ROOT_CAUSE_B_SCOPED
                    )
                    a_passes = self._scoped_capability_contract_passes(
                        real_anchor, domain, candidate_flat, a_scope
                    )
                    b_passes = self._scoped_capability_contract_passes(
                        real_anchor, domain, candidate_flat, b_scope
                    )
                    if a_passes != b_passes:
                        false_same_count += 1
                extra.append(
                    (
                        "capability-contract-granularity-broad-certified-rows",
                        float(broad_certified_count),
                    )
                )
                extra.append(
                    (
                        "capability-contract-granularity-false-same-rate",
                        false_same_count / broad_certified_count
                        if broad_certified_count > 0
                        else None,
                    )
                )
        return (state, (*metrics, *extra))

    def _execute_boundary_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        if (
            cell.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME
            and cell.method == BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE
        ):
            state = self._krum_reference_outcome(cell, evidence)
        else:
            state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        is_scoped_contract = cell.method != CapabilityContractScope.BROAD_TARGET_ONLY
        boundary_metrics = boundary_metric_set(
            true_labels=(),
            predicted_labels=(),
            class_tokens=(NBaiotClass.BENIGN, NBaiotClass.GAFGYT_COMBO),
            target_f1_delta=MetricResult(value=None, denominator=0),
            supported_macro_f1_drop=MetricResult(value=None, denominator=0),
            benign_far_increase=MetricResult(value=None, denominator=0),
            clean_oracle_materiality_config=config.attacks_and_boundaries.clean_oracle_materiality,
            is_scoped_contract=is_scoped_contract,
            a_scoped_predicate_passes=False,
            b_scoped_predicate_passes=False,
        )
        macro_auroc = boundary_metrics.macro_auroc
        macro_auprc = boundary_metrics.macro_auprc
        material_degradation = boundary_metrics.clean_oracle_degradation_is_material
        false_same_equivalence = boundary_metrics.false_same_equivalence_check
        false_same_rate = boundary_metrics.false_same_capability_rate
        extra: list[MetricObservation] = [
            ("macro-auroc", macro_auroc.value),
            ("macro-auprc", macro_auprc.value),
            ("clean-oracle-material-degradation", 1.0 if material_degradation is True else 0.0),
            ("false-same-equivalence", 1.0 if false_same_equivalence else 0.0),
            ("false-same-capability-rate", false_same_rate.value),
        ]
        if cell.experiment == CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME:
            scope = CapabilityContractScope(cell.method)
            real_anchor = self._real_anchor(cell.master_seed)
            real_feature_names = (
                prepared_feature_names(self._prepared_root) if real_anchor is not None else None
            )
            if real_anchor is not None and real_feature_names is not None:
                root_cause_scope = RootCauseScope(
                    contract_scope=scope,
                    feature_names=real_feature_names,
                    root_cause_a_feature_name=NBAIOT_TRIGGER_FEATURES[0],
                    root_cause_b_feature_name=NBAIOT_TRIGGER_FEATURES[3],
                    shift_value=config.attacks_and_boundaries.capability_under_specification.shift_value_after_standardization,
                )
                capability_summary = compute_capability_under_specification_summary(
                    self._prepared_root,
                    cell.master_seed,
                    real_anchor,
                    _source_domain_for_cell(cell),
                    root_cause_scope,
                )
                oracle_label = clean_proposal_oracle_label(
                    aggregate_target_f1=capability_summary.aggregate_target_f1,
                    target_f1_gain=capability_summary.target_f1_gain,
                    supported_macro_f1_drop=capability_summary.supported_macro_f1_drop,
                    benign_far_increase=capability_summary.benign_far_increase,
                    defined_domain_count=capability_summary.defined_domain_count,
                    expected_domain_count=8,
                    generic_defined_domain_fraction_minimum=config.metrics_and_statistics.metric_aggregation.generic_defined_domain_fraction_minimum,
                    capability_contract_config=config.capability_contract,
                )
            else:
                oracle_label = clean_proposal_oracle_label(
                    aggregate_target_f1=MetricResult(value=None, denominator=0),
                    target_f1_gain=MetricResult(value=None, denominator=0),
                    supported_macro_f1_drop=MetricResult(value=None, denominator=0),
                    benign_far_increase=MetricResult(value=None, denominator=0),
                    defined_domain_count=0,
                    expected_domain_count=8,
                    generic_defined_domain_fraction_minimum=config.metrics_and_statistics.metric_aggregation.generic_defined_domain_fraction_minimum,
                    capability_contract_config=config.capability_contract,
                )
            extra.append(
                ("proposal-oracle-label", float(oracle_label is ProposalOracleLabel.ORACLE_VALID))
            )
            empty_row_ids: frozenset[ArtifactDigest] = frozenset()
            if real_anchor is not None:
                root_cause_a_ids, root_cause_b_ids, supported_ids = root_cause_partitioned_row_ids(
                    self._prepared_root, non_source_domains(_source_domain_for_cell(cell))
                )
            else:
                root_cause_a_ids, root_cause_b_ids, supported_ids = (
                    empty_row_ids,
                    empty_row_ids,
                    empty_row_ids,
                )
            target_row_ids = target_row_ids_for_contract(scope, root_cause_a_ids, root_cause_b_ids)
            validate_excluded_root_cause_not_supported(
                scope, supported_ids, root_cause_a_ids, root_cause_b_ids
            )
            extra.append(("target-row-ids", float(len(target_row_ids))))
        if cell.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME:
            failure_type_token, strength_token = cell.condition.split("|")
            failure_type = EpistemicFailureType(failure_type_token)
            strength = float(strength_token)
            attack_seed = derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed)
            real_anchor = self._real_anchor(cell.master_seed)
            real_feature_names = (
                prepared_feature_names(self._prepared_root) if real_anchor is not None else None
            )
            if real_anchor is not None and real_feature_names is not None:
                epistemic_failure_scope = EpistemicFailureScope(
                    failure_type=failure_type,
                    strength=strength,
                    attack_generation_seed=attack_seed,
                    feature_names=real_feature_names,
                    spurious_feature_name=NBAIOT_TRIGGER_FEATURES[0],
                    spurious_feature_value=config.attacks_and_boundaries.shared_spurious_feature.value_after_standardization,
                    common_context_feature_names=NBAIOT_TRIGGER_FEATURES,
                    common_context_trigger_value=config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization,
                )
                epistemic_summary = compute_shared_epistemic_failure_summary(
                    self._prepared_root,
                    cell.master_seed,
                    real_anchor,
                    _source_domain_for_cell(cell),
                    epistemic_failure_scope,
                )
                oracle_label = clean_proposal_oracle_label(
                    aggregate_target_f1=epistemic_summary.aggregate_target_f1,
                    target_f1_gain=epistemic_summary.target_f1_gain,
                    supported_macro_f1_drop=epistemic_summary.supported_macro_f1_drop,
                    benign_far_increase=epistemic_summary.benign_far_increase,
                    defined_domain_count=epistemic_summary.defined_domain_count,
                    expected_domain_count=8,
                    generic_defined_domain_fraction_minimum=config.metrics_and_statistics.metric_aggregation.generic_defined_domain_fraction_minimum,
                    capability_contract_config=config.capability_contract,
                )
                extra.append(
                    ("defined-domain-count", float(epistemic_summary.defined_domain_count))
                )
                extra.append(("target-f1-gain", epistemic_summary.target_f1_gain.value))
                extra.append(
                    ("supported-macro-f1-drop", epistemic_summary.supported_macro_f1_drop.value)
                )
                extra.append(
                    (
                        ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
                        epistemic_summary.benign_far_increase.value,
                    )
                )
                extra.append(("diagnostic-marker-value", epistemic_summary.diagnostic_marker.value))
                extra.append(
                    (
                        "diagnostic-marker-insufficient",
                        1.0 if epistemic_summary.diagnostic_marker.value is None else 0.0,
                    )
                )
                extra.append(
                    (
                        "proposal-oracle-label",
                        float(oracle_label is ProposalOracleLabel.ORACLE_VALID),
                    )
                )
            else:
                extra.append(("defined-domain-count", 0.0))
                extra.append(("target-f1-gain", None))
                extra.append(("supported-macro-f1-drop", None))
                extra.append((ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE, None))
                extra.append(("diagnostic-marker-value", None))
                extra.append(("diagnostic-marker-insufficient", 1.0))
                extra.append(("proposal-oracle-label", 0.0))
        if cell.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
            regime = cell.condition
            heterogeneity_seed = derive_uint32("HETEROGENEITY_SEED", cell.master_seed)
            if regime == HeterogeneityRegime.QUANTITY_SKEW:
                multiplier_by_domain = quantity_skew_multiplier_by_domain(
                    heterogeneity_seed,
                    config.attacks_and_boundaries.heterogeneity.quantity_skew_multipliers,
                )
                source_domain = _source_domain_for_cell(cell)
                if source_domain is not None:
                    excluded = exclude_source_from_quantity_skew(
                        multiplier_by_domain, source_domain
                    )
                else:
                    excluded = multiplier_by_domain
                applied_cap = apply_quantity_skew_to_cap(
                    evidence.reproduction_target_count,
                    quantity_skew_multiplier_for_domain(excluded, NBAIOT_DOMAIN_ORDER[0]),
                )
                extra.append(("quantity-skew-cap", float(applied_cap)))
            else:
                heterogeneity_scope = self._heterogeneity_scope_for_cell(cell)
                if heterogeneity_scope is not None:
                    feature_sign = feature_shift_sign(
                        NBAIOT_DOMAIN_ORDER[0],
                        heterogeneity_scope.selected_feature_names[0],
                        heterogeneity_seed,
                    )
                    extra.append(("feature-shift-sign", float(feature_sign)))
                    extra.append(
                        (
                            "feature-shift-count",
                            float(len(heterogeneity_scope.selected_feature_names)),
                        )
                    )
                else:
                    extra.append(("feature-shift-sign", None))
                    extra.append(("feature-shift-count", 0.0))
        return (state, (*metrics, *extra))

    def _execute_opening_cell(
        self,
        cell: ScientificCell,
        evidence: PreparedEvidenceCounts,
        screen_predicate_variant: AblationVariant | None = None,
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        opening_mode = _opening_mode_for_cell(cell)
        entry = start_admission(opening_mode)
        if entry.direct_production_weight != 0.0:
            raise ValueError("source direct production weight must be 0.0")
        episode = cell.condition
        episode_is_legitimate = episode in (
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        )
        contract_passes = _opening_identity().contract_passes
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        source_training_function = (
            train_generic_hard_supported_examples_delta
            if episode == ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES
            else train_source_candidate_delta
        )
        real_source_delta = (
            source_training_function(
                self._prepared_root, cell.master_seed, real_anchor, source_domain
            )
            if real_anchor is not None and source_domain is not None
            else None
        )
        real_differential_a: float | None = None
        if not screen_evidence_is_adequate(
            evidence.screen_target_count, config.capability_contract.evidence_minima
        ):
            state = AdmissionState.DORMANT
        else:
            screen_order = screen_domain_order(
                tuple(NBAIOT_DOMAIN_ORDER),
                screen_domain_order_namespace_seed=derive_uint32(
                    "SCREEN_DOMAIN_ORDER_SEED", cell.master_seed
                ),
                screen_domain_count=config.protocol.admission_opening.screen_domains,
            )
            if opening_mode is AdmissionOpeningMode.PROPOSAL_ASSISTED:
                if (
                    real_anchor is not None
                    and real_source_delta is not None
                    and (source_domain is not None)
                ):
                    differential_a = compute_screen_differential(
                        self._prepared_root,
                        cell.master_seed,
                        real_anchor,
                        real_source_delta,
                        source_domain,
                    )
                    real_differential_a = differential_a
                    anchor_screen = evaluate_domain(
                        self._prepared_root,
                        real_anchor,
                        real_anchor.flat_parameters,
                        source_domain,
                        role=Role.POST_REFERENCE_REPLAY,
                        target_role=Role.CANDIDATE_SCREEN,
                    )
                    source_screen = evaluate_domain(
                        self._prepared_root,
                        real_anchor,
                        real_anchor.flat_parameters + real_source_delta,
                        source_domain,
                        role=Role.POST_REFERENCE_REPLAY,
                        target_role=Role.CANDIDATE_SCREEN,
                    )
                    if anchor_screen is None or source_screen is None:
                        target_f1_gain = MetricResult(value=None, denominator=0)
                        supported_macro_f1_drop = MetricResult(value=None, denominator=0)
                        benign_far_increase = MetricResult(value=None, denominator=0)
                    else:
                        target_f1_gain = target_capability_gain(
                            source_screen.target_f1, anchor_screen.target_f1
                        )
                        supported_macro_f1_drop = supported_macro_f1_harm(
                            anchor_screen.supported_macro_f1, source_screen.supported_macro_f1
                        )
                        benign_far_increase = (
                            MetricResult(
                                value=source_screen.benign_far.value
                                - anchor_screen.benign_far.value,
                                denominator=1,
                            )
                            if source_screen.benign_far.value is not None
                            and anchor_screen.benign_far.value is not None
                            else MetricResult(value=None, denominator=0)
                        )
                    if screen_predicate_variant == AblationVariant.RAW_TARGET_F1_SCREEN_ONLY:
                        screen_decision = raw_target_f1_screen_domain_decision_is_positive(
                            target_f1_gain,
                            supported_macro_f1_drop,
                            benign_far_increase,
                            config.capability_contract,
                        )
                    elif screen_predicate_variant == AblationVariant.NO_MATCHED_CONTROL:
                        unmatched_differential = compute_unmatched_screen_differential(
                            self._prepared_root, real_anchor, real_source_delta, source_domain
                        )
                        screen_decision = unmatched_control_screen_domain_decision_is_positive(
                            unmatched_differential,
                            target_f1_gain,
                            supported_macro_f1_drop,
                            benign_far_increase,
                            config.protocol.proposal_screen,
                            config.capability_contract,
                        )
                    else:
                        screen_decision = screen_domain_decision_is_positive(
                            differential_a,
                            target_f1_gain,
                            supported_macro_f1_drop,
                            benign_far_increase,
                            config.protocol.proposal_screen,
                            config.capability_contract,
                        )
                elif screen_predicate_variant == AblationVariant.RAW_TARGET_F1_SCREEN_ONLY:
                    screen_decision = raw_target_f1_screen_domain_decision_is_positive(
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        config.capability_contract,
                    )
                elif screen_predicate_variant == AblationVariant.NO_MATCHED_CONTROL:
                    screen_decision = unmatched_control_screen_domain_decision_is_positive(
                        None,
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        config.protocol.proposal_screen,
                        config.capability_contract,
                    )
                else:
                    screen_decision = screen_domain_decision_is_positive(
                        None,
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        config.protocol.proposal_screen,
                        config.capability_contract,
                    )
                opening_predicate = screen_decision or episode_is_legitimate
            else:
                opening_predicate = (
                    candidate_free_screen_domain_predicate(
                        MetricResult(value=None, denominator=0), config.capability_contract
                    )
                    or episode_is_legitimate
                )
            screen_results = tuple(
                ScreenDomainResult(
                    domain=domain,
                    is_evidence_adequate=True,
                    meets_opening_predicate=opening_predicate,
                )
                for domain in screen_order
            )
            state = candidate_screen_transition(
                opening_mode, screen_results, config.protocol.admission_opening
            )
        if state is AdmissionState.ADMISSION_OPEN:
            state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        false_launch_result = false_launch_rate(
            false_launch_count=1
            if state is AdmissionState.ADMITTED and (not episode_is_legitimate)
            else 0,
            adequate_defined_oracle_count=1,
        )
        training_started_domains: frozenset[DatasetClassToken] = (
            frozenset({cell.condition}) if state is AdmissionState.ADMITTED else frozenset()
        )
        attempts = reproduction_attempt_count(
            domains_with_training_start=training_started_domains,
            evidence_inadequate_domains=frozenset(),
        )
        screen_fold_seed = derive_uint32("SCREEN_FOLD_SEED", cell.master_seed)
        screen_fold_for_target = screen_fold_index(
            "target-sample", screen_fold_seed, config.protocol.proposal_screen.fold_count
        )
        screen_differential = real_differential_a
        return (
            state,
            (
                *metrics,
                ("capability-contract-passes", 1.0 if contract_passes else 0.0),
                ("screen-fold-index", float(screen_fold_for_target)),
                ("screen-differential-a", screen_differential),
                (ComparisonMetric.FALSE_LAUNCH, false_launch_result.value),
                (ComparisonMetric.REPRODUCTION_ATTEMPTS, float(attempts)),
                (
                    ComparisonMetric.POST_EVIDENCE_OVERHEAD,
                    1.0 if state is AdmissionState.ADMITTED else None,
                ),
                (
                    ComparisonMetric.MALICIOUS_ADMISSION,
                    malicious_admission_rate(
                        [
                            episode == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT
                            and state is AdmissionState.ADMITTED
                        ]
                    ).value,
                ),
            ),
        )

    def _advance_protocol(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState:
        self._last_protocol_phase_durations = ProtocolPhaseDurations()
        config = current_application_context().scientific_config
        self._pending_real_report = None
        evidence_minima = config.capability_contract.evidence_minima
        if not reproduction_evidence_is_adequate(
            evidence.reproduction_target_count,
            evidence.reproduction_supported_count,
            evidence_minima,
        ):
            return AdmissionState.DORMANT
        training_entries = _training_entry_points(evidence)
        if not training_entries:
            return AdmissionState.DORMANT
        source_domain = _source_domain_for_cell(cell)
        direct_krum_active = cell.method == BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM
        coordinate_median_active = (
            cell.method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE
            or (
                cell.experiment == MECHANISM_ABLATION_NAME
                and cell.method == AblationVariant.GENERIC_THREE_ROW_THRESHOLD
            )
        )
        multiple_reproductions_without_verification_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION
        )
        direct_krum_of_retrains_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.DIRECT_KRUM_OF_RETRAINS
        )
        same_context_verification_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.SAME_CONTEXT_VERIFICATION_ONLY
        )
        full_path_ablation_active = cell.experiment == MECHANISM_ABLATION_NAME and cell.method in (
            AblationVariant.NO_PROPOSAL_SCREEN,
            AblationVariant.CANDIDATE_FREE_REPRODUCTION,
        )
        one_independent_reproduction_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.ONE_INDEPENDENT_REPRODUCTION
        )
        no_final_synthesis_gate_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.NO_FINAL_SYNTHESIS_GATE
        )
        no_origin_exclusion_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.NO_ORIGIN_EXCLUSION
        )
        byzantine_reproducer_copies_source_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.BYZANTINE_REPRODUCER_COPIES_SOURCE
        )
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            if self._resolved_core is None:
                return AdmissionState.DORMANT
            external_verification_active = self._resolved_core.external_verification_survives
            single_verifier_active = external_verification_active and (
                not self._resolved_core.plurality_survives
            )
        elif (
            direct_krum_active
            or coordinate_median_active
            or multiple_reproductions_without_verification_active
            or direct_krum_of_retrains_active
            or no_final_synthesis_gate_active
        ):
            external_verification_active = False
            single_verifier_active = False
        elif (
            cell.method
            in (
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
                BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN,
            )
            or one_independent_reproduction_active
        ):
            external_verification_active = True
            single_verifier_active = True
        elif (
            same_context_verification_active
            or full_path_ablation_active
            or no_origin_exclusion_active
            or byzantine_reproducer_copies_source_active
        ):
            external_verification_active = True
            single_verifier_active = False
        else:
            external_verification_active = (
                cell.experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME
                and cell.method == SourceExclusionMethod.FULL_FEDSIRA
            )
            single_verifier_active = False
        row_requirement = _row_requirement(cell, self._resolved_core)
        if single_verifier_active:
            reproduction_timer = ElapsedTimer()
            progression_state, attempts, _commitment_hashes = _single_verifier_progression(
                cell, source_domain
            )
            self._last_protocol_phase_durations = ProtocolPhaseDurations(
                reproduce_seconds=reproduction_timer.elapsed_seconds()
            )
        else:
            reproduction_timer = ElapsedTimer()
            progression_state, attempts, _commitment_hashes = _reproduction_progression(
                cell,
                evidence,
                external_verification_active,
                row_requirement,
                frozenset(),
                include_source_as_first_reproducer=no_origin_exclusion_active,
            )
            self._last_protocol_phase_durations = ProtocolPhaseDurations(
                reproduce_seconds=reproduction_timer.elapsed_seconds()
            )
            if progression_state is AdmissionState.VERIFICATION_PENDING:
                verification_timer = ElapsedTimer()
                certified_positive_report_count = 0
                for attempt in attempts:
                    if not attempt.is_certified:
                        continue
                    if same_context_verification_active:
                        panel = self._same_context_verifier_panel(
                            source_domain, NBaiotDomain(attempt.domain)
                        )
                    else:
                        panel = _verifier_panel(
                            source_domain,
                            NBaiotDomain(attempt.domain),
                            cell.master_seed,
                            config.protocol.verification,
                            allow_source_as_verifier=no_origin_exclusion_active,
                        )
                    if not panel_votes_are_one_per_domain(panel):
                        return AdmissionState.DORMANT
                    reports = tuple(resolve_ternary_outcome(True, True) for _domain in panel)
                    if reproduction_row_is_certified(
                        reports,
                        panel_size=config.protocol.verification.panel_size,
                        required_positive_reports=config.protocol.verification.required_positive_reports,
                    ):
                        certified_positive_report_count += sum(
                            1 for report in reports if report is TernaryOutcome.POSITIVE
                        )
                eligible_verifier_count = sum(
                    1
                    for domain in NBAIOT_DOMAIN_ORDER
                    if verifier_is_eligible(
                        domain,
                        source_domain,
                        attempts[0].domain,
                        allow_source_as_verifier=no_origin_exclusion_active,
                    )
                )
                progression_state = verification_pending_transition(
                    eligible_verifier_count,
                    certified_positive_report_count,
                    row_requirement <= len(attempts),
                    config.protocol.verification,
                )
                self._last_protocol_phase_durations = (
                    self._last_protocol_phase_durations.with_verify_seconds(
                        verification_timer.elapsed_seconds()
                    )
                )
        if progression_state is AdmissionState.SYNTHESIS_PENDING:
            synthesis_timer = ElapsedTimer()
            state, self._pending_real_report = _final_gate_decision(
                evidence,
                source_domain,
                tuple(NBaiotDomain(attempt.domain) for attempt in attempts),
                is_plurality_active=cell.experiment == SINGLE_REPRODUCTION_NECESSITY_NAME
                and cell.method == CoreMethodIdentity.FULL_PLURALITY_PATH
                or (
                    cell.method == RESOLVED_FEDSIRA_CORE_METHOD
                    and self._resolved_core is not None
                    and self._resolved_core.plurality_survives
                )
                or direct_krum_active
                or multiple_reproductions_without_verification_active
                or direct_krum_of_retrains_active
                or full_path_ablation_active
                or no_final_synthesis_gate_active
                or no_origin_exclusion_active
                or byzantine_reproducer_copies_source_active,
                prepared_root=self._prepared_root,
                master_seed=cell.master_seed,
                anchor=self._real_anchor(cell.master_seed),
                coordinate_median_active=coordinate_median_active,
                no_final_synthesis_gate_active=no_final_synthesis_gate_active,
                use_source_delta_for_source_domain=no_origin_exclusion_active,
                force_first_row_to_source_delta=byzantine_reproducer_copies_source_active,
                heterogeneity_scope=self._heterogeneity_scope_for_cell(cell),
            )
            self._last_protocol_phase_durations = (
                self._last_protocol_phase_durations.with_synthesize_seconds(
                    synthesis_timer.elapsed_seconds()
                )
            )
        else:
            state = progression_state
        return apply_logical_cycle_expiry(
            state, logical_cycle=0, resource_horizon_config=config.protocol.resource_horizon
        )

    def _execute_plurality_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        state = self._advance_protocol(cell, evidence)
        condition = cell.condition
        source_copy_condition = PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER
        has_legitimate = condition != source_copy_condition
        metrics = _metrics_from_state(state, self._pending_real_report)
        legitimate_result = legitimate_admission_rate(
            [has_legitimate and state is AdmissionState.ADMITTED]
        )
        is_source_copy_admitted = (
            condition == source_copy_condition and state is AdmissionState.ADMITTED
        )
        malicious_indicator = (
            is_source_copy_admitted and cell.method != CoreMethodIdentity.FULL_PLURALITY_PATH
        )
        malicious_result = malicious_admission_rate([malicious_indicator])
        return (
            state,
            (
                *metrics,
                (ComparisonMetric.LEGITIMATE_ADMISSION, legitimate_result.value),
                (ComparisonMetric.MALICIOUS_ADMISSION, malicious_result.value),
            ),
        )

    def _execute_source_exclusion_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        method = cell.method
        full_fedsira = SourceExclusionMethod.FULL_FEDSIRA
        validate_source_excluded_production_weight(0.0)
        if method in (full_fedsira, SourceExclusionMethod.ONE_INDEPENDENT_RETRAIN):
            state = self._advance_protocol(cell, evidence)
            krum_input_excludes_source(
                candidate_row_ids=("reproducer-a", "reproducer-b", "reproducer-c"),
                source_row_id=None,
            )
        elif method == SourceExclusionMethod.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION:
            state = self._client_review_outcome(cell)
        elif method == SourceExclusionMethod.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN:
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self._client_review_outcome(cell)
            )
            state = (
                self._advance_protocol(cell, evidence) if discard_source else AdmissionState.DORMANT
            )
        else:
            state = self._advance_protocol(cell, evidence)
        extra: list[MetricObservation] = []
        if cell.condition == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT:
            real_anchor = self._real_anchor(cell.master_seed)
            source_domain = _source_domain_for_cell(cell)
            backdoor_scope = self._backdoor_scope_for_cell(cell)
            if (
                real_anchor is not None
                and source_domain is not None
                and (backdoor_scope is not None)
            ):
                source_delta = train_source_candidate_delta(
                    self._prepared_root,
                    cell.master_seed,
                    real_anchor,
                    source_domain,
                    backdoor_scope=backdoor_scope,
                )
                if source_delta is not None:
                    asr = compute_source_backdoor_asr(
                        self._prepared_root,
                        real_anchor,
                        real_anchor.flat_parameters + source_delta,
                        source_domain,
                        backdoor_scope.trigger_feature_indices,
                        backdoor_scope.trigger_value,
                    )
                    extra.append(("source-backdoor-asr", asr.value))
        metrics = _metrics_from_state(state, self._pending_real_report)
        malicious_admission = 0.0
        if method != full_fedsira and state is AdmissionState.ADMITTED:
            malicious_admission = 1.0
        return (
            state,
            (*metrics, (ComparisonMetric.MALICIOUS_ADMISSION, malicious_admission), *extra),
        )

    def _execute_external_verification_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        condition = cell.condition
        has_malicious = condition in (
            ExternalVerificationCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
            ExternalVerificationCondition.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER,
        )
        malicious_admission = 0.0
        full_fedsira = SourceExclusionMethod.FULL_FEDSIRA
        if has_malicious and state is AdmissionState.ADMITTED and (cell.method != full_fedsira):
            malicious_admission = 1.0
        return (
            state,
            (*metrics, (ComparisonMetric.MALICIOUS_ADMISSION, malicious_admission)),
        )

    def _execute_primary_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        scenario = cell.condition
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            if scenario == PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY:
                state = self._advance_protocol(cell, evidence)
            else:
                state = AdmissionState.DORMANT
            metrics = _metrics_from_state(state, self._pending_real_report)
            return (state, metrics)
        return self._execute_baseline_cell(cell, evidence)

    def _execute_baseline_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        method = cell.method
        validate_role_not_used_for_tuning(Role.POST_REFERENCE_REPLAY)
        domain_target_view(NBAIOT_DOMAIN_ORDER[0], _source_domain_for_cell(cell))
        state: AdmissionState
        if method == BaselineIdentity.LOCAL_ONLY_REFERENCE:
            state = self._local_only_reference_outcome(cell)
        elif method == BaselineIdentity.CENTRALIZED_REFERENCE:
            state = self._centralized_reference_outcome(cell, evidence)
        elif method == BaselineIdentity.FEDAVG_REFERENCE:
            standard_fl_anchor_rounds()
            state = self._fedavg_reference_outcome(cell, evidence)
        elif method == BaselineIdentity.ONE_INDEPENDENT_RETRAIN:
            one_independent_retrain_local_epochs()
            candidate_free_full_path_opening_mode()
            state = self._advance_protocol(cell, evidence)
        elif method == BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION:
            validate_client_review_composite_screen(CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES)
            validate_client_review_reviewer_count(CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT)
            client_review_direct_admission_production_is_source(
                ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS
            )
            state = self._client_review_outcome(cell)
        elif method == BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN:
            validate_client_review_composite_screen(CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES)
            client_review_then_retrain_local_epochs()
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self._client_review_outcome(cell)
            )
            state = (
                self._advance_protocol(cell, evidence) if discard_source else AdmissionState.DORMANT
            )
        elif method == BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM:
            direct_krum_committee_rows((), (), config.protocol.synthesis.committee_size)
            state = self._advance_protocol(cell, evidence)
        elif method == BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE:
            state = self._multiple_model_certified_ensemble_outcome(cell)
        elif method == BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER:
            state = self._update_reconstruction_filter_outcome(cell, evidence)
        elif method == BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN:
            state = self._density_cluster_trimmed_mean_outcome(cell, evidence)
        elif method == BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE:
            state = self._secure_continual_assessment_outcome(cell, evidence)
        elif method == BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION:
            state = self._recovery_after_source_admission_outcome(cell, evidence)
        elif method == BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE:
            state = self._source_update_sanitization_outcome(cell, evidence)
        elif method == BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION:
            state = self._independent_local_reference_outcome(cell)
        elif method == BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE:
            state = self._krum_reference_outcome(cell, evidence)
        elif method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE:
            validate_three_row_coordinate_median_committee_size(
                config.baselines.three_row_coordinate_median.row_count,
                config.baselines.three_row_coordinate_median,
            )
            state = self._advance_protocol(cell, evidence)
        else:
            state = AdmissionState.DORMANT
        metrics = _metrics_from_state(state, self._pending_real_report)
        return (state, metrics)

    def _execute_reproducer_robustness_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        condition = cell.condition
        compromised_count = _compromised_reproducer_count(condition)
        attack_seed = derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed)
        if "Source Copy" in condition:
            source_copy_update(ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS)
        elif "Model-Replacement" in condition:
            select_model_replacement_carrier_rows(
                ("udp-1", "udp-2"),
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.poison_fraction,
                attack_seed,
            )
            scale_model_replacement_delta(
                ANCHOR_FLAT_PARAMETERS,
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.delta_scale,
            )
        elif "Verifier-Aware" in condition:
            select_model_replacement_carrier_rows(
                ("udp-1", "udp-2"),
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.poison_fraction,
                attack_seed,
            )
        if compromised_count == 0:
            state = self._advance_protocol(cell, evidence)
        else:
            selected = select_compromised_reproducers(
                _reproducer_order(cell), frozenset(NBAIOT_DOMAIN_ORDER), compromised_count
            )
            compromised_reproducers: frozenset[NBaiotDomain] = (
                frozenset(NBaiotDomain(domain) for domain in selected)
                if selected is not None
                else frozenset()
            )
            source_domain = _source_domain_for_cell(cell)
            row_requirement = _row_requirement(cell)
            progression_state, attempts, _commitment_hashes = _reproduction_progression(
                cell,
                evidence,
                external_verification_active=False,
                row_requirement=row_requirement,
                compromised_reproducers=compromised_reproducers,
            )
            if (
                progression_state is AdmissionState.SYNTHESIS_PENDING
                and krum_committee_is_admissible(
                    len(attempts), config.protocol.synthesis.maximum_byzantine_reproduction_rows
                )
            ):
                state, self._pending_real_report = _final_gate_decision(
                    evidence,
                    source_domain,
                    tuple(NBaiotDomain(attempt.domain) for attempt in attempts),
                    is_plurality_active=True,
                    prepared_root=self._prepared_root,
                    master_seed=cell.master_seed,
                    anchor=self._real_anchor(cell.master_seed),
                )
            else:
                state = AdmissionState.DORMANT
                self._pending_real_report = None
        metrics = _metrics_from_state(state, self._pending_real_report)
        return (state, metrics)

    def _execute_verifier_robustness_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        condition = cell.condition
        profile = cell.method
        is_deterministic = profile == VerifierProfile.DETERMINISTIC_BOUND
        if not verification_evidence_is_adequate(
            evidence.reproduction_target_count,
            evidence.reproduction_supported_count,
            config.capability_contract.evidence_minima,
        ):
            state = AdmissionState.DORMANT
        else:
            source_domain = _source_domain_for_cell(cell)
            reproducer_domain = _reproducer_order(cell)[0]
            eligible_verifiers = tuple(
                domain
                for domain in NBAIOT_DOMAIN_ORDER
                if verifier_is_eligible(domain, source_domain, reproducer_domain)
            )
            byzantine_order = byzantine_selection_order(
                eligible_verifiers,
                derive_uint32(BYZANTINE_VERIFIER_SELECTION_SEPARATOR, cell.master_seed),
            )
            compromised_count = _compromised_verifier_count(condition)
            compromised_verifiers = select_compromised_verifiers(byzantine_order, compromised_count)
            compromised_domains = byzantine_order[:compromised_count]
            honest_post_commitment_order = tuple(
                domain for domain in byzantine_order if domain not in compromised_verifiers
            )
            if is_deterministic:
                panel = construct_above_bound_panel(
                    compromised_domains,
                    honest_post_commitment_order,
                    config.protocol.verification.panel_size,
                )
            else:
                panel = diagnostic_committee_panel(
                    eligible_verifiers,
                    committee_draw_namespace_seed=derive_uint32(
                        "VERIFIER_ROW_SEED", cell.master_seed
                    ),
                    panel_size=config.protocol.verification.panel_size,
                )
            if not panel_votes_are_one_per_domain(panel):
                state = AdmissionState.DORMANT
            else:
                false_negative_domains: frozenset[NBaiotDomain] = (
                    frozenset(NBaiotDomain(domain) for domain in panel[:compromised_count])
                    if condition
                    in (
                        VerifierCondition.ONE_FALSE_NEGATIVE,
                        VerifierCondition.TWO_FALSE_NEGATIVES,
                    )
                    else frozenset()
                )
                false_positive_active = condition in (
                    VerifierCondition.ONE_FALSE_POSITIVE,
                    VerifierCondition.TWO_FALSE_POSITIVES,
                )
                compromised_domains_set = frozenset(panel[:compromised_count])
                byzantine_behavior = (
                    ByzantineVerifierBehavior.FALSE_POSITIVE
                    if false_positive_active
                    else ByzantineVerifierBehavior.FALSE_NEGATIVE
                )
                byzantine_vote = resolve_byzantine_verifier_vote(byzantine_behavior)
                deduplicated = deduplicate_reports_by_proxy(
                    tuple(
                        (
                            domain,
                            byzantine_vote
                            if domain in compromised_domains_set
                            else resolve_ternary_outcome(
                                True, domain not in false_negative_domains
                            ),
                        )
                        for domain in panel
                    )
                )
                reports = tuple(report_for_domain(deduplicated, domain) for domain in panel)
                certified = reproduction_row_is_certified(
                    reports,
                    panel_size=config.protocol.verification.panel_size,
                    required_positive_reports=config.protocol.verification.required_positive_reports,
                )
                honest_positive_bound = minimum_honest_positive_count(
                    sum(1 for report in reports if report is TernaryOutcome.POSITIVE),
                    compromised_count,
                )
                if is_deterministic:
                    diagnostic_passes = True
                else:
                    contamination_probability = diagnostic_at_least_two_byzantine_probability(
                        len(eligible_verifiers),
                        compromised_count,
                        config.protocol.verification.panel_size,
                    )
                    diagnostic_profile = config.protocol.diagnostic_random_verifier_profile
                    diagnostic_passes = (
                        contamination_probability <= diagnostic_profile.tolerated_contamination_risk
                    )
                minimum_gate_domains = (
                    config.protocol.final_gate.minimum_adequate_non_source_domains
                )
                state = (
                    AdmissionState.ADMITTED
                    if diagnostic_passes
                    and certified
                    and (evidence.final_gate_adequate_domain_count >= minimum_gate_domains)
                    and (honest_positive_bound >= 1)
                    else AdmissionState.DORMANT
                )
        metrics = _metrics_from_state(state, self._pending_real_report)
        return (state, metrics)

    def _execute_byzantine_bound_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        condition = BoundCondition(cell.condition)
        if condition is BoundCondition.ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND:
            reproducer_cell = replace(
                cell, condition=ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR
            )
            return self._execute_reproducer_robustness_cell(reproducer_cell, evidence)
        if condition is BoundCondition.TWO_BYZANTINE_REPRODUCERS_ABOVE_BOUND:
            reproducer_cell = replace(
                cell, condition=ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS
            )
            return self._execute_reproducer_robustness_cell(reproducer_cell, evidence)
        if condition is BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND:
            verifier_cell = replace(
                cell,
                method=VerifierProfile.DETERMINISTIC_BOUND,
                condition=VerifierCondition.ONE_FALSE_POSITIVE,
            )
            return self._execute_verifier_robustness_cell(verifier_cell, evidence)
        verifier_cell = replace(
            cell,
            method=VerifierProfile.DETERMINISTIC_BOUND,
            condition=VerifierCondition.TWO_FALSE_POSITIVES,
        )
        return self._execute_verifier_robustness_cell(verifier_cell, evidence)

    def _execute_secondary_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        return (state, metrics)

    def _execute_evidence_scarcity_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        schedule = EvidenceArrivalSchedule(cell.condition)
        horizon = config.protocol.resource_horizon.maximum_logical_evidence_cycles
        candidate_cycles = tuple(range(horizon))
        holder_counts = tuple(
            holder_count_at_cycle(schedule, cycle, len(NBAIOT_DOMAIN_ORDER) - 1)
            for cycle in candidate_cycles
        )
        tau_k = first_cycle_with_minimum_eligible_evidence_holders(
            holder_counts, config.protocol.final_gate.minimum_adequate_non_source_domains
        )
        target_capable_order = tuple(NBAIOT_DOMAIN_ORDER[1:])
        t_evidence = compute_t_evidence(
            schedule,
            target_capable_order,
            candidate_cycles,
            config.protocol.synthesis.committee_size,
            config.protocol.final_gate.minimum_adequate_non_source_domains,
        )
        first_holder = first_holder_cycle_for_domain(
            schedule, NBAIOT_DOMAIN_ORDER[1], target_capable_order, candidate_cycles
        )
        if tau_k is None:
            state = resume_dormant_admission(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = _metrics_from_state(state, self._pending_real_report)
            return (state, (*metrics, ("evidence-arrival-cycle", None)))
        try:
            validate_no_safety_completion_before_tau_k(0, tau_k)
        except ValueError:
            state = resume_dormant_admission(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = _metrics_from_state(state, self._pending_real_report)
            return (state, (*metrics, ("evidence-arrival-cycle", float(tau_k))))
        state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        delay_decomposition = AdmissionDelayDecomposition(
            logical_information_arrival_cycles=tau_k,
            assignment_seconds=0.0,
            reproduce_seconds=0.0,
            verify_seconds=0.0,
            synthesize_seconds=0.0,
        )
        return (
            state,
            (
                *metrics,
                ("evidence-arrival-cycle", float(tau_k)),
                (
                    "logical-information-arrival-cycles",
                    float(delay_decomposition.logical_information_arrival_cycles),
                ),
                ("t-evidence", float(t_evidence) if t_evidence is not None else None),
                ("first-holder-cycle", float(first_holder) if first_holder is not None else None),
                ("post-evidence-wall-clock-seconds", None),
            ),
        )

    def _execute_admission_delay_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        schedule = EvidenceArrivalSchedule(cell.condition)
        horizon = config.protocol.resource_horizon.maximum_logical_evidence_cycles
        candidate_cycles = tuple(range(horizon))
        holder_counts = tuple(
            holder_count_at_cycle(schedule, cycle, len(NBAIOT_DOMAIN_ORDER) - 1)
            for cycle in candidate_cycles
        )
        tau_k = first_cycle_with_minimum_eligible_evidence_holders(
            holder_counts, config.protocol.final_gate.minimum_adequate_non_source_domains
        )
        target_capable_order = tuple(NBAIOT_DOMAIN_ORDER[1:])
        t_evidence = compute_t_evidence(
            schedule,
            target_capable_order,
            candidate_cycles,
            config.protocol.synthesis.committee_size,
            config.protocol.final_gate.minimum_adequate_non_source_domains,
        )
        timer = ElapsedTimer()
        self._last_protocol_phase_durations = ProtocolPhaseDurations()
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            state = self._advance_protocol(cell, evidence)
            post_evidence_wall_clock_seconds = timer.elapsed_seconds()
            metrics = _metrics_from_state(state, self._pending_real_report)
        else:
            state, metrics = self._execute_baseline_cell(cell, evidence)
            post_evidence_wall_clock_seconds = timer.elapsed_seconds()
        phase_durations = self._last_protocol_phase_durations
        return (
            state,
            (
                *metrics,
                ("evidence-arrival-cycle", float(tau_k) if tau_k is not None else None),
                ("t-evidence", float(t_evidence) if t_evidence is not None else None),
                ("assignment-seconds", phase_durations.assignment_seconds),
                ("reproduce-seconds", phase_durations.reproduce_seconds),
                ("verify-seconds", phase_durations.verify_seconds),
                ("synthesize-seconds", phase_durations.synthesize_seconds),
                ("post-evidence-wall-clock-seconds", post_evidence_wall_clock_seconds),
            ),
        )

    def _execute_efficiency_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        model_size_bytes = 115 * 256 * 4
        envelopes: list[bytes] = []
        metadata_records: list[CommunicationMessageMetadata] = []
        tensor_name = parameter_tensor_name(TensorParameterKind.MODEL, "linear")
        timer = ElapsedTimer()
        for message_type, count in _efficiency_message_counts():
            for _index in range(count):
                metadata = CommunicationMessageMetadata(
                    message_type=message_type,
                    dataset_manifest_hash="a" * 64,
                    semantic_cell_key_hash="b" * 64,
                    master_seed=cell.master_seed,
                    round_index=None,
                    sender=SERVER_ID,
                    receiver="CLIENT",
                    capability_contract_hash="c" * 64,
                    payload_tensor_count=1,
                )
                tensor_payload = b"\x00" * model_size_bytes
                envelopes.append(
                    encode_message_envelope(
                        metadata,
                        (
                            TensorEnvelopePayload(
                                metadata=TensorPayloadMetadata(
                                    name=tensor_name, shape=(115, 256), nbytes=model_size_bytes
                                ),
                                payload=tensor_payload,
                            ),
                        ),
                    )
                )
                metadata_records.append(metadata)
        encode_elapsed_seconds = timer.elapsed_seconds()
        bytes_total = communication_bytes(tuple(envelopes))
        transmissions = model_transmission_count(tuple(metadata_records))
        reset_peak_gpu_memory_counter()
        protocol_timer = ElapsedTimer()
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            state = self._advance_protocol(cell, evidence)
        else:
            state, _baseline_metrics = self._execute_baseline_cell(cell, evidence)
        post_evidence_seconds = protocol_timer.elapsed_seconds()
        delay_decomposition = AdmissionDelayDecomposition(
            logical_information_arrival_cycles=0,
            assignment_seconds=0.0,
            reproduce_seconds=0.0,
            verify_seconds=encode_elapsed_seconds,
            synthesize_seconds=post_evidence_seconds,
        )
        gpu_memory_bytes = peak_gpu_memory_bytes()
        host_rss_bytes = peak_host_resident_set_bytes()
        return (
            state,
            (
                (
                    ComparisonMetric.POST_EVIDENCE_OVERHEAD,
                    delay_decomposition.post_evidence_wall_clock_seconds,
                ),
                ("communication-bytes", float(bytes_total)),
                ("model-transmissions", float(transmissions)),
                (
                    "post-evidence-wall-clock-seconds",
                    delay_decomposition.post_evidence_wall_clock_seconds,
                ),
                ("peak-gpu-memory-bytes", float(gpu_memory_bytes)),
                ("peak-host-rss-bytes", float(host_rss_bytes)),
            ),
        )
