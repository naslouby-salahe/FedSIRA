from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import replace
from pathlib import Path
from typing import Protocol, cast

import torch

from fedsira.artifacts.paths import experiment_repetition_telemetry_root, prepared_evidence_root
from fedsira.datasets.ciciot2023.schema import TARGET_LABEL as CICIOT2023_TARGET_LABEL
from fedsira.datasets.common import (
    BackdoorScope,
    DatasetAdapter,
    EpistemicFailureScope,
    HeterogeneityScope,
    RealAnchor,
    Role,
    RootCauseScope,
    apply_quantity_skew_to_cap,
    dataset_manifest_hash,
    dataset_specification,
    exclude_source_from_quantity_skew,
    feature_shift_sign,
    prepared_feature_names,
    quantity_skew_multiplier_by_domain,
    quantity_skew_multiplier_for_domain,
    role_hash_token,
    select_heterogeneity_shift_features,
    target_row_ids_for_contract,
    validate_excluded_root_cause_not_supported,
)
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotDomain,
    nbaiot_adapter,
)
from fedsira.domain.enums import (
    AdmissionOpeningMode,
    AdmissionState,
    ByzantineVerifierBehavior,
    CapabilityContractScope,
    CoreMethodIdentity,
    DatasetId,
    DormantOrigin,
    ExperimentLifecycleState,
    FailureClass,
    ScientificCellPhase,
    TernaryOutcome,
)
from fedsira.domain.models import (
    SERVER_ID,
    AdmissionDelayDecomposition,
    CommunicationMessageMetadata,
    CommunicationMessageType,
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
    BooleanValue,
    ByzantineDomainCount,
    CellHandlerName,
    CommunicationMessageCount,
    CompromisedReproducerCount,
    ConditionName,
    DomainId,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MetricObservation,
    MetricValue,
    RequiredReproductionRowCount,
)
from fedsira.evaluation.comparisons import (
    ComparisonMetric,
)
from fedsira.evaluation.metrics import (
    RealReportSummary,
    boundary_metric_set,
    clean_proposal_oracle_label,
    compute_screen_differential,
    compute_source_backdoor_asr,
    evaluate_domain,
    evaluate_screen_domain,
    false_launch_rate,
    malicious_admission_rate,
    metrics_from_state,
    non_source_domains,
    reproduction_attempt_count,
    root_cause_partitioned_row_ids,
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.evaluation.service import (
    SingleProcessTimingWorker,
    TimingRepetitionObservation,
    TimingWorkerResult,
    compute_capability_under_specification_summary,
    compute_shared_epistemic_failure_summary,
)
from fedsira.experiments.collapse import ResolvedCore
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BASELINE_IMPLEMENTATION_VALIDATION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    PROTOCOL_INVARIANT_VALIDATION_NAME,
    REGISTERED_EXPERIMENT_NAMES,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    AblationVariant,
    BoundCondition,
    DescriptiveScientificMetric,
    EpistemicFailureType,
    EvidenceArrivalSchedule,
    ExternalVerificationCondition,
    HeterogeneityRegime,
    OpeningMode,
    PluralityCondition,
    ProposalEpisode,
    ReproducerCondition,
    SecondaryScenario,
    SourceExclusionMethod,
    VerifierCondition,
    VerifierProfile,
    experiment_by_name,
)
from fedsira.experiments.engine import (
    AdmissionStateObservation,
    CellExecutionOutcome,
    CellExecutor,
    PreparedEvidenceCounts,
    ProtocolPhaseDurations,
    load_prepared_evidence_counts,
)
from fedsira.experiments.execution import (
    run_data_and_domain_evidence_validation,
    run_protocol_invariant_validation,
)
from fedsira.experiments.planning import (
    ScientificCell,
)
from fedsira.learning.federated import train_anchor
from fedsira.learning.post_reference import (
    certified_domain_delta_committee,
    train_domain_reproduction_delta,
    train_generic_hard_supported_examples_delta,
    train_source_candidate_delta,
)
from fedsira.protocol.admission import (
    final_gate_decision,
)
from fedsira.protocol.attacks import (
    resolve_byzantine_verifier_vote,
    scale_model_replacement_delta,
    select_model_replacement_carrier_rows,
    source_copy_update,
)
from fedsira.protocol.baselines.defenses import (
    CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES,
    CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
    DomainFeatureMean,
    client_review_direct_admission_production_is_source,
    client_review_then_retrain_local_epochs,
    client_review_then_retrain_should_discard_source_weights,
    direct_krum_committee_rows,
    parameter_similarity_certification_row_results,
    same_context_verifier_panel,
    validate_client_review_composite_screen,
    validate_client_review_reviewer_count,
    validate_group_without_target_member_uses_supported_only,
    validate_three_row_coordinate_median_committee_size,
)
from fedsira.protocol.baselines.outcomes import ProtocolBaselineOutcomes
from fedsira.protocol.baselines.registry import (
    ORDINARY_POST_REFERENCE_DATA_ACCESS,
    BaselineIdentity,
    domain_target_view,
    domain_without_target_view_may_participate,
    first_eligible_non_source_reproducer,
    single_fresh_verifier_domain,
    single_fresh_verifier_outcome,
    standard_fl_anchor_rounds,
    validate_role_not_used_for_tuning,
)
from fedsira.protocol.baselines.training import (
    candidate_free_full_path_opening_mode,
    one_independent_retrain_local_epochs,
    validate_candidate_free_full_path_opening_mode,
)
from fedsira.protocol.capability_contract import (
    build_capability_contract,
    capability_contract_for_digest,
    capability_contract_passes,
    compute_capability_identity,
    reproduction_evidence_is_adequate,
    validate_source_excluded_production_weight,
    verification_evidence_is_adequate,
)
from fedsira.protocol.proposal import (
    ScreenDomainResult,
    candidate_screen_transition,
    first_target_sample_id,
    opening_identity,
    screen_domain_order,
    screen_fold_index,
    source_domain_for_cell,
    start_admission,
    supported_role_count,
    target_role_count,
)
from fedsira.protocol.reproduction import (
    ReproductionAttempt,
    commitment_digest,
    consumed_domains,
    handle_adequate_domain_trained,
    handle_inadequate_domain,
    handle_no_adequate_unconsumed_domain,
    next_reproducer_domain,
    select_compromised_reproducers,
    validate_commitment_exists_before_verifier_assignment,
    validate_reproduction_start_checkpoint,
    validate_reproduction_starts_from_anchor,
)
from fedsira.protocol.rules import (
    apply_logical_cycle_expiry,
    compute_t_evidence,
    deduplicate_reports_by_proxy,
    diagnostic_at_least_two_byzantine_probability,
    first_cycle_with_minimum_eligible_evidence_holders,
    first_holder_cycle_for_domain,
    holder_count_at_cycle,
    krum_committee_is_admissible,
    minimum_honest_positive_count,
    report_for_domain,
    reproducer_order_for_cell,
    reproduction_update_vector,
    resolve_ternary_outcome,
    resume_dormant_admission,
    validate_no_safety_completion_before_tau_k,
)
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    krum_input_excludes_source,
)
from fedsira.protocol.verification import (
    byzantine_selection_order,
    construct_above_bound_panel,
    diagnostic_committee_panel,
    honest_verifier_report,
    panel_votes_are_one_per_domain,
    reproduction_row_is_certified,
    select_compromised_verifiers,
    verification_pending_transition,
    verifier_is_eligible,
    verifier_panel,
)
from fedsira.runtime import (
    REPOSITORY_ROOT,
    ElapsedTimer,
    FailureDetail,
    current_application_context,
    derive_uint32,
)


class ProtocolCellDispatch:
    _primary_adapter: DatasetAdapter
    _prepared_root: Path
    _secondary_prepared_root: Path
    _resolved_core: ResolvedCore | None
    _pending_real_report: RealReportSummary | None
    _last_protocol_phase_durations: ProtocolPhaseDurations

    def real_anchor(self, master_seed: MasterSeed) -> RealAnchor | None: ...

    def backdoor_scope_for_cell(self, cell: ScientificCell) -> BackdoorScope | None: ...

    def heterogeneity_scope_for_cell(self, cell: ScientificCell) -> HeterogeneityScope | None: ...

    def _same_context_verifier_panel(
        self,
        source_domain: DomainId | None,
        reproducer_domain: DomainId,
    ) -> tuple[DomainId, ...]: ...

    def _scoped_capability_contract_passes(
        self,
        real_anchor: RealAnchor,
        source_domain: DomainId,
        candidate_flat_parameters: torch.Tensor,
        root_cause_scope: RootCauseScope,
    ) -> BooleanValue: ...

    def client_review_outcome(self, cell: ScientificCell) -> AdmissionState: ...

    def _centralized_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

    def _local_only_reference_outcome(self, cell: ScientificCell) -> AdmissionState: ...

    def _fedavg_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

    def _krum_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

    def _density_cluster_trimmed_mean_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

    def _update_reconstruction_filter_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

    def _source_update_sanitization_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

    def _recovery_after_source_admission_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

    def _secure_continual_assessment_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

    def _independent_local_reference_outcome(self, cell: ScientificCell) -> AdmissionState: ...

    def _multiple_model_certified_ensemble_outcome(
        self, cell: ScientificCell
    ) -> AdmissionState: ...

    def _source_release_after_full_external_check_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> AdmissionState: ...

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
            state = self.client_review_outcome(cell)
            return (
                state,
                metrics_from_state(
                    state, self._pending_real_report, legitimate_admission_eligible=True
                ),
            )
        if variant == AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK:
            state = self._source_release_after_full_external_check_outcome(cell, evidence)
            return (
                state,
                metrics_from_state(
                    state, self._pending_real_report, legitimate_admission_eligible=True
                ),
            )
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
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
        extra: list[MetricObservation] = []
        if variant == AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION:
            domain_without_target_view_may_participate(True)
            real_anchor = self.real_anchor(cell.master_seed)
            if real_anchor is not None:
                candidate_domains = non_source_domains(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    source_domain_for_cell(self._primary_adapter, cell),
                )[: config.baselines.parameter_similarity.required_committed_rows]
                committee_deltas = certified_domain_delta_committee(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    candidate_domains,
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
                row_requirement(cell, self._resolved_core),
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
            real_anchor = self.real_anchor(cell.master_seed)
            source_domain = source_domain_for_cell(self._primary_adapter, cell)
            real_feature_names = (
                prepared_feature_names(self._primary_adapter.prepared_root)
                if real_anchor is not None
                else None
            )
            if (
                real_anchor is not None
                and source_domain is not None
                and (real_feature_names is not None)
            ):
                candidate_domains = non_source_domains(
                    nbaiot_adapter(self._primary_adapter.prepared_root), source_domain
                )[: config.protocol.synthesis.committee_size]
                committee_deltas = certified_domain_delta_committee(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    candidate_domains,
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
                        ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
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
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
        is_scoped_contract = cell.method != CapabilityContractScope.BROAD_TARGET_ONLY
        boundary_metrics = boundary_metric_set(
            true_labels=(),
            predicted_labels=(),
            class_tokens=(
                self._primary_adapter.benign_class_token,
                self._primary_adapter.target_class_token,
            ),
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
            (ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE, false_same_rate.value),
        ]
        if cell.experiment == CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME:
            scope = CapabilityContractScope(cell.method)
            real_anchor = self.real_anchor(cell.master_seed)
            real_feature_names = (
                prepared_feature_names(self._primary_adapter.prepared_root)
                if real_anchor is not None
                else None
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
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    source_domain_for_cell(self._primary_adapter, cell),
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
                extra.append(
                    (
                        "root-cause-a-target-f1",
                        capability_summary.root_cause_a_target_f1.value,
                    )
                )
                extra.append(
                    (
                        "root-cause-b-target-f1",
                        capability_summary.root_cause_b_target_f1.value,
                    )
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
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    non_source_domains(
                        nbaiot_adapter(self._primary_adapter.prepared_root),
                        source_domain_for_cell(self._primary_adapter, cell),
                    ),
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
            real_anchor = self.real_anchor(cell.master_seed)
            real_feature_names = (
                prepared_feature_names(self._primary_adapter.prepared_root)
                if real_anchor is not None
                else None
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
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    source_domain_for_cell(self._primary_adapter, cell),
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
                    self._primary_adapter,
                    heterogeneity_seed,
                    config.attacks_and_boundaries.heterogeneity.quantity_skew_multipliers,
                )
                source_domain = source_domain_for_cell(self._primary_adapter, cell)
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
                heterogeneity_scope = self.heterogeneity_scope_for_cell(cell)
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
        opening_mode = opening_mode_for_cell(cell)
        entry = start_admission(opening_mode)
        if entry.direct_production_weight != 0.0:
            raise ValueError("source direct production weight must be 0.0")
        episode = cell.condition
        episode_is_legitimate = episode in (
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        )
        source_domain = source_domain_for_cell(self._primary_adapter, cell)
        real_anchor = self.real_anchor(cell.master_seed)
        resolved_opening_identity = (
            opening_identity(self._primary_adapter, real_anchor.dataset_manifest_hash)
            if real_anchor is not None
            else None
        )
        if (
            real_anchor is not None
            and source_domain is not None
            and opening_mode is AdmissionOpeningMode.PROPOSAL_ASSISTED
        ):
            if episode == ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES:
                real_source_delta = train_generic_hard_supported_examples_delta(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    source_domain,
                )
            else:
                real_source_delta = train_source_candidate_delta(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    source_domain,
                    backdoor_scope=self.backdoor_scope_for_cell(cell),
                )
        else:
            real_source_delta = None
        if real_anchor is None or source_domain is None:
            state = AdmissionState.DORMANT
            screen_results: tuple[ScreenDomainResult, ...] = ()
            real_differential_a: float | None = None
        else:
            non_source = tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain)
            screen_order = screen_domain_order(
                non_source,
                screen_domain_order_namespace_seed=derive_uint32(
                    "SCREEN_DOMAIN_ORDER_SEED", cell.master_seed
                ),
                screen_domain_count=config.protocol.admission_opening.screen_domains,
            )
            screen_results = tuple(
                evaluate_screen_domain(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    real_source_delta,
                    NBaiotDomain(domain),
                    opening_mode,
                    screen_predicate_variant,
                )
                for domain in screen_order
            )
            real_differential_a = (
                compute_screen_differential(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    real_source_delta,
                    NBaiotDomain(screen_order[0]),
                )
                if real_source_delta is not None and screen_order
                else None
            )
            state = candidate_screen_transition(
                opening_mode, screen_results, config.protocol.admission_opening
            )
        if state is AdmissionState.ADMISSION_OPEN:
            state = self._advance_protocol(cell, evidence)
        metrics = metrics_from_state(
            state,
            self._pending_real_report,
            legitimate_admission_eligible=episode_is_legitimate,
        )
        false_launch_result = false_launch_rate(
            false_launch_count=1
            if state is AdmissionState.ADMITTED and (not episode_is_legitimate)
            else 0,
            adequate_defined_oracle_count=1 if screen_results else 0,
        )
        trained_domains = frozenset(
            result.domain for result in screen_results if result.meets_opening_predicate
        )
        attempts = reproduction_attempt_count(
            domains_with_training_start=trained_domains
            if state is AdmissionState.ADMITTED
            else frozenset(),
            evidence_inadequate_domains=frozenset(
                result.domain for result in screen_results if not result.is_evidence_adequate
            ),
        )
        screen_fold_seed = derive_uint32("SCREEN_FOLD_SEED", cell.master_seed)
        fold_sample_id = (
            first_target_sample_id(
                self._primary_adapter, NBaiotDomain(screen_results[0].domain), Role.CANDIDATE_SCREEN
            )
            if screen_results
            else None
        )
        screen_fold_for_target = (
            screen_fold_index(
                fold_sample_id, screen_fold_seed, config.protocol.proposal_screen.fold_count
            )
            if fold_sample_id is not None
            else None
        )
        return (
            state,
            (
                *metrics,
                (
                    "capability-contract-passes",
                    1.0
                    if resolved_opening_identity is not None and state is AdmissionState.ADMITTED
                    else 0.0,
                ),
                (
                    "screen-fold-index",
                    float(screen_fold_for_target) if screen_fold_for_target is not None else None,
                ),
                ("screen-differential-a", real_differential_a),
                (ComparisonMetric.FALSE_LAUNCH, false_launch_result.value),
                (ComparisonMetric.REPRODUCTION_ATTEMPTS, float(attempts)),
                (
                    ComparisonMetric.POST_EVIDENCE_OVERHEAD,
                    self._last_protocol_phase_durations.reproduce_seconds
                    + self._last_protocol_phase_durations.verify_seconds
                    + self._last_protocol_phase_durations.synthesize_seconds
                    + self._last_protocol_phase_durations.assignment_seconds,
                ),
                (
                    ComparisonMetric.MALICIOUS_ADMISSION,
                    malicious_admission_rate(
                        [
                            state is AdmissionState.ADMITTED
                            and episode is ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT
                        ]
                    ).value
                    if episode is ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT
                    else None,
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
        real_anchor = self.real_anchor(cell.master_seed)
        if real_anchor is None:
            return AdmissionState.DORMANT
        source_domain = source_domain_for_cell(self._primary_adapter, cell)
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
        full_reference_ablation_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.FULL_FEDSIRA
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
            or full_reference_ablation_active
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
        required_row_count = row_requirement(cell, self._resolved_core)
        source_delta = (
            train_source_candidate_delta(
                nbaiot_adapter(self._primary_adapter.prepared_root),
                cell.master_seed,
                real_anchor,
                source_domain,
                backdoor_scope=self.backdoor_scope_for_cell(cell),
            )
            if source_domain is not None
            and (
                no_origin_exclusion_active
                or byzantine_reproducer_copies_source_active
                or self.backdoor_scope_for_cell(cell) is not None
            )
            else None
        )
        heterogeneity_scope = self.heterogeneity_scope_for_cell(cell)
        backdoor_scope = self.backdoor_scope_for_cell(cell)
        if single_verifier_active:
            reproduction_timer = ElapsedTimer()
            progression_state, attempts, commitment_hashes, updates = single_verifier_progression(
                cell,
                source_domain,
                self._primary_adapter,
                real_anchor,
                heterogeneity_scope,
            )
            self._last_protocol_phase_durations = ProtocolPhaseDurations(
                reproduce_seconds=reproduction_timer.elapsed_seconds()
            )
        else:
            reproduction_timer = ElapsedTimer()
            progression_state, attempts, commitment_hashes, updates = reproduction_progression(
                cell,
                evidence,
                external_verification_active,
                required_row_count,
                frozenset(),
                self._primary_adapter,
                real_anchor,
                include_source_as_first_reproducer=no_origin_exclusion_active,
                heterogeneity_scope=heterogeneity_scope,
                backdoor_scope=backdoor_scope,
                source_delta=source_delta,
            )
            self._last_protocol_phase_durations = ProtocolPhaseDurations(
                reproduce_seconds=reproduction_timer.elapsed_seconds()
            )
            if progression_state is AdmissionState.VERIFICATION_PENDING:
                verification_timer = ElapsedTimer()
                certified_positive_report_count = 0
                certified_attempts = 0
                for attempt, commitment_hash in zip(attempts, commitment_hashes, strict=False):
                    if not attempt.was_trained:
                        continue
                    attempt_domain = NBaiotDomain(attempt.domain)
                    if attempt_domain not in updates:
                        continue
                    candidate_flat = real_anchor.flat_parameters + updates[attempt_domain]
                    if same_context_verification_active:
                        panel = self._same_context_verifier_panel(source_domain, attempt_domain)
                    else:
                        panel = verifier_panel(
                            self._primary_adapter,
                            source_domain,
                            attempt_domain,
                            cell.master_seed,
                            config.protocol.verification,
                            commitment_hash,
                            allow_source_as_verifier=no_origin_exclusion_active,
                        )
                    if not panel_votes_are_one_per_domain(panel):
                        return AdmissionState.DORMANT
                    reports = tuple(
                        honest_verifier_report(
                            self._primary_adapter,
                            real_anchor,
                            candidate_flat,
                            NBaiotDomain(verifier_domain),
                            heterogeneity_scope,
                        )
                        for verifier_domain in panel
                    )
                    if reproduction_row_is_certified(
                        reports,
                        panel_size=config.protocol.verification.panel_size,
                        required_positive_reports=config.protocol.verification.required_positive_reports,
                    ):
                        certified_attempts += 1
                        certified_positive_report_count += sum(
                            1 for report in reports if report is TernaryOutcome.POSITIVE
                        )
                eligible_verifier_count = sum(
                    1
                    for domain in self._primary_adapter.domain_ids
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
                    certified_attempts >= required_row_count,
                    config.protocol.verification,
                )
                self._last_protocol_phase_durations = (
                    self._last_protocol_phase_durations.with_verify_seconds(
                        verification_timer.elapsed_seconds()
                    )
                )
        if progression_state is AdmissionState.SYNTHESIS_PENDING:
            synthesis_timer = ElapsedTimer()
            state, self._pending_real_report = final_gate_decision(
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
                adapter=self._primary_adapter,
                master_seed=cell.master_seed,
                anchor=real_anchor,
                coordinate_median_active=coordinate_median_active,
                no_final_synthesis_gate_active=no_final_synthesis_gate_active,
                use_source_delta_for_source_domain=no_origin_exclusion_active,
                force_first_row_to_source_delta=byzantine_reproducer_copies_source_active,
                heterogeneity_scope=heterogeneity_scope,
                precomputed_updates=updates,
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
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
        malicious_value: MetricValue | None = (
            malicious_admission_rate(
                [
                    state is AdmissionState.ADMITTED
                    and cell.method != CoreMethodIdentity.FULL_PLURALITY_PATH
                ]
            ).value
            if condition is source_copy_condition
            else None
        )
        return (
            state,
            (*metrics, (ComparisonMetric.MALICIOUS_ADMISSION, malicious_value)),
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
                candidate_row_ids=tuple(domain.name for domain in NBAIOT_DOMAIN_ORDER[:3]),
                source_row_id=None,
            )
        elif method == SourceExclusionMethod.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION:
            state = self.client_review_outcome(cell)
        elif method == SourceExclusionMethod.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN:
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self.client_review_outcome(cell)
            )
            state = (
                self._advance_protocol(cell, evidence) if discard_source else AdmissionState.DORMANT
            )
        else:
            state = self._advance_protocol(cell, evidence)
        extra: list[MetricObservation] = []
        source_backdoor_asr: MetricResult | None = None
        if cell.condition == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT:
            real_anchor = self.real_anchor(cell.master_seed)
            source_domain = source_domain_for_cell(self._primary_adapter, cell)
            backdoor_scope = self.backdoor_scope_for_cell(cell)
            if (
                real_anchor is not None
                and source_domain is not None
                and (backdoor_scope is not None)
            ):
                source_delta = train_source_candidate_delta(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    source_domain,
                    backdoor_scope=backdoor_scope,
                )
                if source_delta is not None:
                    asr = compute_source_backdoor_asr(
                        nbaiot_adapter(self._primary_adapter.prepared_root),
                        real_anchor,
                        real_anchor.flat_parameters + source_delta,
                        source_domain,
                        backdoor_scope.trigger_feature_indices,
                        backdoor_scope.trigger_value,
                    )
                    source_backdoor_asr = asr
        metrics = metrics_from_state(
            state,
            self._pending_real_report,
            source_backdoor_asr,
            legitimate_admission_eligible=True,
        )
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
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
        condition = cell.condition
        has_malicious = condition in (
            ExternalVerificationCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
            ExternalVerificationCondition.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER,
        )
        malicious_admission: MetricValue | None = (
            1.0
            if has_malicious
            and state is AdmissionState.ADMITTED
            and cell.method != SourceExclusionMethod.FULL_FEDSIRA
            else 0.0
            if has_malicious
            else None
        )
        return (
            state,
            (*metrics, (ComparisonMetric.MALICIOUS_ADMISSION, malicious_admission)),
        )

    def _execute_primary_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            state = self._advance_protocol(cell, evidence)
            metrics = metrics_from_state(
                state, self._pending_real_report, legitimate_admission_eligible=True
            )
            return (state, metrics)
        return self._execute_baseline_cell(cell, evidence)

    def _execute_baseline_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        method = cell.method
        validate_role_not_used_for_tuning(Role.POST_REFERENCE_REPLAY)
        domain_target_view(
            NBAIOT_DOMAIN_ORDER[0],
            source_domain_for_cell(self._primary_adapter, cell),
            ORDINARY_POST_REFERENCE_DATA_ACCESS,
        )
        state: AdmissionState
        if method == BaselineIdentity.LOCAL_ONLY_REFERENCE:
            state = self._local_only_reference_outcome(cell)
        elif method == BaselineIdentity.CENTRALIZED_REFERENCE:
            state = self._centralized_reference_outcome(cell, evidence)
        elif method == BaselineIdentity.FEDAVG_REFERENCE:
            standard_fl_anchor_rounds()
            state = self._fedavg_reference_outcome(cell, evidence)
        elif method == BaselineIdentity.CANDIDATE_FREE_FULL_PATH:
            validate_candidate_free_full_path_opening_mode(candidate_free_full_path_opening_mode())
            state = self._advance_protocol(cell, evidence)
        elif method == BaselineIdentity.ONE_INDEPENDENT_RETRAIN:
            one_independent_retrain_local_epochs()
            validate_candidate_free_full_path_opening_mode(candidate_free_full_path_opening_mode())
            state = self._advance_protocol(cell, evidence)
        elif method == BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION:
            validate_client_review_composite_screen(CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES)
            validate_client_review_reviewer_count(CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT)
            real_anchor = self.real_anchor(cell.master_seed)
            source_domain = source_domain_for_cell(self._primary_adapter, cell)
            source_delta = (
                train_source_candidate_delta(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    source_domain,
                )
                if real_anchor is not None and source_domain is not None
                else None
            )
            if real_anchor is not None and source_delta is not None:
                client_review_direct_admission_production_is_source(source_delta, source_delta)
            state = self.client_review_outcome(cell)
        elif method == BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN:
            validate_client_review_composite_screen(CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES)
            client_review_then_retrain_local_epochs()
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self.client_review_outcome(cell)
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
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
        return (state, metrics)

    def _execute_reproducer_robustness_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        condition = cell.condition
        compromised_count = compromised_reproducer_count(condition)
        attack_seed = derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed)
        real_anchor = self.real_anchor(cell.master_seed)
        source_domain = source_domain_for_cell(self._primary_adapter, cell)
        carrier_rows = (
            nbaiot_adapter(self._primary_adapter.prepared_root).load_rows(
                source_domain,
                self._primary_adapter.attack_carrier_class_token(),
                Role.POST_REFERENCE_REPLAY,
            )
            if source_domain is not None
            else None
        )
        carrier_ids = carrier_rows.sample_ids if carrier_rows is not None else ()
        if condition in (
            ReproducerCondition.ONE_SOURCE_COPY,
            ReproducerCondition.TWO_SOURCE_COPIES,
        ):
            source_delta = (
                train_source_candidate_delta(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    source_domain,
                )
                if real_anchor is not None and source_domain is not None
                else None
            )
            if real_anchor is not None and source_delta is not None:
                source_copy_update(
                    real_anchor.flat_parameters + source_delta, real_anchor.flat_parameters
                )
        elif condition in (
            ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
            ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
            ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
            ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
        ):
            select_model_replacement_carrier_rows(
                carrier_ids,
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.poison_fraction,
                attack_seed,
            )
        if compromised_count == 0:
            state = self._advance_protocol(cell, evidence)
        else:
            selected = select_compromised_reproducers(
                reproducer_order_for_cell(self._primary_adapter, cell),
                frozenset(self._primary_adapter.domain_ids),
                compromised_count,
            )
            compromised_reproducers: frozenset[DomainId] = (
                frozenset(NBaiotDomain(domain) for domain in selected)
                if selected is not None
                else frozenset()
            )
            required_row_count = row_requirement(cell)
            progression_state, attempts, _commitment_hashes, updates = reproduction_progression(
                cell,
                evidence,
                False,
                required_row_count,
                compromised_reproducers,
                self._primary_adapter,
                real_anchor,
                backdoor_scope=self.backdoor_scope_for_cell(cell),
            )
            if (
                progression_state is AdmissionState.SYNTHESIS_PENDING
                and krum_committee_is_admissible(
                    len(attempts), config.protocol.synthesis.maximum_byzantine_reproduction_rows
                )
            ):
                state, self._pending_real_report = final_gate_decision(
                    evidence,
                    source_domain,
                    tuple(NBaiotDomain(attempt.domain) for attempt in attempts),
                    is_plurality_active=True,
                    adapter=self._primary_adapter,
                    master_seed=cell.master_seed,
                    anchor=real_anchor,
                    coordinate_median_active=False,
                    no_final_synthesis_gate_active=False,
                    use_source_delta_for_source_domain=False,
                    force_first_row_to_source_delta=False,
                    precomputed_updates=updates,
                )
            else:
                state = AdmissionState.DORMANT
                self._pending_real_report = None
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
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
            source_domain = source_domain_for_cell(self._primary_adapter, cell)
            reproducer_domain = reproducer_order_for_cell(self._primary_adapter, cell)[0]
            eligible_verifiers = tuple(
                domain
                for domain in self._primary_adapter.domain_ids
                if verifier_is_eligible(domain, source_domain, reproducer_domain)
            )
            byzantine_order = byzantine_selection_order(
                eligible_verifiers,
                derive_uint32(BYZANTINE_VERIFIER_SELECTION_SEPARATOR, cell.master_seed),
            )
            compromised_count = compromised_verifier_count(condition)
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
                false_negative_domains: frozenset[DomainId] = (
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
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
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
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
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
            metrics = metrics_from_state(
                state, self._pending_real_report, legitimate_admission_eligible=True
            )
            return (state, (*metrics, ("evidence-arrival-cycle", None)))
        try:
            validate_no_safety_completion_before_tau_k(0, tau_k)
        except ValueError:
            state = resume_dormant_admission(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = metrics_from_state(
                state, self._pending_real_report, legitimate_admission_eligible=True
            )
            return (state, (*metrics, ("evidence-arrival-cycle", float(tau_k))))
        state = self._advance_protocol(cell, evidence)
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
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
                (
                    DescriptiveScientificMetric.T_EVIDENCE.value,
                    float(t_evidence) if t_evidence is not None else None,
                ),
                ("first-holder-cycle", float(first_holder) if first_holder is not None else None),
                (DescriptiveScientificMetric.WALL_CLOCK_SECONDS.value, None),
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
            metrics = metrics_from_state(
                state, self._pending_real_report, legitimate_admission_eligible=True
            )
        else:
            state, metrics = self._execute_baseline_cell(cell, evidence)
            post_evidence_wall_clock_seconds = timer.elapsed_seconds()
        phase_durations = self._last_protocol_phase_durations
        return (
            state,
            (
                *metrics,
                ("evidence-arrival-cycle", float(tau_k) if tau_k is not None else None),
                (
                    DescriptiveScientificMetric.T_EVIDENCE.value,
                    float(t_evidence) if t_evidence is not None else None,
                ),
                ("assignment-seconds", phase_durations.assignment_seconds),
                ("reproduce-seconds", phase_durations.reproduce_seconds),
                ("verify-seconds", phase_durations.verify_seconds),
                ("synthesize-seconds", phase_durations.synthesize_seconds),
                (
                    DescriptiveScientificMetric.WALL_CLOCK_SECONDS.value,
                    post_evidence_wall_clock_seconds,
                ),
            ),
        )

    def _execute_efficiency_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        real_anchor = self.real_anchor(cell.master_seed)
        if real_anchor is None:
            tensor_payload = b""
            parameter_shape: tuple[int, ...] = (0,)
            manifest_hash = dataset_manifest_hash(self._primary_adapter.prepared_root)
            capability_hash = manifest_hash
        else:
            flat_parameters = real_anchor.flat_parameters.detach().cpu().contiguous()
            tensor_payload = flat_parameters.numpy().tobytes()
            parameter_shape = (int(flat_parameters.numel()),)
            manifest_hash = real_anchor.dataset_manifest_hash
            capability_hash = compute_capability_identity(
                capability_contract_for_digest(self._primary_adapter, manifest_hash)
            )
        model_size_bytes = len(tensor_payload)
        semantic_cell_key_hash = hashlib.sha256(cell.semantic_key.encode("utf-8")).hexdigest()
        tensor_name = parameter_tensor_name(TensorParameterKind.MODEL, "linear.weight")
        receiver = NBAIOT_DOMAIN_ORDER[0].name

        def measured_execution() -> TimingWorkerResult:
            envelopes: list[bytes] = []
            metadata_records: list[CommunicationMessageMetadata] = []
            for message_type, count in efficiency_message_counts():
                for _index in range(count):
                    metadata = CommunicationMessageMetadata(
                        message_type=message_type,
                        dataset_manifest_hash=manifest_hash,
                        semantic_cell_key_hash=semantic_cell_key_hash,
                        master_seed=cell.master_seed,
                        round_index=None,
                        sender=SERVER_ID,
                        receiver=receiver,
                        capability_contract_hash=capability_hash,
                        payload_tensor_count=1 if model_size_bytes else 0,
                    )
                    envelopes.append(
                        encode_message_envelope(
                            metadata,
                            (
                                TensorEnvelopePayload(
                                    metadata=TensorPayloadMetadata(
                                        name=tensor_name,
                                        shape=parameter_shape,
                                        nbytes=model_size_bytes,
                                    ),
                                    payload=tensor_payload,
                                ),
                            )
                            if model_size_bytes
                            else (),
                        )
                    )
                    metadata_records.append(metadata)
            if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
                state = self._advance_protocol(cell, evidence)
            else:
                state, _baseline_metrics = self._execute_baseline_cell(cell, evidence)
            return (
                state,
                communication_bytes(tuple(envelopes)),
                model_transmission_count(tuple(metadata_records)),
            )

        observation = SingleProcessTimingWorker().measure(
            measured_execution,
            current_application_context().scientific_config.execution.timing.warmup_forward_passes,
        )
        state, bytes_total, transmissions = observation.value
        if cell.repetition is None:
            raise ValueError("Efficiency Measurement cell requires a repetition identity")
        diagnostic_root = REPOSITORY_ROOT / experiment_repetition_telemetry_root(
            cell.experiment,
            cell.method,
            cell.master_seed,
            cell.repetition,
        )
        diagnostic_root.mkdir(parents=True, exist_ok=True)
        (diagnostic_root / "timing-observation.json").write_text(
            TimingRepetitionObservation(
                experiment=cell.experiment,
                method=cell.method,
                condition=cell.condition,
                master_seed=cell.master_seed,
                repetition=cell.repetition,
                semantic_key=cell.semantic_key,
                wall_clock_seconds=observation.wall_clock_seconds,
                gpu_seconds=observation.gpu_seconds,
                peak_gpu_memory_bytes=observation.peak_gpu_memory_bytes,
                peak_host_rss_bytes=observation.peak_host_rss_bytes,
                communication_bytes=bytes_total,
                model_transmissions=transmissions,
            ).model_dump_json(indent=2)
            + "\n"
        )
        storage_bytes = sum(
            path.stat().st_size for path in diagnostic_root.rglob("*") if path.is_file()
        )
        return (
            state,
            (
                (
                    ComparisonMetric.POST_EVIDENCE_OVERHEAD,
                    observation.wall_clock_seconds,
                ),
                (DescriptiveScientificMetric.COMMUNICATION_BYTES.value, float(bytes_total)),
                (DescriptiveScientificMetric.MODEL_TRANSMISSIONS.value, float(transmissions)),
                (
                    DescriptiveScientificMetric.WALL_CLOCK_SECONDS.value,
                    observation.wall_clock_seconds,
                ),
                (DescriptiveScientificMetric.GPU_SECONDS.value, observation.gpu_seconds),
                (
                    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES.value,
                    float(observation.peak_gpu_memory_bytes),
                ),
                (
                    DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES.value,
                    float(observation.peak_host_rss_bytes),
                ),
                (DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES.value, float(storage_bytes)),
            ),
        )


class CellHandler(Protocol):
    def __call__(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]: ...


class CellHandlerRegistration(FrozenDomainModel):
    experiment: ExperimentName
    handler: CellHandlerName


CELL_HANDLER_REGISTRATIONS: tuple[CellHandlerRegistration, ...] = (
    CellHandlerRegistration(
        experiment=DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
        handler="_execute_data_and_domain_validation_cell",
    ),
    CellHandlerRegistration(
        experiment=PROTOCOL_INVARIANT_VALIDATION_NAME,
        handler="_execute_protocol_invariant_validation_cell",
    ),
    CellHandlerRegistration(
        experiment=BASELINE_IMPLEMENTATION_VALIDATION_NAME, handler="_execute_baseline_cell"
    ),
    CellHandlerRegistration(
        experiment=PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME, handler="_execute_opening_cell"
    ),
    CellHandlerRegistration(
        experiment=SINGLE_REPRODUCTION_NECESSITY_NAME, handler="_execute_plurality_cell"
    ),
    CellHandlerRegistration(
        experiment=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        handler="_execute_source_exclusion_cell",
    ),
    CellHandlerRegistration(
        experiment=EXTERNAL_VERIFICATION_NECESSITY_NAME,
        handler="_execute_external_verification_cell",
    ),
    CellHandlerRegistration(
        experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME, handler="_execute_primary_cell"
    ),
    CellHandlerRegistration(experiment=MECHANISM_ABLATION_NAME, handler="_execute_ablation_cell"),
    CellHandlerRegistration(
        experiment=COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
        handler="_execute_reproducer_robustness_cell",
    ),
    CellHandlerRegistration(
        experiment=COMPROMISED_VERIFIER_ROBUSTNESS_NAME, handler="_execute_verifier_robustness_cell"
    ),
    CellHandlerRegistration(
        experiment=BYZANTINE_BOUND_VIOLATION_NAME, handler="_execute_byzantine_bound_cell"
    ),
    CellHandlerRegistration(
        experiment=EVIDENCE_SCARCITY_AND_DORMANCY_NAME, handler="_execute_evidence_scarcity_cell"
    ),
    CellHandlerRegistration(
        experiment=SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME, handler="_execute_boundary_cell"
    ),
    CellHandlerRegistration(
        experiment=CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME, handler="_execute_boundary_cell"
    ),
    CellHandlerRegistration(
        experiment=HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME, handler="_execute_boundary_cell"
    ),
    CellHandlerRegistration(
        experiment=ADMISSION_DELAY_DECOMPOSITION_NAME, handler="_execute_admission_delay_cell"
    ),
    CellHandlerRegistration(
        experiment=EFFICIENCY_MEASUREMENT_NAME, handler="_execute_efficiency_cell"
    ),
    CellHandlerRegistration(
        experiment=SECONDARY_DATASET_GENERALIZATION_NAME, handler="_execute_secondary_cell"
    ),
)


def cell_handler_registration(experiment: ExperimentName) -> CellHandlerName | None:
    for registration in CELL_HANDLER_REGISTRATIONS:
        if registration.experiment == experiment:
            return registration.handler
    return None


def validate_cell_handler_registration() -> None:
    registered = set(REGISTERED_EXPERIMENT_NAMES)
    mapped = {registration.experiment for registration in CELL_HANDLER_REGISTRATIONS}
    missing = registered - mapped
    if missing:
        raise ValueError(f"registered experiments without a cell handler: {sorted(missing)}")
    unknown = mapped - registered
    if unknown:
        raise ValueError(f"cell handlers for unregistered experiments: {sorted(unknown)}")


class ProtocolCellExecutor(CellExecutor, ProtocolBaselineOutcomes, ProtocolCellDispatch):
    def __init__(
        self,
        primary_prepared_root: Path | None = None,
        secondary_prepared_root: Path | None = None,
        resolved_core: ResolvedCore | None = None,
    ) -> None:
        self._primary_adapter = DatasetAdapter(
            specification=dataset_specification(DatasetId.N_BAIOT),
            prepared_root=primary_prepared_root or prepared_evidence_root(DatasetId.N_BAIOT),
        )
        self._secondary_adapter = DatasetAdapter(
            specification=dataset_specification(DatasetId.CICIOT2023),
            prepared_root=secondary_prepared_root or prepared_evidence_root(DatasetId.CICIOT2023),
        )
        self._prepared_root = self._primary_adapter.prepared_root
        self._secondary_prepared_root = self._secondary_adapter.prepared_root
        self._resolved_core = resolved_core
        self.real_anchor_cache: OrderedDict[MasterSeed, RealAnchor | None] = OrderedDict()
        self._pending_real_report: RealReportSummary | None = None
        self._last_protocol_phase_durations = ProtocolPhaseDurations()

    def real_anchor(self, master_seed: MasterSeed) -> RealAnchor | None:
        if master_seed not in self.real_anchor_cache:
            self.real_anchor_cache[master_seed] = (
                train_anchor(self._primary_adapter, master_seed)
                if self._primary_adapter.evidence_available()
                else None
            )
        return self.real_anchor_cache[master_seed]

    def _same_context_verifier_panel(
        self,
        source_domain: DomainId | None,
        reproducer_domain: DomainId,
    ) -> tuple[DomainId, ...]:
        config = current_application_context().scientific_config
        eligible_verifiers = tuple(
            domain
            for domain in self._primary_adapter.domain_ids
            if verifier_is_eligible(domain, source_domain, reproducer_domain)
        )
        reproducer_feature_mean = nbaiot_adapter(
            self._primary_adapter.prepared_root
        ).anchor_train_feature_mean(reproducer_domain)
        if reproducer_feature_mean is None:
            raise ValueError(
                "same-context verification requires real anchor-train features for "
                f"{reproducer_domain}"
            )
        eligible_verifier_feature_means: list[DomainFeatureMean] = []
        for domain in eligible_verifiers:
            feature_mean = nbaiot_adapter(
                self._primary_adapter.prepared_root
            ).anchor_train_feature_mean(domain)
            if feature_mean is None:
                raise ValueError(
                    f"same-context verification requires real anchor-train features for {domain}"
                )
            eligible_verifier_feature_means.append(
                DomainFeatureMean(domain=domain, feature_mean=feature_mean)
            )
        return same_context_verifier_panel(
            reproducer_feature_mean,
            tuple(eligible_verifier_feature_means),
            config.protocol.verification.panel_size,
        )

    def candidate_capability_contract_passes(
        self,
        real_anchor: RealAnchor,
        source_domain: DomainId,
        candidate_flat_parameters: torch.Tensor,
    ) -> BooleanValue:
        config = current_application_context().scientific_config
        anchor_screen = evaluate_domain(
            nbaiot_adapter(self._primary_adapter.prepared_root),
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        candidate_screen = evaluate_domain(
            nbaiot_adapter(self._primary_adapter.prepared_root),
            real_anchor,
            candidate_flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        if anchor_screen is None or candidate_screen is None:
            return False
        contract = build_capability_contract(
            real_anchor.dataset_manifest_hash,
            role_hash_token(Role.POST_REFERENCE_REPLAY),
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            self._primary_adapter.target_class_token,
            len(self._primary_adapter.class_tokens) - 1,
            config.capability_contract,
        )
        target_f1_gain = target_capability_gain(candidate_screen.target_f1, anchor_screen.target_f1)
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_screen.supported_macro_f1, candidate_screen.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(
                value=candidate_screen.benign_far.value - anchor_screen.benign_far.value,
                denominator=1,
            )
            if candidate_screen.benign_far.value is not None
            and anchor_screen.benign_far.value is not None
            else MetricResult(value=None, denominator=0)
        )
        return capability_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def _scoped_capability_contract_passes(
        self,
        real_anchor: RealAnchor,
        source_domain: DomainId,
        candidate_flat_parameters: torch.Tensor,
        root_cause_scope: RootCauseScope,
    ) -> BooleanValue:
        config = current_application_context().scientific_config
        anchor_screen = evaluate_domain(
            nbaiot_adapter(self._primary_adapter.prepared_root),
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
            root_cause_scope=root_cause_scope,
        )
        candidate_screen = evaluate_domain(
            nbaiot_adapter(self._primary_adapter.prepared_root),
            real_anchor,
            candidate_flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
            root_cause_scope=root_cause_scope,
        )
        if anchor_screen is None or candidate_screen is None:
            return False
        contract = build_capability_contract(
            real_anchor.dataset_manifest_hash,
            role_hash_token(Role.POST_REFERENCE_REPLAY),
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            self._primary_adapter.target_class_token,
            len(self._primary_adapter.class_tokens) - 1,
            config.capability_contract,
        )
        target_f1_gain = target_capability_gain(candidate_screen.target_f1, anchor_screen.target_f1)
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_screen.supported_macro_f1, candidate_screen.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(
                value=candidate_screen.benign_far.value - anchor_screen.benign_far.value,
                denominator=1,
            )
            if candidate_screen.benign_far.value is not None
            and anchor_screen.benign_far.value is not None
            else MetricResult(value=None, denominator=0)
        )
        return capability_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def backdoor_scope_for_cell(self, cell: ScientificCell) -> BackdoorScope | None:
        config = current_application_context().scientific_config
        if cell.condition != ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT:
            return None
        real_feature_names = prepared_feature_names(self._primary_adapter.prepared_root)
        if real_feature_names is None:
            return None
        trigger_indices = tuple(real_feature_names.index(name) for name in NBAIOT_TRIGGER_FEATURES)
        return BackdoorScope(
            attack_generation_seed=derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed),
            poison_fraction=config.attacks_and_boundaries.hidden_source_backdoor.confirmatory_poison_fraction,
            trigger_feature_indices=trigger_indices,
            trigger_value=config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization,
        )

    def heterogeneity_scope_for_cell(self, cell: ScientificCell) -> HeterogeneityScope | None:
        config = current_application_context().scientific_config
        if cell.experiment != HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
            return None
        regime = HeterogeneityRegime(cell.condition)
        magnitudes = config.attacks_and_boundaries.heterogeneity.feature_shift_magnitudes
        if regime is HeterogeneityRegime.FEATURE_SHIFT_0_5:
            shift_magnitude = magnitudes[0]
        elif regime is HeterogeneityRegime.FEATURE_SHIFT_1_0:
            shift_magnitude = magnitudes[1]
        else:
            return None
        real_feature_names = prepared_feature_names(self._primary_adapter.prepared_root)
        if real_feature_names is None:
            return None
        heterogeneity_seed = derive_uint32("HETEROGENEITY_SEED", cell.master_seed)
        selected_feature_names = select_heterogeneity_shift_features(
            real_feature_names,
            heterogeneity_seed,
            config.attacks_and_boundaries.heterogeneity.feature_shift_selected_feature_count,
        )
        return HeterogeneityScope(
            heterogeneity_namespace_seed=heterogeneity_seed,
            selected_feature_names=selected_feature_names,
            feature_names=real_feature_names,
            shift_magnitude=shift_magnitude,
        )

    def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome:
        self._pending_real_report = None
        dataset = experiment_by_name(cell.experiment).dataset
        if dataset is DatasetId.CICIOT2023:
            prepared_root = self._secondary_prepared_root
            target_class_token = CICIOT2023_TARGET_LABEL
        else:
            prepared_root = self._primary_adapter.prepared_root
            target_class_token = self._primary_adapter.target_class_token
        if cell.experiment == PROTOCOL_INVARIANT_VALIDATION_NAME:
            evidence = PreparedEvidenceCounts(
                screen_target_count=0,
                reproduction_target_count=0,
                reproduction_supported_count=0,
                final_gate_adequate_domain_count=0,
            )
        else:
            evidence = load_prepared_evidence_counts(prepared_root, target_class_token)
            if evidence is None:
                return CellExecutionOutcome(
                    cell=cell,
                    terminal_state=ExperimentLifecycleState.INVALID,
                    failure=FailureDetail(
                        failure_class=FailureClass.EVIDENCE_INSUFFICIENT,
                        message=(
                            "prepared evidence is not materialized for this cell; "
                            "run fedsira preprocess first"
                        ),
                        cell_phase=ScientificCellPhase.PREPARE,
                    ),
                )
        try:
            _state, metrics = self._execute_cell_protocol(cell, evidence)
        except ValueError as error:
            return CellExecutionOutcome(
                cell=cell,
                terminal_state=ExperimentLifecycleState.INVALID,
                failure=FailureDetail(
                    failure_class=FailureClass.INVARIANT_VIOLATION,
                    message=str(error),
                    cell_phase=ScientificCellPhase.PREPARE,
                ),
            )
        trajectory = (
            self._evidence_scarcity_trajectory(metrics, _state)
            if cell.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME
            else ()
        )
        return CellExecutionOutcome(
            cell=cell,
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=metrics,
            state_trajectory=trajectory,
        )

    def _evidence_scarcity_trajectory(
        self,
        metrics: tuple[MetricObservation, ...],
        terminal_state: AdmissionState,
    ) -> tuple[AdmissionStateObservation, ...]:
        arrival_cycle = next(
            (value for name, value in metrics if name == "evidence-arrival-cycle"), None
        )
        scientific_config = current_application_context().scientific_config
        horizon = scientific_config.protocol.resource_horizon.maximum_logical_evidence_cycles
        return tuple(
            AdmissionStateObservation(
                cycle=cycle,
                state=(
                    AdmissionState.DORMANT
                    if arrival_cycle is None or cycle < arrival_cycle
                    else AdmissionState.VERIFICATION_PENDING
                    if cycle == arrival_cycle
                    else terminal_state
                ),
            )
            for cycle in range(horizon + 1)
        )

    def _execute_data_and_domain_validation_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        run_data_and_domain_evidence_validation(
            evidence.reproduction_target_count,
            evidence.reproduction_supported_count,
            evidence.final_gate_adequate_domain_count,
        )
        return (
            AdmissionState.ADMITTED,
            metrics_from_state(AdmissionState.ADMITTED, legitimate_admission_eligible=False),
        )

    def _execute_protocol_invariant_validation_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        run_protocol_invariant_validation()
        return (
            AdmissionState.ADMITTED,
            metrics_from_state(AdmissionState.ADMITTED, legitimate_admission_eligible=False),
        )

    def _execute_cell_protocol(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        handler_name = cell_handler_registration(cell.experiment)
        if handler_name is None:
            raise ValueError(f"no registered cell handler for experiment {cell.experiment}")
        handler = cast(CellHandler, getattr(self, handler_name))
        return handler(cell, evidence)


BYZANTINE_VERIFIER_SELECTION_SEPARATOR = "BYZANTINE_VERIFIER_SELECTION"


ANCHOR_CHECKPOINT_IDENTITY = "anchor-checkpoint"


SOURCE_CHECKPOINT_IDENTITY = "source-checkpoint"


def opening_mode_for_cell(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> AdmissionOpeningMode:
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return resolved_core.opening_mode
    if cell.method == OpeningMode.PROPOSAL_ASSISTED:
        return AdmissionOpeningMode.PROPOSAL_ASSISTED
    return AdmissionOpeningMode.CANDIDATE_FREE


def row_requirement(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> RequiredReproductionRowCount:
    config = current_application_context().scientific_config
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return config.protocol.synthesis.committee_size if resolved_core.plurality_survives else 1
    if cell.method in (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
        BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN,
    ) or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.ONE_INDEPENDENT_REPRODUCTION
    ):
        return 1
    if cell.method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.GENERIC_THREE_ROW_THRESHOLD
    ):
        return config.baselines.three_row_coordinate_median.row_count
    return config.protocol.synthesis.committee_size


def _domain_is_reproduction_adequate(adapter: DatasetAdapter, domain: DomainId) -> BooleanValue:
    config = current_application_context().scientific_config
    return reproduction_evidence_is_adequate(
        target_role_count(adapter, domain, Role.REPRODUCTION),
        supported_role_count(adapter, domain, Role.POST_REFERENCE_REPLAY),
        config.capability_contract.evidence_minima,
    )


def _train_reproduction_update(
    adapter: DatasetAdapter,
    cell: ScientificCell,
    anchor: RealAnchor,
    domain: DomainId,
    source_delta: torch.Tensor | None,
    compromised_reproducers: frozenset[DomainId],
    heterogeneity_scope: HeterogeneityScope | None,
    backdoor_scope: BackdoorScope | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    validate_reproduction_starts_from_anchor(anchor.flat_parameters, anchor.flat_parameters)
    if domain not in compromised_reproducers:
        return train_domain_reproduction_delta(
            adapter,
            cell.master_seed,
            anchor,
            domain,
            heterogeneity_scope=heterogeneity_scope,
        )
    condition = cell.condition
    if condition in (
        ReproducerCondition.ONE_SOURCE_COPY,
        ReproducerCondition.TWO_SOURCE_COPIES,
        PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
        ExternalVerificationCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
        SecondaryScenario.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER,
    ):
        if source_delta is None:
            return None
        return reproduction_update_vector(
            anchor.flat_parameters, anchor.flat_parameters + source_delta
        )
    trained = train_domain_reproduction_delta(
        adapter,
        cell.master_seed,
        anchor,
        domain,
        heterogeneity_scope=heterogeneity_scope,
        backdoor_scope=backdoor_scope,
    )
    if trained is None:
        return None
    if condition in (
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
    ):
        return scale_model_replacement_delta(
            trained,
            config.attacks_and_boundaries.byzantine_reproduction.model_replacement.delta_scale,
        )
    return trained


def reproduction_progression(
    cell: ScientificCell,
    evidence: PreparedEvidenceCounts,
    external_verification_active: BooleanValue,
    row_requirement: RequiredReproductionRowCount,
    compromised_reproducers: frozenset[DomainId],
    adapter: DatasetAdapter,
    anchor: RealAnchor | None,
    include_source_as_first_reproducer: BooleanValue = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
    source_delta: torch.Tensor | None = None,
) -> tuple[
    AdmissionState,
    tuple[ReproductionAttempt, ...],
    tuple[ArtifactDigest, ...],
    OrderedDict[DomainId, torch.Tensor],
]:
    del evidence
    if anchor is None:
        return (AdmissionState.DORMANT, (), (), OrderedDict())
    reproducer_order = reproducer_order_for_cell(adapter, cell)
    source_domain = source_domain_for_cell(adapter, cell)
    validate_reproduction_start_checkpoint(
        ANCHOR_CHECKPOINT_IDENTITY, frozenset({SOURCE_CHECKPOINT_IDENTITY})
    )
    validate_reproduction_starts_from_anchor(anchor.flat_parameters, anchor.flat_parameters)
    capability_identity = compute_capability_identity(
        capability_contract_for_digest(adapter, anchor.dataset_manifest_hash)
    )
    adequate_domains = frozenset(
        domain
        for domain in adapter.domain_ids
        if domain != source_domain and _domain_is_reproduction_adequate(adapter, domain)
    )
    attempts: list[ReproductionAttempt] = []
    commitment_hashes: list[ArtifactDigest] = []
    updates: OrderedDict[DomainId, torch.Tensor] = OrderedDict()
    certified_count = 0
    state = AdmissionState.REPRODUCTION_PENDING
    if (
        include_source_as_first_reproducer
        and source_domain is not None
        and source_delta is not None
    ):
        reproduced = anchor.flat_parameters + source_delta
        commitment_hash = commitment_digest(
            source_domain, cell.master_seed, capability_identity, reproduced
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        updates[source_domain] = source_delta
        attempts.append(
            ReproductionAttempt(domain=source_domain, was_trained=True, is_certified=True)
        )
        certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is AdmissionState.SYNTHESIS_PENDING:
            return (state, tuple(attempts), tuple(commitment_hashes), updates)
    for _row_index in range(len(reproducer_order)):
        next_domain = next_reproducer_domain(
            reproducer_order, consumed_domains(attempts), adequate_domains
        )
        if next_domain is None:
            state = handle_no_adequate_unconsumed_domain(certified_count >= row_requirement)
            break
        domain = NBaiotDomain(next_domain)
        update = _train_reproduction_update(
            adapter,
            cell,
            anchor,
            domain,
            source_delta,
            compromised_reproducers,
            heterogeneity_scope,
            backdoor_scope,
        )
        if update is None:
            state = handle_inadequate_domain()
            continue
        reproduced = anchor.flat_parameters + update
        commitment_hash = commitment_digest(
            domain, cell.master_seed, capability_identity, reproduced
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        updates[domain] = update
        is_certified = domain not in compromised_reproducers or not external_verification_active
        attempts.append(
            ReproductionAttempt(domain=domain, was_trained=True, is_certified=is_certified)
        )
        if is_certified:
            certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is AdmissionState.SYNTHESIS_PENDING:
            break
    return (state, tuple(attempts), tuple(commitment_hashes), updates)


def single_verifier_progression(
    cell: ScientificCell,
    source_domain: DomainId | None,
    adapter: DatasetAdapter,
    anchor: RealAnchor | None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[
    AdmissionState,
    tuple[ReproductionAttempt, ...],
    tuple[ArtifactDigest, ...],
    OrderedDict[DomainId, torch.Tensor],
]:
    if anchor is None:
        return (AdmissionState.DORMANT, (), (), OrderedDict())
    config = current_application_context().scientific_config
    reproducer_order = reproducer_order_for_cell(adapter, cell)
    adequate_domains = frozenset(
        domain
        for domain in adapter.domain_ids
        if domain != source_domain and _domain_is_reproduction_adequate(adapter, domain)
    )
    capability_identity = compute_capability_identity(
        capability_contract_for_digest(adapter, anchor.dataset_manifest_hash)
    )
    consumed: set[NBaiotDomain] = set()
    while True:
        candidate = first_eligible_non_source_reproducer(
            reproducer_order, adequate_domains - frozenset(consumed)
        )
        if candidate is None:
            return (AdmissionState.DORMANT, (), (), OrderedDict())
        next_domain = NBaiotDomain(candidate)
        consumed.add(next_domain)
        update = train_domain_reproduction_delta(
            adapter,
            cell.master_seed,
            anchor,
            next_domain,
            heterogeneity_scope=heterogeneity_scope,
        )
        if update is None:
            continue
        reproduced = anchor.flat_parameters + update
        commitment_hash = commitment_digest(
            next_domain, cell.master_seed, capability_identity, reproduced
        )
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        panel_order = verifier_panel(
            adapter,
            source_domain,
            next_domain,
            cell.master_seed,
            config.protocol.verification,
            commitment_hash,
        )
        verifier_domain = single_fresh_verifier_domain(
            panel_order, frozenset(), frozenset(panel_order)
        )
        if verifier_domain is None:
            continue
        report = honest_verifier_report(
            adapter,
            anchor,
            reproduced,
            NBaiotDomain(verifier_domain),
            heterogeneity_scope,
        )
        verifier_outcome = single_fresh_verifier_outcome(verifier_domain, report)
        if verifier_outcome is AdmissionState.ADMITTED:
            attempt = ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=True)
            return (
                AdmissionState.SYNTHESIS_PENDING,
                (attempt,),
                (commitment_hash,),
                OrderedDict(((next_domain, update),)),
            )
        if verifier_outcome is AdmissionState.REJECTED:
            continue


def compromised_reproducer_count(condition: ConditionName) -> CompromisedReproducerCount:
    if condition in (
        ReproducerCondition.ONE_SOURCE_COPY,
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
        ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
    ):
        return 1
    if condition in (
        ReproducerCondition.TWO_SOURCE_COPIES,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
        ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
    ):
        return 2
    return 0


def compromised_verifier_count(condition: ConditionName) -> ByzantineDomainCount:
    if condition in (
        VerifierCondition.ONE_FALSE_POSITIVE,
        VerifierCondition.ONE_FALSE_NEGATIVE,
    ):
        return 1
    if condition in (
        VerifierCondition.TWO_FALSE_POSITIVES,
        VerifierCondition.TWO_FALSE_NEGATIVES,
    ):
        return 2
    return 0


RESOLVED_FEDSIRA_CORE_METHOD = CoreMethodIdentity.RESOLVED_FEDSIRA_CORE


def efficiency_message_counts() -> (
    tuple[
        tuple[CommunicationMessageType, CommunicationMessageCount],
        ...,
    ]
):
    return (
        (CommunicationMessageType.SOURCE_COMMITMENT, 1),
        (CommunicationMessageType.MODEL_DISTRIBUTION, 8),
        (CommunicationMessageType.UPDATE_SUBMISSION, 8),
        (CommunicationMessageType.CAPABILITY_CONTRACT, 1),
        (CommunicationMessageType.REVIEW_ASSIGNMENT, 3),
        (CommunicationMessageType.REVIEW_REPORT, 3),
        (CommunicationMessageType.VERIFIER_ASSIGNMENT, 5),
        (CommunicationMessageType.VERIFIER_REPORT, 5),
        (CommunicationMessageType.FINAL_GATE_ASSIGNMENT, 6),
        (CommunicationMessageType.FINAL_GATE_REPORT, 6),
        (CommunicationMessageType.DECISION, 1),
    )
