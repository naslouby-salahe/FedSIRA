from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import replace
from pathlib import Path
from typing import Protocol, cast

import numpy
import torch

from fedsira.artifacts.paths import (
    current_repository_root,
    experiment_repetition_telemetry_root,
    prepared_evidence_root,
)
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
    flat_parameters_identity,
    prepared_feature_names,
    quantity_skew_multiplier_by_domain,
    quantity_skew_multiplier_for_domain,
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
    AblationReproducerStrategy,
    AblationScenario,
    AblationVariant,
    AdmissionOpeningMode,
    AdmissionState,
    ArtifactFamily,
    BaselineIdentity,
    BoundCondition,
    ByzantineVerifierBehavior,
    CapabilityContractScope,
    CoreMethodIdentity,
    DatasetId,
    DelayPhaseMetric,
    DescriptiveScientificMetric,
    DormantOrigin,
    EvidenceArrivalSchedule,
    ExperimentLifecycleState,
    ExperimentName,
    ExternalVerificationCondition,
    FailureClass,
    HeterogeneityRegime,
    MetricObservationKey,
    OpeningMode,
    PluralityCondition,
    PrimaryScenario,
    ReproducerCondition,
    ScientificCellPhase,
    SeedDerivationLabel,
    SourceExclusionMethod,
    TernaryOutcome,
    VerifierCondition,
    VerifierProfile,
    WorkspaceFileToken,
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
    CellHandlerName,
    CommunicationMessageCount,
    CompromisedProductionAncestry,
    DeltaScale,
    DomainId,
    FrozenDomainModel,
    MasterSeed,
    MetricObservation,
    MetricValue,
    Probability,
    ReproductionAttemptCount,
)
from fedsira.evaluation.comparisons import (
    ComparisonMetric,
    ablation_metric,
)
from fedsira.evaluation.metrics import (
    RealReportSummary,
    benign_false_alarm_rate_increase,
    boundary_metric_set,
    clean_proposal_oracle_label,
    compute_screen_differential,
    compute_source_backdoor_asr,
    evaluate_domain,
    false_launch_rate,
    malicious_admission_from_ancestry,
    metrics_from_state,
    non_source_domains,
    production_depends_on_compromised_contributor,
    reproduction_attempt_count,
    root_cause_partitioned_row_ids,
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.evaluation.scores import capture_model_score_artifacts
from fedsira.evaluation.screen_evidence import evaluate_screen_domain
from fedsira.evaluation.service import (
    SingleProcessTimingWorker,
    TimingRepetitionObservation,
    TimingWorkerResult,
    compute_capability_under_specification_summary,
    compute_shared_epistemic_failure_summary,
)
from fedsira.evaluation.statistics import mean_of_defined_values as mean_of_defined
from fedsira.experiments.byzantine import (
    SOURCE_COPY_CONDITIONS,
    compromised_reproducer_count,
    compromised_verifier_count,
)
from fedsira.experiments.cell_parameters import (
    RESOLVED_FEDSIRA_CORE_METHOD,
    domain_is_reproduction_adequate,
    opening_mode_for_cell,
    row_requirement,
)
from fedsira.experiments.checkpoints import (
    publish_anchor_checkpoints,
    publish_trained_update,
    source_candidate_stage_identity,
)
from fedsira.experiments.collapse import ResolvedCore
from fedsira.experiments.definitions import (
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    BASELINE_IMPLEMENTATION_VALIDATION_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    CATALOG_EXPERIMENT_NAMES,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    LEAVE_FAULT_CERTIFICATE_VALIDATION_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    PROTOCOL_INVARIANT_VALIDATION_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    EpistemicFailureType,
    ProposalEpisode,
    ablation_mixed_episode_instances,
    ablation_opening_mode,
    ablation_reproducer_strategy,
    ablation_scenario_episode,
    ablation_scenario_for_condition,
    core_opening_episode,
    experiment_by_name,
    feature_shift_magnitude,
)
from fedsira.experiments.engine import (
    AdmissionStateObservation,
    CellExecutionOutcome,
    CellExecutor,
    PreparedEvidenceCounts,
    PreparedEvidenceProvenanceError,
    ProtocolPhaseDurations,
    invalid_prepared_evidence_outcome,
    load_prepared_evidence_counts,
)
from fedsira.experiments.execution import (
    run_data_and_domain_evidence_validation,
    run_protocol_invariant_validation,
)
from fedsira.experiments.leave_fault_validation import execute_leave_fault_validation_cell
from fedsira.experiments.observations import (
    declared_contract_scopes,
    measurement_cycles,
    observation_value,
    observations_with_replacements,
    permanent_singleton_admission,
)
from fedsira.experiments.planning import (
    ScientificCell,
)
from fedsira.experiments.protocol_evidence import (
    CALIBRATED_BASELINE_METHODS,
    PROTOCOL_EVIDENCE_SCHEMA_VERSION,
    KrumSynthesizedUpdatePayload,
    publish_krum_synthesized_update,
    record_baseline_calibration,
    record_production_evidence,
    record_verification_evidence,
)
from fedsira.experiments.reproduction_progression import (
    model_replacement_attack_feasible_domains,
    reproduction_progression,
)
from fedsira.learning.federated import train_anchor
from fedsira.learning.post_reference import (
    certified_domain_delta_committee,
    train_domain_reproduction_delta,
    train_generic_hard_supported_examples_delta,
    train_irrelevant_source_improvement_delta,
    train_source_candidate_delta,
)
from fedsira.protocol.admission import (
    final_gate_decision,
    production_committee,
)
from fedsira.protocol.attacks import (
    resolve_byzantine_verifier_vote,
    source_copy_update,
    validate_declared_source_backdoor_poison_fraction,
)
from fedsira.protocol.baselines.defenses import (
    CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES,
    DomainFeatureMean,
    ReviewPanelProfile,
    client_review_direct_admission_production_is_source,
    client_review_then_retrain_local_epochs,
    client_review_then_retrain_should_discard_source_weights,
    direct_krum_committee_rows,
    parameter_similarity_certification_row_results,
    review_panel_requirements,
    same_context_verifier_panel,
    validate_client_review_composite_screen,
    validate_client_review_reviewer_count,
    validate_group_without_target_member_uses_supported_only,
    validate_three_row_coordinate_median_committee_size,
)
from fedsira.protocol.baselines.outcomes import ProtocolBaselineOutcomes
from fedsira.protocol.baselines.registry import (
    ORDINARY_POST_REFERENCE_DATA_ACCESS,
    BaselineValidationFixture,
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
)
from fedsira.protocol.proposal import (
    OpeningStageOutcome,
    ScreenDomainResult,
    candidate_screen_transition,
    first_target_sample_id,
    opening_identity,
    screen_domain_order,
    screen_fold_index,
    source_domain_for_cell,
    start_admission,
)
from fedsira.protocol.reproduction import (
    ReproductionAttempt,
    commitment_digest,
    select_compromised_reproducers,
    validate_commitment_exists_before_verifier_assignment,
)
from fedsira.protocol.rules import (
    apply_logical_cycle_expiry,
    compute_t_evidence,
    diagnostic_at_least_two_byzantine_probability,
    first_cycle_with_minimum_eligible_evidence_holders,
    first_holder_cycle_for_domain,
    holder_count_at_cycle,
    krum_committee_is_admissible,
    reproducer_order_for_cell,
    reproduction_update_vector,
    resume_dormant_admission,
    validate_no_safety_completion_before_tau_k,
)
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    require_source_identity_excluded_from_synthesis,
    select_krum_update,
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
    ElapsedTimer,
    FailureDetail,
    current_application_context,
    derive_uint32,
    namespace_seed,
)

_ORDINARY_CLIENT_ATTACK_METHODS = (
    BaselineIdentity.FEDAVG_REFERENCE,
    BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
    BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN,
    BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER,
    BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE,
    BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
)
_SOURCE_POISON_AVERAGING_METHODS = (
    BaselineIdentity.FEDAVG_REFERENCE,
    BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN,
    BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER,
    BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE,
    BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
)


def _efficiency_message_counts() -> (
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


class ProtocolCellDispatch:
    _primary_adapter: DatasetAdapter
    _prepared_root: Path
    _secondary_prepared_root: Path
    _resolved_core: ResolvedCore | None
    _pending_real_report: RealReportSummary | None
    _last_protocol_phase_durations: ProtocolPhaseDurations
    _last_committee_deltas: OrderedDict[DomainId, torch.Tensor]
    _last_synthesis_row_ids: tuple[DomainId, ...]
    _last_production_contributor_ids: tuple[DomainId, ...]
    _last_designated_compromised_ids: tuple[DomainId, ...]
    _last_compromised_reproducers: frozenset[DomainId]
    _last_ablation_strategy: AblationReproducerStrategy
    _last_reproduction_attempts: ReproductionAttemptCount
    _last_certified_attempts: ReproductionAttemptCount
    _last_verifier_report_count: ReproductionAttemptCount
    _last_verifier_abstention_count: ReproductionAttemptCount
    _last_opening_stage: OpeningStageOutcome | None

    def real_anchor(self, master_seed: MasterSeed) -> RealAnchor | None: ...

    def backdoor_scope_for_cell(self, cell: ScientificCell) -> BackdoorScope | None: ...

    def source_backdoor_scope_for_cell(self, cell: ScientificCell) -> BackdoorScope | None: ...

    def _configured_backdoor_scope(
        self, cell: ScientificCell, poison_fraction: Probability
    ) -> BackdoorScope | None: ...

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
        claim_metrics: tuple[MetricObservation, ...] = ()
        if (
            ablation_scenario_for_condition(cell.condition)
            is AblationScenario.MIXED_LEGITIMATE_IRRELEVANT_PROPOSAL
        ):
            return self._execute_mixed_episode_ablation_cell(cell, evidence)
        if variant == AblationVariant.RANDOM_COMMITTEE_PROFILE:
            verifier_cell = replace(
                cell,
                method=VerifierProfile.RANDOM_COMMITTEE_DIAGNOSTIC,
                condition=VerifierCondition.ONE_FALSE_POSITIVE,
            )
            state, metrics = self._execute_verifier_robustness_cell(verifier_cell, evidence)
            return (state, (*metrics, *self._ablation_claim_metrics(cell, state)))
        if variant in (
            AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW,
            AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK,
        ):
            state = (
                self.client_review_outcome(cell)
                if variant == AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW
                else self._source_release_after_full_external_check_outcome(cell, evidence)
            )
            released_source = source_domain_for_cell(self._primary_adapter, cell)
            released_ids = (released_source,) if released_source is not None else ()
            return (
                state,
                (
                    *metrics_from_state(
                        state, self._pending_real_report, legitimate_admission_eligible=True
                    ),
                    (
                        ComparisonMetric.ATTACK_SUCCESS_RATE,
                        self._deployed_source_asr(cell)
                        if state is AdmissionState.ADMITTED
                        else 0.0,
                    ),
                    (
                        ComparisonMetric.MALICIOUS_ADMISSION,
                        self._ancestry_malicious_admission(
                            state,
                            released_source is not None,
                            released_ids,
                        ),
                    ),
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
                opening_cell, evidence, screen_predicate_variant=cast(AblationVariant, variant)
            )
        state = self._advance_protocol(cell, evidence)
        claim_metrics = self._ablation_claim_metrics(cell, state)
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
                extra.append(
                    (
                        MetricObservationKey.PARAMETER_SIMILARITY_COMMITTED_ROWS,
                        float(len(committed_rows)),
                    )
                )
                extra.append(
                    (
                        MetricObservationKey.PARAMETER_SIMILARITY_CERTIFIED_ROWS,
                        float(sum(row_results)),
                    )
                )
        elif variant == AblationVariant.GENERIC_THREE_ROW_THRESHOLD:
            validate_three_row_coordinate_median_committee_size(
                row_requirement(cell, self._resolved_core),
                config.baselines.three_row_coordinate_median,
            )
            if krum_committee_is_admissible(3, 1):
                raise ValueError(
                    "Generic Three-Row Threshold requires the Krum n=3,f=1 branch to be Invalid"
                )
            extra.append((MetricObservationKey.KRUM_N3_F1_INVALID, 1.0))
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
                balanced_selection_seed = derive_uint32(
                    SeedDerivationLabel.ATTACK_GENERATION_SEED, cell.master_seed
                )
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
                    scoped_passes = tuple(
                        self._scoped_capability_contract_passes(
                            real_anchor,
                            domain,
                            candidate_flat,
                            broad_scope
                            if contract is CapabilityContractScope.BROAD_TARGET_ONLY
                            else replace(broad_scope, contract_scope=contract),
                        )
                        for contract in declared_contract_scopes()
                    )
                    if sum(scoped_passes) == 1:
                        false_same_count += 1
                extra.append(
                    (
                        MetricObservationKey.CAPABILITY_CONTRACT_GRANULARITY_BROAD_CERTIFIED_ROWS,
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
        return (state, (*metrics, *claim_metrics, *extra))

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
            false_certification_count=0,
            broad_certified_row_count=0,
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
                        MetricObservationKey.ROOT_CAUSE_A_TARGET_F1,
                        capability_summary.root_cause_a_target_f1.value,
                    )
                )
                extra.append(
                    (
                        MetricObservationKey.ROOT_CAUSE_B_TARGET_F1,
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
                (
                    MetricObservationKey.PROPOSAL_ORACLE_LABEL,
                    float(oracle_label is ProposalOracleLabel.ORACLE_VALID),
                )
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
            extra.append((MetricObservationKey.TARGET_ROW_IDS, float(len(target_row_ids))))
        if cell.experiment == SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME:
            failure_type_token, strength_token = cell.condition.split("|")
            failure_type = EpistemicFailureType(failure_type_token)
            strength = float(strength_token)
            attack_seed = derive_uint32(
                SeedDerivationLabel.ATTACK_GENERATION_SEED, cell.master_seed
            )
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
                    (
                        MetricObservationKey.DEFINED_DOMAIN_COUNT,
                        float(epistemic_summary.defined_domain_count),
                    )
                )
                extra.append(
                    (
                        DescriptiveScientificMetric.TARGET_F1_GAIN,
                        epistemic_summary.target_f1_gain.value,
                    )
                )
                extra.append(
                    (
                        MetricObservationKey.SUPPORTED_MACRO_F1_DROP,
                        epistemic_summary.supported_macro_f1_drop.value,
                    )
                )
                extra.append(
                    (
                        ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
                        epistemic_summary.benign_far_increase.value,
                    )
                )
                extra.append(
                    (
                        MetricObservationKey.DIAGNOSTIC_MARKER_VALUE,
                        epistemic_summary.diagnostic_marker.value,
                    )
                )
                extra.append(
                    (
                        MetricObservationKey.DIAGNOSTIC_MARKER_INSUFFICIENT,
                        1.0 if epistemic_summary.diagnostic_marker.value is None else 0.0,
                    )
                )
                extra.append(
                    (
                        MetricObservationKey.PROPOSAL_ORACLE_LABEL,
                        float(oracle_label is ProposalOracleLabel.ORACLE_VALID),
                    )
                )
            else:
                extra.append((MetricObservationKey.DEFINED_DOMAIN_COUNT, 0.0))
                extra.append((DescriptiveScientificMetric.TARGET_F1_GAIN, None))
                extra.append((MetricObservationKey.SUPPORTED_MACRO_F1_DROP, None))
                extra.append((ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE, None))
                extra.append((MetricObservationKey.DIAGNOSTIC_MARKER_VALUE, None))
                extra.append((MetricObservationKey.DIAGNOSTIC_MARKER_INSUFFICIENT, 1.0))
                extra.append((MetricObservationKey.PROPOSAL_ORACLE_LABEL, 0.0))
        if cell.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
            regime = cell.condition
            heterogeneity_seed = derive_uint32(
                SeedDerivationLabel.HETEROGENEITY_SEED, cell.master_seed
            )
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
                extra.append((MetricObservationKey.QUANTITY_SKEW_CAP, float(applied_cap)))
            else:
                heterogeneity_scope = self.heterogeneity_scope_for_cell(cell)
                if heterogeneity_scope is not None:
                    feature_sign = feature_shift_sign(
                        NBAIOT_DOMAIN_ORDER[0],
                        heterogeneity_scope.selected_feature_names[0],
                        heterogeneity_seed,
                    )
                    extra.append((MetricObservationKey.FEATURE_SHIFT_SIGN, float(feature_sign)))
                    extra.append(
                        (
                            MetricObservationKey.FEATURE_SHIFT_COUNT,
                            float(len(heterogeneity_scope.selected_feature_names)),
                        )
                    )
                else:
                    extra.append((MetricObservationKey.FEATURE_SHIFT_SIGN, None))
                    extra.append((MetricObservationKey.FEATURE_SHIFT_COUNT, 0.0))
        return (state, (*metrics, *extra))

    def _run_opening_stage(
        self,
        cell: ScientificCell,
        episode: ProposalEpisode,
        opening_mode: AdmissionOpeningMode,
        screen_predicate_variant: AblationVariant | None = None,
    ) -> OpeningStageOutcome:
        config = current_application_context().scientific_config
        entry = start_admission(opening_mode)
        if entry.direct_production_weight != 0.0:
            raise ValueError("source direct production weight must be 0.0")
        episode_is_legitimate = episode in (
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        )
        screen_cell = replace(cell, condition=episode)
        source_domain = source_domain_for_cell(self._primary_adapter, screen_cell)
        real_anchor = self.real_anchor(cell.master_seed)
        resolved_opening_identity = (
            opening_identity(self._primary_adapter, real_anchor.dataset_manifest_hash)
            if real_anchor is not None
            else None
        )
        real_source_delta: torch.Tensor | None = None
        if (
            real_anchor is not None
            and source_domain is not None
            and opening_mode is AdmissionOpeningMode.PROPOSAL_ASSISTED
        ):
            if episode is ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES:
                real_source_delta = train_generic_hard_supported_examples_delta(
                    nbaiot_adapter(self._primary_adapter.prepared_root),
                    cell.master_seed,
                    real_anchor,
                    source_domain,
                )
            elif episode is ProposalEpisode.IRRELEVANT_SOURCE_IMPROVEMENT:
                real_source_delta = train_irrelevant_source_improvement_delta(
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
                    backdoor_scope=self.source_backdoor_scope_for_cell(screen_cell),
                )
                if real_source_delta is not None:
                    publish_trained_update(
                        ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT,
                        self._primary_adapter.dataset,
                        cell.master_seed,
                        source_candidate_stage_identity(episode, source_domain),
                        real_anchor.dataset_manifest_hash,
                        real_source_delta,
                        real_anchor.input_width,
                        real_anchor.output_width,
                        self._primary_adapter.class_tokens,
                    )
        if real_anchor is None or source_domain is None:
            state = AdmissionState.DORMANT
            screen_results: tuple[ScreenDomainResult, ...] = ()
            real_differential_a: MetricValue | None = None
        else:
            non_source = tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain)
            screen_order = screen_domain_order(
                non_source,
                screen_domain_order_namespace_seed=derive_uint32(
                    SeedDerivationLabel.SCREEN_DOMAIN_ORDER_SEED, cell.master_seed
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
        screen_fold_seed = derive_uint32(SeedDerivationLabel.SCREEN_FOLD_SEED, cell.master_seed)
        fold_sample_id = (
            first_target_sample_id(
                self._primary_adapter, NBaiotDomain(screen_results[0].domain), Role.CANDIDATE_SCREEN
            )
            if screen_results
            else None
        )
        return OpeningStageOutcome(
            state=state,
            episode=episode,
            source_delta=real_source_delta,
            screen_results=screen_results,
            screen_differential_a=real_differential_a,
            capability_contract_passes=(1.0 if resolved_opening_identity is not None else 0.0),
            screen_fold_index=(
                float(
                    screen_fold_index(
                        fold_sample_id, screen_fold_seed, config.protocol.proposal_screen.fold_count
                    )
                )
                if fold_sample_id is not None
                else None
            ),
            legitimate_admission_eligible=episode_is_legitimate,
        )

    def _execute_opening_cell(
        self,
        cell: ScientificCell,
        evidence: PreparedEvidenceCounts,
        screen_predicate_variant: AblationVariant | None = None,
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        episode = ProposalEpisode(cell.condition)
        stage = self._run_opening_stage(
            cell,
            episode,
            opening_mode_for_cell(cell, self._resolved_core),
            screen_predicate_variant,
        )
        self._last_opening_stage = stage
        state = stage.state
        if state is AdmissionState.ADMISSION_OPEN:
            state = self._advance_protocol(cell, evidence, opening_resolved=True)
        metrics = metrics_from_state(
            state,
            self._pending_real_report,
            legitimate_admission_eligible=stage.legitimate_admission_eligible,
        )
        return (
            state,
            (
                *metrics,
                *self._opening_stage_observations(
                    stage,
                    state,
                    source_domain_for_cell(self._primary_adapter, cell),
                ),
            ),
        )

    def _opening_stage_observations(
        self,
        stage: OpeningStageOutcome,
        state: AdmissionState,
        source_domain: DomainId | None,
    ) -> tuple[MetricObservation, ...]:
        false_launch_result = false_launch_rate(
            false_launch_count=1
            if state is AdmissionState.ADMITTED and (not stage.legitimate_admission_eligible)
            else 0,
            adequate_defined_oracle_count=1 if stage.screen_results else 0,
        )
        trained_domains = frozenset(
            result.domain for result in stage.screen_results if result.meets_opening_predicate
        )
        attempts = reproduction_attempt_count(
            domains_with_training_start=trained_domains
            if state is AdmissionState.ADMITTED
            else frozenset(),
            evidence_inadequate_domains=frozenset(
                result.domain for result in stage.screen_results if not result.is_evidence_adequate
            ),
        )
        return (
            ("capability-contract-passes", stage.capability_contract_passes),
            ("screen-fold-index", stage.screen_fold_index),
            ("screen-differential-a", stage.screen_differential_a),
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
                self._ancestry_malicious_admission(
                    state,
                    stage.episode is ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
                    (source_domain,) if source_domain is not None else (),
                ),
            ),
        )

    def _execute_mixed_episode_ablation_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        instances: list[tuple[ProposalEpisode, AdmissionState, tuple[MetricObservation, ...]]] = []
        for episode in ablation_mixed_episode_instances(
            AblationScenario.MIXED_LEGITIMATE_IRRELEVANT_PROPOSAL
        ):
            instance_state, instance_observations = self._execute_opening_cell(
                replace(cell, condition=episode), evidence
            )
            instances.append((episode, instance_state, instance_observations))
        legitimate = next(
            instance
            for instance in instances
            if instance[0] is ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY
        )
        irrelevant = next(
            instance
            for instance in instances
            if instance[0] is ProposalEpisode.IRRELEVANT_SOURCE_IMPROVEMENT
        )
        state = legitimate[1]
        attempts = mean_of_defined(
            tuple(
                observation_value(instance_observations, ComparisonMetric.REPRODUCTION_ATTEMPTS)
                for _episode, _state, instance_observations in instances
            )
        )
        overhead = mean_of_defined(
            tuple(
                observation_value(instance_observations, ComparisonMetric.POST_EVIDENCE_OVERHEAD)
                for _episode, _state, instance_observations in instances
            )
        )
        return (
            state,
            observations_with_replacements(
                legitimate[2],
                (
                    (
                        ComparisonMetric.FALSE_LAUNCH,
                        observation_value(irrelevant[2], ComparisonMetric.FALSE_LAUNCH),
                    ),
                    (ComparisonMetric.REPRODUCTION_ATTEMPTS, attempts),
                    (ComparisonMetric.POST_EVIDENCE_OVERHEAD, overhead),
                    (
                        ComparisonMetric.MALICIOUS_ADMISSION,
                        observation_value(irrelevant[2], ComparisonMetric.MALICIOUS_ADMISSION),
                    ),
                ),
            ),
        )

    def _ablation_production_is_compromised(
        self, cell: ScientificCell
    ) -> CompromisedProductionAncestry:
        compromised = self._last_compromised_reproducers
        if not compromised:
            return False
        strategy = self._last_ablation_strategy
        if strategy is AblationReproducerStrategy.MODEL_REPLACEMENT and not (
            self._last_committee_deltas
        ):
            return False
        if not self._last_committee_deltas:
            return True
        config = current_application_context().scientific_config
        committee = production_committee(
            self._last_committee_deltas,
            tuple(self._last_committee_deltas),
        )
        if krum_committee_is_admissible(
            len(committee), config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ):
            selected = select_krum_update(
                committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
            )
            return selected.reproducer_domain in compromised
        return bool(compromised & frozenset(self._last_committee_deltas))

    def _ablation_claim_metrics(
        self, cell: ScientificCell, state: AdmissionState
    ) -> tuple[MetricObservation, ...]:
        variant = AblationVariant(cell.method)
        scenario = AblationScenario(cell.condition)
        admitted = state is AdmissionState.ADMITTED
        observations: list[MetricObservation] = []
        asr_metric = (
            ablation_metric(variant)[0]
            if variant is not AblationVariant.FULL_FEDSIRA
            else ComparisonMetric.ATTACK_SUCCESS_RATE
        )
        if asr_metric is ComparisonMetric.ATTACK_SUCCESS_RATE:
            observations.append(
                (ComparisonMetric.ATTACK_SUCCESS_RATE, self._ablation_production_asr(cell))
            )
        if asr_metric is ComparisonMetric.MALICIOUS_ADMISSION or scenario in (
            AblationScenario.ONE_MALICIOUS_REPRODUCER,
            AblationScenario.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER,
            AblationScenario.ONE_COMPROMISED_VERIFIER,
        ):
            observations.append(
                (
                    ComparisonMetric.MALICIOUS_ADMISSION,
                    None
                    if not self._last_compromised_reproducers
                    else float(admitted and self._ablation_production_is_compromised(cell)),
                )
            )
        if asr_metric is ComparisonMetric.REPRODUCTION_ATTEMPTS:
            observations.append(
                (
                    ComparisonMetric.REPRODUCTION_ATTEMPTS,
                    float(self._last_reproduction_attempts),
                )
            )
        if asr_metric is ComparisonMetric.POST_EVIDENCE_OVERHEAD:
            durations = self._last_protocol_phase_durations
            observations.append(
                (
                    ComparisonMetric.POST_EVIDENCE_OVERHEAD,
                    durations.reproduce_seconds
                    + durations.verify_seconds
                    + durations.synthesize_seconds
                    + durations.assignment_seconds,
                )
            )
        return tuple(observations)

    def _deployed_source_asr(self, cell: ScientificCell) -> MetricValue | None:
        backdoor_scope = self.source_backdoor_scope_for_cell(cell)
        real_anchor = self.real_anchor(cell.master_seed)
        source_domain = source_domain_for_cell(self._primary_adapter, cell)
        if backdoor_scope is None or real_anchor is None or source_domain is None:
            return None
        source_delta = train_source_candidate_delta(
            nbaiot_adapter(self._primary_adapter.prepared_root),
            cell.master_seed,
            real_anchor,
            source_domain,
            backdoor_scope=backdoor_scope,
        )
        if source_delta is None:
            return None
        return compute_source_backdoor_asr(
            nbaiot_adapter(self._primary_adapter.prepared_root),
            real_anchor,
            real_anchor.flat_parameters + source_delta,
            source_domain,
            backdoor_scope.trigger_feature_indices,
            backdoor_scope.trigger_value,
        ).value

    def _ablation_production_asr(self, cell: ScientificCell) -> MetricValue | None:
        backdoor_scope = self.source_backdoor_scope_for_cell(cell)
        if backdoor_scope is None:
            return None
        real_anchor = self.real_anchor(cell.master_seed)
        source_domain = source_domain_for_cell(self._primary_adapter, cell)
        if real_anchor is None or source_domain is None:
            return None
        if not self._last_committee_deltas:
            return None
        config = current_application_context().scientific_config
        committee = production_committee(
            self._last_committee_deltas,
            tuple(self._last_committee_deltas),
        )
        if not committee:
            return None
        if krum_committee_is_admissible(
            len(committee), config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ):
            selected = select_krum_update(
                committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
            )
            production_update = selected.update_vector
            publish_krum_synthesized_update(
                KrumSynthesizedUpdatePayload(
                    schema_version=PROTOCOL_EVIDENCE_SCHEMA_VERSION,
                    experiment=cell.experiment,
                    master_seed=cell.master_seed,
                    committee_size=len(committee),
                    maximum_byzantine_reproduction_rows=(
                        config.protocol.synthesis.maximum_byzantine_reproduction_rows
                    ),
                    selected_flat_parameters_identity=flat_parameters_identity(
                        real_anchor.flat_parameters + production_update
                    ),
                    selected_update_identity=flat_parameters_identity(production_update),
                )
            )
        else:
            production_update = next(iter(self._last_committee_deltas.values()))
        asr = compute_source_backdoor_asr(
            nbaiot_adapter(self._primary_adapter.prepared_root),
            real_anchor,
            real_anchor.flat_parameters + production_update,
            source_domain,
            backdoor_scope.trigger_feature_indices,
            backdoor_scope.trigger_value,
        )
        return asr.value

    def _ablation_compromised_reproducers(
        self, cell: ScientificCell, strategy: AblationReproducerStrategy
    ) -> frozenset[DomainId]:
        if strategy is AblationReproducerStrategy.NONE:
            return frozenset()
        selected = select_compromised_reproducers(
            reproducer_order_for_cell(self._primary_adapter, cell),
            frozenset(self._primary_adapter.domain_ids),
            1,
        )
        if selected is None:
            return frozenset()
        return frozenset(NBaiotDomain(domain) for domain in selected)

    def _ablation_opening_stage(self, cell: ScientificCell) -> OpeningStageOutcome | None:
        if cell.experiment != MECHANISM_ABLATION_NAME:
            return None
        variant = AblationVariant(cell.method)
        if variant in (
            AblationVariant.RAW_TARGET_F1_SCREEN_ONLY,
            AblationVariant.NO_MATCHED_CONTROL,
        ):
            return None
        scenario = ablation_scenario_for_condition(cell.condition)
        if scenario is None:
            return None
        return self._run_opening_stage(
            cell,
            ablation_scenario_episode(scenario),
            ablation_opening_mode(variant),
        )

    def _advance_protocol(
        self,
        cell: ScientificCell,
        evidence: PreparedEvidenceCounts,
        opening_resolved: BooleanValue = False,
        verifier_condition_override: VerifierCondition | None = None,
    ) -> AdmissionState:
        self._last_protocol_phase_durations = ProtocolPhaseDurations()
        self._last_committee_deltas = OrderedDict()
        self._last_synthesis_row_ids = ()
        self._last_production_contributor_ids = ()
        self._last_designated_compromised_ids = ()
        self._last_compromised_reproducers = frozenset()
        self._last_ablation_strategy = AblationReproducerStrategy.NONE
        self._last_reproduction_attempts = 0
        self._last_certified_attempts = 0
        self._last_verifier_report_count = 0
        self._last_verifier_abstention_count = 0
        if not opening_resolved:
            self._last_opening_stage = None
            stage = self._ablation_opening_stage(cell)
            if stage is None and (
                cell.method == RESOLVED_FEDSIRA_CORE_METHOD and self._resolved_core is not None
            ):
                stage = self._run_opening_stage(
                    cell,
                    core_opening_episode(cell.condition),
                    self._resolved_core.opening_mode,
                )
            if stage is not None:
                self._last_opening_stage = stage
                if stage.state is not AdmissionState.ADMISSION_OPEN:
                    return stage.state
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
                (
                    cell.experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME
                    and cell.method == SourceExclusionMethod.FULL_FEDSIRA
                )
                or cell.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME
                or (
                    cell.experiment == BYZANTINE_BOUND_VIOLATION_NAME
                    and verifier_condition_override is not None
                )
            )
            single_verifier_active = False
        required_row_count = row_requirement(cell, self._resolved_core)
        screened_source_delta = (
            self._last_opening_stage.source_delta if self._last_opening_stage is not None else None
        )
        source_backdoor_scope = self.source_backdoor_scope_for_cell(cell)
        source_delta = (
            screened_source_delta
            if screened_source_delta is not None
            else train_source_candidate_delta(
                nbaiot_adapter(self._primary_adapter.prepared_root),
                cell.master_seed,
                real_anchor,
                source_domain,
                backdoor_scope=source_backdoor_scope,
            )
            if source_domain is not None
            and (
                no_origin_exclusion_active
                or byzantine_reproducer_copies_source_active
                or source_backdoor_scope is not None
            )
            else None
        )
        heterogeneity_scope = self.heterogeneity_scope_for_cell(cell)
        verifier_robustness_condition = verifier_condition_override or (
            VerifierCondition(cell.condition)
            if cell.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME
            else None
        )
        if verifier_condition_override is not None:
            external_verification_active = True
            single_verifier_active = False
        backdoor_scope = self.backdoor_scope_for_cell(cell)
        ablation_scenario = (
            ablation_scenario_for_condition(cell.condition)
            if cell.experiment == MECHANISM_ABLATION_NAME
            else None
        )
        ablation_strategy = (
            ablation_reproducer_strategy(ablation_scenario)
            if ablation_scenario is not None
            else AblationReproducerStrategy.NONE
        )
        compromised_reproducers = self._ablation_compromised_reproducers(cell, ablation_strategy)
        if verifier_robustness_condition in (
            VerifierCondition.ONE_FALSE_POSITIVE,
            VerifierCondition.TWO_FALSE_POSITIVES,
        ):
            model_replacement_cell = replace(
                cell, condition=ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR
            )
            backdoor_scope = self.backdoor_scope_for_cell(model_replacement_cell)
            selected_reproducers = select_compromised_reproducers(
                reproducer_order_for_cell(self._primary_adapter, cell),
                model_replacement_attack_feasible_domains(self._primary_adapter),
                1,
            )
            if selected_reproducers is None or backdoor_scope is None:
                raise ValueError(
                    "compromised-verifier fixture lacks its declared model-replacement row"
                )
            compromised_reproducers = frozenset(
                NBaiotDomain(domain) for domain in selected_reproducers
            )
            ablation_strategy = AblationReproducerStrategy.MODEL_REPLACEMENT
        if cell.condition in SOURCE_COPY_CONDITIONS and not compromised_reproducers:
            copy_count = compromised_reproducer_count(cell.condition)
            reproduction_method = cell.method in (
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
                BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
                BaselineIdentity.CANDIDATE_FREE_FULL_PATH,
                RESOLVED_FEDSIRA_CORE_METHOD,
                CoreMethodIdentity.FULL_PLURALITY_PATH,
                SourceExclusionMethod.FULL_FEDSIRA,
            )
            if (
                cell.condition == PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT
                and not reproduction_method
            ):
                copy_count = 0
            if copy_count and source_domain is not None:
                if source_delta is None:
                    copy_scope = self._configured_backdoor_scope(
                        cell,
                        config.attacks_and_boundaries.hidden_source_backdoor.confirmatory_poison_fraction,
                    )
                    if copy_scope is not None:
                        source_delta = train_source_candidate_delta(
                            nbaiot_adapter(self._primary_adapter.prepared_root),
                            cell.master_seed,
                            real_anchor,
                            source_domain,
                            backdoor_scope=copy_scope,
                        )
                selected_copies = select_compromised_reproducers(
                    reproducer_order_for_cell(self._primary_adapter, cell),
                    model_replacement_attack_feasible_domains(self._primary_adapter),
                    copy_count,
                )
                if selected_copies is None:
                    raise ValueError("declared source-copy count exceeds attack-feasible domains")
                compromised_reproducers = frozenset(
                    NBaiotDomain(domain) for domain in selected_copies
                )
        if cell.condition == ExternalVerificationCondition.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER:
            ablation_strategy = AblationReproducerStrategy.VERIFIER_AWARE
            if backdoor_scope is None:
                backdoor_scope = self._configured_backdoor_scope(
                    cell,
                    config.attacks_and_boundaries.hidden_source_backdoor.confirmatory_poison_fraction,
                )
            if not compromised_reproducers:
                selected_verifier_aware = select_compromised_reproducers(
                    reproducer_order_for_cell(self._primary_adapter, cell),
                    model_replacement_attack_feasible_domains(self._primary_adapter),
                    compromised_reproducer_count(cell.condition),
                )
                if selected_verifier_aware is None or backdoor_scope is None:
                    raise ValueError(
                        "verifier-aware reproducer fixture lacks its declared attack row"
                    )
                compromised_reproducers = frozenset(
                    NBaiotDomain(domain) for domain in selected_verifier_aware
                )
        self._last_compromised_reproducers = compromised_reproducers
        self._last_ablation_strategy = ablation_strategy
        if single_verifier_active:
            reproduction_timer = ElapsedTimer()
            progression_state, attempts, commitment_hashes, updates = single_verifier_progression(
                cell,
                source_domain,
                self._primary_adapter,
                real_anchor,
                heterogeneity_scope,
                compromised_reproducers,
                source_delta,
            )
            self._last_protocol_phase_durations = ProtocolPhaseDurations(
                reproduce_seconds=reproduction_timer.elapsed_seconds()
            )
            self._last_synthesis_row_ids = tuple(updates)
        else:
            reproduction_timer = ElapsedTimer()
            progression_state, attempts, commitment_hashes, updates = reproduction_progression(
                cell,
                evidence,
                external_verification_active,
                required_row_count,
                compromised_reproducers,
                self._primary_adapter,
                real_anchor,
                strategy=ablation_strategy,
                include_source_as_first_reproducer=no_origin_exclusion_active,
                heterogeneity_scope=heterogeneity_scope,
                backdoor_scope=backdoor_scope,
                source_delta=source_delta,
            )
            self._last_protocol_phase_durations = ProtocolPhaseDurations(
                reproduce_seconds=reproduction_timer.elapsed_seconds()
            )
            self._last_committee_deltas = updates
            self._last_synthesis_row_ids = tuple(updates)
            self._last_reproduction_attempts = len(attempts)
            if progression_state is AdmissionState.VERIFICATION_PENDING:
                verification_timer = ElapsedTimer()
                certified_positive_report_count = 0
                certified_attempts = 0
                verifier_report_count = 0
                verifier_abstention_count = 0
                for attempt, commitment_hash in zip(attempts, commitment_hashes, strict=False):
                    if not attempt.was_trained:
                        continue
                    attempt_domain = NBaiotDomain(attempt.domain)
                    if attempt_domain not in updates:
                        continue
                    candidate_flat = real_anchor.flat_parameters + updates[attempt_domain]
                    compromised_verifiers: frozenset[DomainId] = frozenset()
                    if same_context_verification_active:
                        panel = self._same_context_verifier_panel(source_domain, attempt_domain)
                    elif verifier_robustness_condition is not None:
                        eligible_verifiers = tuple(
                            domain
                            for domain in self._primary_adapter.domain_ids
                            if verifier_is_eligible(domain, source_domain, attempt.domain)
                        )
                        verifier_order = byzantine_selection_order(
                            eligible_verifiers,
                            derive_uint32(
                                SeedDerivationLabel.BYZANTINE_VERIFIER_SELECTION,
                                cell.master_seed,
                            ),
                        )
                        compromised_verifier_total = compromised_verifier_count(
                            verifier_robustness_condition
                        )
                        compromised_verifiers = select_compromised_verifiers(
                            verifier_order, compromised_verifier_total
                        )
                        if cell.method == VerifierProfile.DETERMINISTIC_BOUND or (
                            cell.experiment == BYZANTINE_BOUND_VIOLATION_NAME
                            and verifier_condition_override is not None
                        ):
                            panel = construct_above_bound_panel(
                                verifier_order[:compromised_verifier_total],
                                tuple(
                                    domain
                                    for domain in verifier_order
                                    if domain not in compromised_verifiers
                                ),
                                config.protocol.verification.panel_size,
                            )
                        else:
                            panel = diagnostic_committee_panel(
                                eligible_verifiers,
                                committee_draw_namespace_seed=derive_uint32(
                                    SeedDerivationLabel.VERIFIER_ROW_SEED,
                                    cell.master_seed,
                                    commitment_hash,
                                ),
                                panel_size=config.protocol.verification.panel_size,
                            )
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
                    malicious_row = attempt_domain in compromised_reproducers
                    is_false_negative = verifier_robustness_condition in (
                        VerifierCondition.ONE_FALSE_NEGATIVE,
                        VerifierCondition.TWO_FALSE_NEGATIVES,
                    )
                    is_false_positive = verifier_robustness_condition in (
                        VerifierCondition.ONE_FALSE_POSITIVE,
                        VerifierCondition.TWO_FALSE_POSITIVES,
                    )
                    reports = tuple(
                        resolve_byzantine_verifier_vote(ByzantineVerifierBehavior.FALSE_NEGATIVE)
                        if verifier_robustness_condition is not None
                        and verifier_domain in compromised_verifiers
                        and is_false_negative
                        else resolve_byzantine_verifier_vote(
                            ByzantineVerifierBehavior.FALSE_POSITIVE
                        )
                        if verifier_robustness_condition is not None
                        and verifier_domain in compromised_verifiers
                        and is_false_positive
                        and malicious_row
                        else honest_verifier_report(
                            self._primary_adapter,
                            real_anchor,
                            candidate_flat,
                            NBaiotDomain(verifier_domain),
                            heterogeneity_scope,
                        )
                        for verifier_domain in panel
                    )
                    certificate_is_valid = reproduction_row_is_certified(
                        reports,
                        panel_size=config.protocol.verification.panel_size,
                        required_positive_reports=config.protocol.verification.required_positive_reports,
                    )
                    verifier_report_count += len(reports)
                    verifier_abstention_count += sum(
                        1 for report in reports if report is TernaryOutcome.ABSTAIN
                    )
                    record_verification_evidence(
                        cell=cell,
                        reproducer_domain=attempt.domain,
                        commitment_identity=commitment_hash,
                        panel=panel,
                        reports=reports,
                        certificate_is_valid=certificate_is_valid,
                        certified_row_count=certified_attempts + int(certificate_is_valid),
                        required_row_count=required_row_count,
                    )
                    if certificate_is_valid:
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
                self._last_certified_attempts = certified_attempts
                self._last_verifier_report_count = verifier_report_count
                self._last_verifier_abstention_count = verifier_abstention_count
                self._last_protocol_phase_durations = (
                    self._last_protocol_phase_durations.with_verify_seconds(
                        verification_timer.elapsed_seconds()
                    )
                )
        if (
            progression_state is AdmissionState.SYNTHESIS_PENDING
            and verifier_robustness_condition is not None
            and cell.method is VerifierProfile.RANDOM_COMMITTEE_DIAGNOSTIC
        ):
            eligible_verifier_count = sum(
                1
                for domain in self._primary_adapter.domain_ids
                if verifier_is_eligible(domain, source_domain, attempts[0].domain)
            )
            contamination_probability = diagnostic_at_least_two_byzantine_probability(
                eligible_verifier_count,
                compromised_verifier_count(verifier_robustness_condition),
                config.protocol.verification.panel_size,
            )
            diagnostic_profile = config.protocol.diagnostic_random_verifier_profile
            if contamination_probability > diagnostic_profile.tolerated_contamination_risk:
                progression_state = AdmissionState.DORMANT
        if progression_state is AdmissionState.SYNTHESIS_PENDING:
            synthesis_timer = ElapsedTimer()
            plurality_synthesis_active = (
                cell.experiment == SINGLE_REPRODUCTION_NECESSITY_NAME
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
                or byzantine_reproducer_copies_source_active
                or cell.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME
                or verifier_condition_override is not None
            )
            (
                state,
                self._pending_real_report,
                production_checkpoint,
                krum_selected_update,
                self._last_production_contributor_ids,
            ) = final_gate_decision(
                evidence,
                source_domain,
                tuple(NBaiotDomain(attempt.domain) for attempt in attempts),
                is_plurality_active=plurality_synthesis_active,
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
            record_production_evidence(
                cell=cell,
                production_checkpoint=production_checkpoint,
                krum_selected_update=krum_selected_update,
                plurality_synthesis_active=plurality_synthesis_active,
                reproduction_row_count=len(attempts),
                decision=state,
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

    def _ancestry_malicious_admission(
        self,
        state: AdmissionState,
        fixture_present: BooleanValue,
        compromised_ids: tuple[DomainId, ...],
    ) -> MetricValue | None:
        return malicious_admission_from_ancestry(
            state is AdmissionState.ADMITTED,
            fixture_present,
            production_depends_on_compromised_contributor(
                self._last_production_contributor_ids,
                compromised_ids,
            ),
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
        malicious_value = self._ancestry_malicious_admission(
            state,
            condition is source_copy_condition,
            tuple(self._last_compromised_reproducers),
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
        source_domain = source_domain_for_cell(self._primary_adapter, cell)
        if method in (full_fedsira, SourceExclusionMethod.ONE_INDEPENDENT_RETRAIN):
            state = self._advance_protocol(cell, evidence)
            require_source_identity_excluded_from_synthesis(
                self._last_synthesis_row_ids,
                source_domain,
            )
        elif method == SourceExclusionMethod.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION:
            state = self.client_review_outcome(cell)
            if source_domain is not None:
                self._last_production_contributor_ids = (source_domain,)
        elif method == SourceExclusionMethod.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN:
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self.client_review_outcome(cell)
            )
            state = (
                self._advance_protocol(cell, evidence) if discard_source else AdmissionState.DORMANT
            )
        elif method == SourceExclusionMethod.SOURCE_UPDATE_SANITIZATION_REFERENCE:
            state = self._source_update_sanitization_outcome(cell, evidence)
        elif method == SourceExclusionMethod.RECOVERY_AFTER_SOURCE_ADMISSION:
            state = self._recovery_after_source_admission_outcome(cell, evidence)
        else:
            state = self._advance_protocol(cell, evidence)
        extra: list[MetricObservation] = []
        source_backdoor_asr: MetricResult | None = None
        if cell.condition == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT:
            real_anchor = self.real_anchor(cell.master_seed)
            source_domain = source_domain_for_cell(self._primary_adapter, cell)
            backdoor_scope = self.source_backdoor_scope_for_cell(cell)
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
        compromised_source = (source_domain,) if source_domain is not None else ()
        malicious_admission = self._ancestry_malicious_admission(
            state,
            cell.condition == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
            (*compromised_source, *self._last_compromised_reproducers),
        )
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
        malicious_admission = self._ancestry_malicious_admission(
            state,
            has_malicious,
            tuple(self._last_compromised_reproducers),
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
            return (state, (*metrics, *self._scenario_malicious_admission(cell, state)))
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
        if method in CALIBRATED_BASELINE_METHODS:
            calibration_anchor = self.real_anchor(cell.master_seed)
            if calibration_anchor is not None:
                record_baseline_calibration(cell, calibration_anchor)
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
            required_reviewer_count, _required_positive_reviews = review_panel_requirements(
                ReviewPanelProfile.CLIENT_REVIEW
            )
            validate_client_review_reviewer_count(required_reviewer_count)
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
        return (state, (*metrics, *self._scenario_malicious_admission(cell, state)))

    def _scenario_malicious_admission(
        self, cell: ScientificCell, state: AdmissionState
    ) -> tuple[MetricObservation, ...]:
        source_domain = source_domain_for_cell(self._primary_adapter, cell)
        fixture = cell.condition in (
            PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
            PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        )
        ordinary_client_attack = (
            cell.method in _ORDINARY_CLIENT_ATTACK_METHODS
            and cell.condition
            in (
                PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT,
                BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
            )
        )
        fixture = ordinary_client_attack or cell.condition in (
            PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
            PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        )
        compromised_ids = list(self._last_compromised_reproducers)
        source_is_compromised_authority = (
            source_domain is not None
            and not ordinary_client_attack
            and cell.condition
            in (
                PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
                ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
            )
        )
        if source_is_compromised_authority and source_domain is not None:
            compromised_ids.insert(0, source_domain)
        for designated in self._last_designated_compromised_ids:
            if designated not in compromised_ids:
                compromised_ids.append(designated)
        return (
            (
                ComparisonMetric.MALICIOUS_ADMISSION,
                self._ancestry_malicious_admission(state, fixture, tuple(compromised_ids)),
            ),
        )

    def _execute_reproducer_robustness_cell(
        self,
        cell: ScientificCell,
        evidence: PreparedEvidenceCounts,
        condition_override: ReproducerCondition | None = None,
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        condition = condition_override or ReproducerCondition(cell.condition)
        compromised_count = compromised_reproducer_count(condition)
        real_anchor = self.real_anchor(cell.master_seed)
        source_domain = source_domain_for_cell(self._primary_adapter, cell)
        source_delta = None
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
        if compromised_count == 0:
            state = self._advance_protocol(cell, evidence)
        else:
            attack_feasible_domains = frozenset(self._primary_adapter.domain_ids)
            if condition in (
                ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
                ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
                ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
                ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
            ):
                attack_feasible_domains = model_replacement_attack_feasible_domains(
                    self._primary_adapter
                )
            selected = select_compromised_reproducers(
                reproducer_order_for_cell(self._primary_adapter, cell),
                attack_feasible_domains,
                compromised_count,
            )
            if selected is None:
                raise ValueError(
                    "planned compromised-reproducer count exceeds attack-feasible domains"
                )
            compromised_reproducers = frozenset(NBaiotDomain(domain) for domain in selected)
            reproducer_strategy = (
                AblationReproducerStrategy.MODEL_REPLACEMENT
                if condition
                in (
                    ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
                    ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
                )
                else AblationReproducerStrategy.VERIFIER_AWARE
                if condition
                in (
                    ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
                    ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
                )
                else AblationReproducerStrategy.NONE
            )
            self._last_compromised_reproducers = compromised_reproducers
            self._last_ablation_strategy = reproducer_strategy
            required_row_count = row_requirement(cell)
            progression_state, attempts, _commitment_hashes, updates = reproduction_progression(
                cell,
                evidence,
                False,
                required_row_count,
                compromised_reproducers,
                self._primary_adapter,
                real_anchor,
                strategy=reproducer_strategy,
                backdoor_scope=self.backdoor_scope_for_cell(replace(cell, condition=condition)),
                source_delta=source_delta,
            )
            self._last_committee_deltas = updates
            self._last_reproduction_attempts = len(attempts)
            if (
                progression_state is AdmissionState.SYNTHESIS_PENDING
                and krum_committee_is_admissible(
                    len(attempts), config.protocol.synthesis.maximum_byzantine_reproduction_rows
                )
            ):
                (
                    state,
                    self._pending_real_report,
                    production_checkpoint,
                    krum_selected_update,
                    self._last_production_contributor_ids,
                ) = final_gate_decision(
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
                record_production_evidence(
                    cell=cell,
                    production_checkpoint=production_checkpoint,
                    krum_selected_update=krum_selected_update,
                    plurality_synthesis_active=True,
                    reproduction_row_count=len(attempts),
                    decision=state,
                )
            else:
                state = AdmissionState.DORMANT
                self._pending_real_report = None
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
        malicious_admission: MetricValue | None = (
            float(
                state is AdmissionState.ADMITTED and self._ablation_production_is_compromised(cell)
            )
            if compromised_count
            else None
        )
        return (state, (*metrics, (ComparisonMetric.MALICIOUS_ADMISSION, malicious_admission)))

    def _execute_verifier_robustness_cell(
        self,
        cell: ScientificCell,
        evidence: PreparedEvidenceCounts,
        condition_override: VerifierCondition | None = None,
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        state = self._advance_protocol(
            cell, evidence, verifier_condition_override=condition_override
        )
        metrics = metrics_from_state(
            state, self._pending_real_report, legitimate_admission_eligible=True
        )
        condition = condition_override or VerifierCondition(cell.condition)
        malicious_case = condition in (
            VerifierCondition.ONE_FALSE_POSITIVE,
            VerifierCondition.TWO_FALSE_POSITIVES,
        )
        malicious_admission: MetricValue | None = (
            float(
                state is AdmissionState.ADMITTED and self._ablation_production_is_compromised(cell)
            )
            if malicious_case
            else None
        )
        certified_yield: MetricValue | None = (
            self._last_certified_attempts / self._last_reproduction_attempts
            if self._last_reproduction_attempts
            else None
        )
        verifier_abstention_rate: MetricValue | None = (
            self._last_verifier_abstention_count / self._last_verifier_report_count
            if self._last_verifier_report_count
            else None
        )
        metrics = observations_with_replacements(
            metrics,
            (
                (DescriptiveScientificMetric.CERTIFIED_ROW_YIELD, certified_yield),
                (DescriptiveScientificMetric.VERIFIER_ABSTENTION_RATE, verifier_abstention_rate),
            ),
        )
        return (state, (*metrics, (ComparisonMetric.MALICIOUS_ADMISSION, malicious_admission)))

    def _execute_byzantine_bound_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        condition = BoundCondition(cell.condition)
        if condition is BoundCondition.ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND:
            return self._execute_reproducer_robustness_cell(
                cell,
                evidence,
                ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
            )
        if condition is BoundCondition.TWO_BYZANTINE_REPRODUCERS_ABOVE_BOUND:
            return self._execute_reproducer_robustness_cell(
                cell,
                evidence,
                ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
            )
        if condition is BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND:
            if cell.method == BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM:
                return self._execute_reproducer_robustness_cell(
                    cell,
                    evidence,
                    ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
                )
            return self._execute_verifier_robustness_cell(
                cell, evidence, VerifierCondition.ONE_FALSE_POSITIVE
            )
        if cell.method == BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM:
            return self._execute_reproducer_robustness_cell(
                cell,
                evidence,
                ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
            )
        return self._execute_verifier_robustness_cell(
            cell, evidence, VerifierCondition.TWO_FALSE_POSITIVES
        )

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
        candidate_cycles = measurement_cycles(config.protocol.resource_horizon)
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
            return (
                state,
                (
                    *metrics,
                    (MetricObservationKey.EVIDENCE_ARRIVAL_CYCLE, None),
                    permanent_singleton_admission(state, holder_counts),
                ),
            )
        try:
            validate_no_safety_completion_before_tau_k(0, tau_k)
        except ValueError:
            state = resume_dormant_admission(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = metrics_from_state(
                state, self._pending_real_report, legitimate_admission_eligible=True
            )
            return (
                state,
                (
                    *metrics,
                    (MetricObservationKey.EVIDENCE_ARRIVAL_CYCLE, float(tau_k)),
                    permanent_singleton_admission(state, holder_counts),
                ),
            )
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
                (MetricObservationKey.EVIDENCE_ARRIVAL_CYCLE, float(tau_k)),
                (
                    "logical-information-arrival-cycles",
                    float(delay_decomposition.logical_information_arrival_cycles),
                ),
                (
                    DescriptiveScientificMetric.T_EVIDENCE,
                    float(t_evidence) if t_evidence is not None else None,
                ),
                ("first-holder-cycle", float(first_holder) if first_holder is not None else None),
                (DescriptiveScientificMetric.WALL_CLOCK_SECONDS, None),
                permanent_singleton_admission(state, holder_counts),
            ),
        )

    def _execute_admission_delay_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        schedule = EvidenceArrivalSchedule(cell.condition)
        candidate_cycles = measurement_cycles(config.protocol.resource_horizon)
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
                (
                    MetricObservationKey.EVIDENCE_ARRIVAL_CYCLE,
                    float(tau_k) if tau_k is not None else None,
                ),
                (
                    DescriptiveScientificMetric.T_EVIDENCE,
                    float(t_evidence) if t_evidence is not None else None,
                ),
                (DelayPhaseMetric.ASSIGNMENT_SECONDS, phase_durations.assignment_seconds),
                (DelayPhaseMetric.REPRODUCE_SECONDS, phase_durations.reproduce_seconds),
                (DelayPhaseMetric.VERIFY_SECONDS, phase_durations.verify_seconds),
                (DelayPhaseMetric.SYNTHESIZE_SECONDS, phase_durations.synthesize_seconds),
                (
                    DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
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
            tensor_payload = numpy.asarray(flat_parameters).tobytes()
            parameter_shape = (flat_parameters.numel(),)
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
            for message_type, count in _efficiency_message_counts():
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
        diagnostic_root = current_repository_root() / experiment_repetition_telemetry_root(
            cell.experiment,
            cell.method,
            cell.master_seed,
            cell.repetition,
        )
        diagnostic_root.mkdir(parents=True, exist_ok=True)
        (diagnostic_root / WorkspaceFileToken.TIMING_OBSERVATION_JSON).write_text(
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
                (DescriptiveScientificMetric.COMMUNICATION_BYTES, float(bytes_total)),
                (DescriptiveScientificMetric.MODEL_TRANSMISSIONS, float(transmissions)),
                (
                    DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
                    observation.wall_clock_seconds,
                ),
                (DescriptiveScientificMetric.GPU_SECONDS, observation.gpu_seconds),
                (
                    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
                    float(observation.peak_gpu_memory_bytes),
                ),
                (
                    DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES,
                    float(observation.peak_host_rss_bytes),
                ),
                (DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES, float(storage_bytes)),
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
    CellHandlerRegistration(
        experiment=LEAVE_FAULT_CERTIFICATE_VALIDATION_NAME,
        handler="_execute_leave_fault_certificate_cell",
    ),
)


def cell_handler_registration(experiment: ExperimentName) -> CellHandlerName | None:
    for registration in CELL_HANDLER_REGISTRATIONS:
        if registration.experiment == experiment:
            return registration.handler
    return None


def validate_cell_handler_registration() -> None:
    catalog = set(CATALOG_EXPERIMENT_NAMES)
    mapped = {registration.experiment for registration in CELL_HANDLER_REGISTRATIONS}
    missing = catalog - mapped
    if missing:
        raise ValueError(f"catalog experiments without a cell handler: {sorted(missing)}")
    unknown = mapped - catalog
    if unknown:
        raise ValueError(f"cell handlers for experiments outside the catalog: {sorted(unknown)}")
    missing_methods = {
        registration.handler
        for registration in CELL_HANDLER_REGISTRATIONS
        if not callable(getattr(ProtocolCellExecutor, registration.handler, None))
    }
    if missing_methods:
        raise ValueError(
            f"registered experiment handlers are missing methods: {sorted(missing_methods)}"
        )


class ProtocolCellExecutor(CellExecutor, ProtocolBaselineOutcomes, ProtocolCellDispatch):
    def __init__(
        self,
        primary_prepared_root: Path | None = None,
        secondary_prepared_root: Path | None = None,
        resolved_core: ResolvedCore | None = None,
    ) -> None:
        validate_cell_handler_registration()
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
        self._current_cell: ScientificCell | None = None
        self._last_protocol_phase_durations = ProtocolPhaseDurations()
        self._last_production_contributor_ids = ()
        self._last_designated_compromised_ids = ()
        self._last_compromised_reproducers = frozenset()

    def _model_replacement_training_args(
        self, cell: ScientificCell
    ) -> tuple[DomainId | None, BackdoorScope | None, DeltaScale | None]:
        model_replacement_condition = cell.condition in (
            PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT,
            BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
        )
        if model_replacement_condition and cell.method in _ORDINARY_CLIENT_ATTACK_METHODS:
            source_domain = source_domain_for_cell(self._primary_adapter, cell)
            feasible = model_replacement_attack_feasible_domains(self._primary_adapter)
            eligible = tuple(
                domain
                for domain in non_source_domains(self._primary_adapter, source_domain)
                if domain in feasible
            )
            selected = select_compromised_reproducers(
                byzantine_selection_order(
                    eligible,
                    namespace_seed(cell.master_seed, SeedDerivationLabel.BYZANTINE_SELECTION),
                ),
                feasible,
                compromised_reproducer_count(
                    PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT
                ),
            )
            if selected is None:
                raise ValueError("ordinary-FL model replacement lacks an attack-feasible client")
            config = current_application_context().scientific_config
            scope = self._configured_backdoor_scope(
                cell,
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.poison_fraction,
            )
            if scope is None:
                raise ValueError("ordinary-FL model replacement lacks its declared poisoned view")
            return (
                selected[0],
                scope,
                config.attacks_and_boundaries.byzantine_reproduction.model_replacement.delta_scale,
            )
        source_backdoor = cell.condition == PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT
        if source_backdoor and cell.method in _SOURCE_POISON_AVERAGING_METHODS:
            source_domain = source_domain_for_cell(self._primary_adapter, cell)
            scope = self.source_backdoor_scope_for_cell(cell)
            if source_domain is None or scope is None:
                raise ValueError("useful backdoored source lacks its declared source update")
            return source_domain, scope, None
        return None, None, None

    def real_anchor(self, master_seed: MasterSeed) -> RealAnchor | None:
        if master_seed not in self.real_anchor_cache:
            anchor = (
                train_anchor(self._primary_adapter, master_seed)
                if self._primary_adapter.evidence_available()
                else None
            )
            if anchor is not None:
                publish_anchor_checkpoints(
                    self._primary_adapter.dataset,
                    master_seed,
                    anchor,
                    self._primary_adapter.class_tokens,
                )
            self.real_anchor_cache[master_seed] = anchor
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
            Role.POST_REFERENCE_REPLAY.name,
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
        benign_far_increase = benign_false_alarm_rate_increase(
            candidate_screen.benign_far, anchor_screen.benign_far
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
            Role.POST_REFERENCE_REPLAY.name,
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
        benign_far_increase = benign_false_alarm_rate_increase(
            candidate_screen.benign_far, anchor_screen.benign_far
        )
        return capability_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def _configured_backdoor_scope(
        self, cell: ScientificCell, poison_fraction: Probability
    ) -> BackdoorScope | None:
        config = current_application_context().scientific_config
        real_feature_names = prepared_feature_names(self._primary_adapter.prepared_root)
        if real_feature_names is None:
            return None
        trigger_indices = tuple(real_feature_names.index(name) for name in NBAIOT_TRIGGER_FEATURES)
        return BackdoorScope(
            attack_generation_seed=derive_uint32(
                SeedDerivationLabel.ATTACK_GENERATION_SEED, cell.master_seed
            ),
            poison_fraction=poison_fraction,
            trigger_feature_indices=trigger_indices,
            trigger_value=config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization,
        )

    def source_backdoor_scope_for_cell(self, cell: ScientificCell) -> BackdoorScope | None:
        if cell.condition != ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT:
            return None
        config = current_application_context().scientific_config
        poison_fraction = (
            config.attacks_and_boundaries.hidden_source_backdoor.confirmatory_poison_fraction
        )
        validate_declared_source_backdoor_poison_fraction(poison_fraction)
        return self._configured_backdoor_scope(cell, poison_fraction)

    def backdoor_scope_for_cell(self, cell: ScientificCell) -> BackdoorScope | None:
        source_scope = self.source_backdoor_scope_for_cell(cell)
        if source_scope is not None:
            return source_scope
        replacement_conditions = (
            ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
            ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
            ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
            ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
        )
        ablation_scenario = ablation_scenario_for_condition(cell.condition)
        ablation_strategy = (
            ablation_reproducer_strategy(ablation_scenario)
            if ablation_scenario is not None
            else AblationReproducerStrategy.NONE
        )
        if cell.condition not in replacement_conditions and ablation_strategy not in (
            AblationReproducerStrategy.MODEL_REPLACEMENT,
            AblationReproducerStrategy.VERIFIER_AWARE,
        ):
            return None
        config = current_application_context().scientific_config
        return self._configured_backdoor_scope(
            cell,
            config.attacks_and_boundaries.byzantine_reproduction.model_replacement.poison_fraction,
        )

    def heterogeneity_scope_for_cell(self, cell: ScientificCell) -> HeterogeneityScope | None:
        config = current_application_context().scientific_config
        shift_magnitude = feature_shift_magnitude(cell.condition)
        if shift_magnitude is None:
            return None
        real_feature_names = prepared_feature_names(self._primary_adapter.prepared_root)
        if real_feature_names is None:
            return None
        heterogeneity_seed = derive_uint32(SeedDerivationLabel.HETEROGENEITY_SEED, cell.master_seed)
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
        self._last_production_contributor_ids = ()
        self._last_designated_compromised_ids = ()
        self._last_compromised_reproducers = frozenset()
        dataset = experiment_by_name(cell.experiment).dataset
        if dataset is DatasetId.CICIOT2023:
            prepared_root = self._secondary_prepared_root
            target_class_token = CICIOT2023_TARGET_LABEL
        else:
            prepared_root = self._primary_adapter.prepared_root
            target_class_token = self._primary_adapter.target_class_token
        if cell.experiment in (
            PROTOCOL_INVARIANT_VALIDATION_NAME,
            LEAVE_FAULT_CERTIFICATE_VALIDATION_NAME,
        ):
            evidence = PreparedEvidenceCounts(
                screen_target_count=0,
                reproduction_target_count=0,
                reproduction_supported_count=0,
                final_gate_adequate_domain_count=0,
            )
        else:
            try:
                evidence = load_prepared_evidence_counts(prepared_root, target_class_token)
            except PreparedEvidenceProvenanceError as error:
                return invalid_prepared_evidence_outcome(
                    cell, FailureClass.INVARIANT_VIOLATION, str(error)
                )
            if evidence is None:
                return invalid_prepared_evidence_outcome(
                    cell,
                    FailureClass.EVIDENCE_INSUFFICIENT,
                    "prepared evidence is not materialized for this cell; "
                    "run fedsira preprocess first",
                )
        with capture_model_score_artifacts() as score_artifacts:
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
                    scoring_artifact_ids=tuple(sorted(set(score_artifacts))),
                )
        trajectory = (
            self.evidence_scarcity_trajectory(metrics, _state)
            if cell.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME
            else ()
        )
        return CellExecutionOutcome(
            cell=cell,
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=metrics,
            state_trajectory=trajectory,
            scoring_artifact_ids=tuple(sorted(set(score_artifacts))),
        )

    def evidence_scarcity_trajectory(
        self,
        metrics: tuple[MetricObservation, ...],
        terminal_state: AdmissionState,
    ) -> tuple[AdmissionStateObservation, ...]:
        arrival_cycle = next(
            (
                value
                for name, value in metrics
                if name == MetricObservationKey.EVIDENCE_ARRIVAL_CYCLE
            ),
            None,
        )
        scientific_config = current_application_context().scientific_config
        horizon = scientific_config.protocol.resource_horizon.maximum_logical_evidence_cycles
        return tuple(
            AdmissionStateObservation(
                cycle=cycle,
                state=apply_logical_cycle_expiry(
                    AdmissionState.DORMANT
                    if arrival_cycle is None or cycle < arrival_cycle
                    else AdmissionState.VERIFICATION_PENDING
                    if cycle == arrival_cycle
                    else terminal_state,
                    cycle,
                    scientific_config.protocol.resource_horizon,
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

    def _execute_leave_fault_certificate_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        del evidence
        return execute_leave_fault_validation_cell(cell)

    def _execute_cell_protocol(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[AdmissionState, tuple[MetricObservation, ...]]:
        handler_name = cell_handler_registration(cell.experiment)
        if handler_name is None:
            raise ValueError(f"no registered cell handler for experiment {cell.experiment}")
        handler = cast(CellHandler, getattr(self, handler_name))
        self._current_cell = cell
        try:
            return handler(cell, evidence)
        finally:
            self._current_cell = None

    def _final_gate_outcome(
        self,
        evidence: PreparedEvidenceCounts,
        source_domain: DomainId | None,
        real_anchor: RealAnchor,
        production_checkpoint: torch.Tensor,
    ) -> AdmissionState:
        cell = self._current_cell
        if cell is None:
            raise ValueError("baseline final gate requires an active scientific cell")
        publish_trained_update(
            ArtifactFamily.BASELINE_CHECKPOINT,
            self._primary_adapter.dataset,
            cell.master_seed,
            f"baseline-{cell.method}-{cell.condition}",
            real_anchor.dataset_manifest_hash,
            production_checkpoint - real_anchor.flat_parameters,
            real_anchor.input_width,
            real_anchor.output_width,
            self._primary_adapter.class_tokens,
        )
        state = ProtocolBaselineOutcomes._final_gate_outcome(
            self, evidence, source_domain, real_anchor, production_checkpoint
        )
        record_production_evidence(
            cell=cell,
            production_checkpoint=production_checkpoint,
            krum_selected_update=None,
            plurality_synthesis_active=False,
            reproduction_row_count=0,
            decision=state,
        )
        return state


def single_verifier_progression(
    cell: ScientificCell,
    source_domain: DomainId | None,
    adapter: DatasetAdapter,
    anchor: RealAnchor | None,
    heterogeneity_scope: HeterogeneityScope | None = None,
    compromised_reproducers: frozenset[DomainId] = frozenset(),
    source_delta: torch.Tensor | None = None,
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
        if domain != source_domain and domain_is_reproduction_adequate(adapter, domain)
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
        if (
            next_domain in compromised_reproducers
            and source_delta is not None
            and cell.condition in SOURCE_COPY_CONDITIONS
        ):
            update = reproduction_update_vector(
                anchor.flat_parameters, anchor.flat_parameters + source_delta
            )
        else:
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
