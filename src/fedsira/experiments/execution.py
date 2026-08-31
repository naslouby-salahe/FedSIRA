from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

import pandas
import torch

from fedsira.analysis.comparisons import (
    ComparisonDefinition,
    ComparisonEffectScale,
    ComparisonFamilyResult,
    ComparisonMetric,
    ComparisonOrientation,
    ComparisonReferenceKind,
    ComparisonResult,
    ComparisonState,
    apply_holm_adjustment,
    build_comparison_registry,
    evaluate_comparison,
)
from fedsira.artifacts.paths import prepared_evidence_root
from fedsira.attacks.reproduction import (
    scale_model_replacement_delta,
    select_model_replacement_carrier_rows,
    source_copy_update,
    verifier_aware_training_step,
)
from fedsira.attacks.source_backdoor import (
    apply_trigger_transform,
    relabel_triggered_rows_as_benign,
    select_source_backdoor_poison_rows,
)
from fedsira.attacks.verification import resolve_byzantine_verifier_vote
from fedsira.baselines.calibration import (
    DomainFeatureMean,
    clip_source_update,
    cosine_distance_matrix,
    density_cluster_labels,
    l2_normalize,
    parameter_similarity_certification_row_results,
    reconstruction_error,
    reconstruction_filter_accepts,
    reconstruction_filter_calibration_error_count,
    reconstruction_filter_reweight,
    reconstruction_rejection_threshold,
    recovery_alarm_threshold,
    recovery_rollback_is_triggered,
    same_context_verifier_panel,
    sanitization_clip_bounds,
    select_largest_density_cluster,
    trimmed_mean_aggregate,
)
from fedsira.baselines.certified_ensemble import (
    certified_ensemble_domain_groups,
    certified_ensemble_post_reference_rounds,
    ensemble_predicted_label,
    validate_group_without_target_member_uses_supported_only,
)
from fedsira.baselines.independent_retraining import (
    candidate_free_full_path_opening_mode,
    one_independent_retrain_local_epochs,
)
from fedsira.baselines.references import (
    centralized_reference_local_epochs,
    centralized_reference_pooled_rows,
    fedavg_reference_post_reference_local_epochs,
    fedavg_reference_post_reference_participants,
    fedavg_reference_post_reference_rounds,
    local_only_reference_evaluation_is_domain_local,
    local_only_reference_local_epochs,
    local_only_reference_training_role,
    post_reference_retrain_maximum_local_epochs,
    standard_fl_anchor_rounds,
)
from fedsira.baselines.registry import (
    BaselineIdentity,
    domain_target_view,
    domain_without_target_view_may_participate,
    first_eligible_non_source_reproducer,
    review_style_baseline_outcome,
    single_fresh_verifier_domain,
    single_fresh_verifier_outcome,
    validate_role_not_used_for_tuning,
)
from fedsira.baselines.robust_aggregation import (
    client_sampling_round_order,
    coordinate_wise_median_synthesis,
    direct_krum_committee_rows,
    krum_reference_post_reference_rounds,
    krum_reference_round_participants,
    validate_three_row_coordinate_median_committee_size,
)
from fedsira.baselines.source_authority import (
    CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES,
    CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
    INDEPENDENT_LOCAL_REFERENCE_REQUIRED_POSITIVE_REVIEWS,
    INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT,
    SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS,
    SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT,
    client_review_direct_admission_production_is_source,
    client_review_then_retrain_local_epochs,
    client_review_then_retrain_should_discard_source_weights,
    independent_local_reference_reviewer_is_positive,
    secure_continual_assessment_post_reference_rounds,
    validate_client_review_composite_screen,
    validate_client_review_reviewer_count,
)
from fedsira.boundaries.capability_granularity import (
    apply_root_cause_feature_shift,
    balanced_capability_selection,
    root_cause_for_sample,
    target_row_ids_for_contract,
    validate_excluded_root_cause_not_supported,
)
from fedsira.boundaries.epistemic_failure import (
    apply_attacker_induced_common_context,
    apply_shared_spurious_feature,
    diagnostic_marker_metric_or_insufficient,
    match_diagnostic_benign_report_test_rows,
    relabel_shared_label_error_rows,
    select_shared_label_error_rows,
    select_spurious_feature_rows,
)
from fedsira.boundaries.evidence_arrival import (
    EvidenceArrivalSchedule,
    compute_t_evidence,
    first_holder_cycle_for_domain,
    holder_count_at_cycle,
    reproducer_order,
)
from fedsira.boundaries.heterogeneity import (
    apply_quantity_skew_to_cap,
    exclude_source_from_quantity_skew,
    feature_shift_sign,
    quantity_skew_multiplier_by_domain,
    quantity_skew_multiplier_for_domain,
    select_heterogeneity_shift_features,
)
from fedsira.config.schema import VerificationConfig
from fedsira.datasets.ciciot2023.schema import TARGET_LABEL as CICIOT2023_TARGET_LABEL
from fedsira.datasets.common import Role, role_hash_token
from fedsira.datasets.nbaiot.preprocessing import view_parquet_path
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TRIGGER_FEATURES,
    NBaiotClass,
    NBaiotDomain,
    nbaiot_domain_hash_token,
)
from fedsira.domain.enums import (
    ByzantineVerifierBehavior,
    CapabilityContractScope,
    ClaimOpeningMode,
    ClaimState,
    CoreMethodIdentity,
    DatasetId,
    DormantOrigin,
    EvaluationInsufficiencyReason,
    ExperimentLifecycleState,
    FailureClass,
    RootCause,
    ScientificCellPhase,
    SeedNamespace,
    TernaryOutcome,
    VerificationOmissionMarker,
)
from fedsira.domain.records import (
    AdequateFinalGateDomainCount,
    AlgorithmName,
    AllowSourceAsVerifier,
    ArtifactDigest,
    BooleanValue,
    CapabilityContractSatisfied,
    CellCompletionStatus,
    ClaimId,
    ClassIndex,
    ClassLabel,
    CompleteSeedCount,
    ConditionName,
    DatasetClassToken,
    DerivedSeed,
    DomainCount,
    DomainId,
    ExampleCount,
    ExecutionSchemaVersion,
    ExperimentName,
    FailureMessage,
    FeatureCount,
    FeatureIndex,
    FeatureMoment,
    FeatureName,
    FiniteFloat,
    FoldIndex,
    FrozenDomainModel,
    LocalEpochCount,
    MasterSeed,
    MethodName,
    MetricDifference,
    MetricName,
    MetricObservation,
    MetricValue,
    MinimumCompletePairCount,
    ModuleName,
    NonNegativeInt,
    OverwriteExisting,
    PairedDifference,
    PositiveInt,
    PreparedEvidencePresent,
    PreparedReproductionTargetCount,
    PreparedScreenTargetCount,
    PreparedSupportedReplayCount,
    PreparedViewKey,
    Probability,
    RequiredReproductionRowCount,
    ResolvedCoreComplete,
    RoundIndex,
    ScenarioName,
    ScientificCellCount,
    ScientificCellSemanticKey,
    SeedBundle,
    TriggerFeatureValue,
)
from fedsira.evaluation.aggregation import (
    coefficient_of_variation,
    decile_bin,
    decile_boundaries,
    domain_disparity,
    equal_weight_domain_mean,
    interquartile_range,
    percentile_10_domain_target_f1,
    worst_domain_target_f1,
)
from fedsira.evaluation.metrics import (
    benign_false_alarm_rate,
    boundary_metric_set,
    clean_proposal_oracle_label,
    compute_confusion_counts_by_class,
    dormant_claim_rate,
    f1_for_class,
    false_launch_rate,
    legitimate_admission_rate,
    macro_f1,
    malicious_admission_rate,
    metric_value,
    report_metric_set,
    reproduction_attempt_count,
    supported_macro_f1_harm,
    target_capability_gain,
)
from fedsira.evaluation.records import (
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
from fedsira.experiments.collapse import CollapseEvaluationInput, ResolvedCore
from fedsira.experiments.planning import (
    ExperimentPlan,
    PlannedExperiment,
    ScientificCell,
    build_plan,
)
from fedsira.experiments.registry import (
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
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    AblationVariant,
    BoundCondition,
    ClaimFamily,
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
    experiment_by_name,
)
from fedsira.experiments.validation import (
    ExperimentPrerequisiteState,
    run_data_and_domain_evidence_validation,
    run_protocol_invariant_validation,
    validate_cell_terminal_record,
    validate_condition_vocabulary,
    validate_experiment_prerequisites_met,
    validate_no_duplicate_semantic_cells,
)
from fedsira.learning.aggregation import (
    ModelState,
    WeightedModelState,
    load_model_state,
    model_state_from_classifier,
)
from fedsira.learning.anchor import run_anchor_fedavg_training
from fedsira.learning.federated import (
    LocalTrainingClient,
    run_fedavg_round,
    train_one_client_locally,
)
from fedsira.learning.post_reference import run_post_reference_training
from fedsira.learning.scoring import logits_for_samples
from fedsira.models.mlp import (
    FedSIRAClassifier,
    flatten_trainable_parameters,
    load_flat_trainable_parameters,
)
from fedsira.protocol.admission import (
    AdmissionArtifactContent,
    apply_production_update,
    final_gate_predicates_pass,
    median_domain_target_f1,
    resolve_production_update,
    validate_admission_artifact_content,
    validate_admission_requires_final_gate,
    validate_production_checkpoint_excludes_source,
)
from fedsira.protocol.claim_contract import (
    build_capability_claim_contract,
    capability_claim_contract_passes,
    compute_claim_identity,
    reproduction_evidence_is_adequate,
    screen_evidence_is_adequate,
    validate_source_excluded_production_weight,
    verification_evidence_is_adequate,
)
from fedsira.protocol.opening import (
    ScreenDomainResult,
    ScreenLossObservation,
    candidate_free_screen_domain_predicate,
    candidate_screen_transition,
    raw_target_f1_screen_domain_decision_is_positive,
    run_proposal_screen_for_domain,
    screen_domain_decision_is_positive,
    screen_domain_order,
    screen_fold_index,
    select_source_domain,
    source_selection_order,
    start_claim,
    unmatched_control_screen_domain_decision_is_positive,
)
from fedsira.protocol.reproduction import (
    ReproductionAttempt,
    compute_reproduction_commitment_hash,
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
from fedsira.protocol.state_machine import (
    apply_logical_cycle_expiry,
    resolve_ternary_outcome,
    resume_dormant_claim,
)
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    krum_input_excludes_source,
    select_krum_update,
    synthesis_pending_transition,
)
from fedsira.protocol.theory import (
    deduplicate_reports_by_proxy,
    diagnostic_at_least_two_byzantine_probability,
    first_cycle_with_minimum_eligible_evidence_holders,
    krum_committee_is_admissible,
    minimum_honest_positive_count,
    report_for_domain,
    reproduction_update_vector,
    validate_exactly_one_source_domain,
    validate_no_safety_claim_before_tau_k,
)
from fedsira.protocol.verification import (
    byzantine_selection_order,
    construct_above_bound_panel,
    deterministic_verifier_panel,
    diagnostic_committee_panel,
    panel_votes_are_one_per_domain,
    reproduction_row_is_certified,
    select_compromised_verifiers,
    verification_pending_transition,
    verifier_assignment_seed_for_row,
    verifier_assignment_timestamp_is_valid,
    verifier_is_eligible,
)
from fedsira.runtime.determinism import (
    derive_uint32,
    framed_bytes,
    local_training_seed,
    namespace_seed,
    seed_job_local_rng_streams,
)
from fedsira.runtime.recovery import automatic_recovery_permitted
from fedsira.runtime.state import FailureDetail, current_application_context
from fedsira.runtime.timing import (
    ElapsedTimer,
    peak_gpu_memory_bytes,
    peak_host_resident_set_bytes,
    reset_peak_gpu_memory_counter,
)

EXECUTION_RECORD_SCHEMA_VERSION: ExecutionSchemaVersion = "fedsira|execution_record|1"


class PersistedFailureDetail(FrozenDomainModel):
    failure_class: FailureClass
    message: FailureMessage
    cell_phase: ScientificCellPhase | None


class PersistedExecutionRecord(FrozenDomainModel):
    schema_version: ExecutionSchemaVersion
    semantic_key: ScientificCellSemanticKey
    experiment: ExperimentName
    method: MethodName
    condition: ScenarioName
    master_seed: MasterSeed
    terminal_state: ExperimentLifecycleState
    metrics: tuple[MetricObservation, ...]
    failure: PersistedFailureDetail | None


class CellExecutionOutcome(FrozenDomainModel):
    cell: ScientificCell
    terminal_state: ExperimentLifecycleState
    failure: FailureDetail | None
    metrics: tuple[MetricObservation, ...] = ()

    @property
    def completed(self) -> CellCompletionStatus:
        return self.terminal_state is ExperimentLifecycleState.COMPLETED


TERMINAL_EXPERIMENT_STATES: frozenset[ExperimentLifecycleState] = frozenset(
    (
        ExperimentLifecycleState.COMPLETED,
        ExperimentLifecycleState.FAILED,
        ExperimentLifecycleState.INVALID,
    )
)


class ExperimentExecutionResult(FrozenDomainModel):
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    outcomes: tuple[CellExecutionOutcome, ...]
    comparison_results: tuple[ComparisonFamilyResult, ...] = ()
    execution_digest: ArtifactDigest | None = None

    @property
    def cell_completion_count(self) -> ScientificCellCount:
        return sum(1 for outcome in self.outcomes if outcome.completed)


class CellExecutor(Protocol):
    def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome: ...


class ExecutionRecordStore:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    def _record_directory(self, experiment: ExperimentName) -> Path:
        return self._workspace_root / "experiments" / experiment / "evaluations" / "records"

    def write_outcome(self, outcome: CellExecutionOutcome) -> None:
        directory = self._record_directory(outcome.cell.experiment)
        directory.mkdir(parents=True, exist_ok=True)
        failure = (
            None
            if outcome.failure is None
            else PersistedFailureDetail(
                failure_class=outcome.failure.failure_class,
                message=outcome.failure.message,
                cell_phase=outcome.failure.cell_phase,
            )
        )
        record = PersistedExecutionRecord(
            schema_version=EXECUTION_RECORD_SCHEMA_VERSION,
            semantic_key=outcome.cell.semantic_key,
            experiment=outcome.cell.experiment,
            method=outcome.cell.method,
            condition=outcome.cell.condition,
            master_seed=outcome.cell.master_seed,
            terminal_state=outcome.terminal_state,
            metrics=outcome.metrics,
            failure=failure,
        )
        digest = hashlib.sha256(framed_bytes(outcome.cell.semantic_key)).hexdigest()
        (directory / f"{digest}.json").write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )

    def read_outcome(
        self, experiment: ExperimentName, semantic_key: ScientificCellSemanticKey
    ) -> PersistedExecutionRecord | None:
        digest = hashlib.sha256(framed_bytes(semantic_key)).hexdigest()
        path = self._record_directory(experiment) / f"{digest}.json"
        if not path.exists():
            return None
        record = PersistedExecutionRecord.model_validate_json(path.read_text(encoding="utf-8"))
        if record.semantic_key != semantic_key or record.experiment != experiment:
            raise ValueError("persisted execution record identity mismatch")
        return record

    def read_all_outcomes(self, experiment: ExperimentName) -> tuple[PersistedExecutionRecord, ...]:
        directory = self._record_directory(experiment)
        if not directory.exists():
            return ()
        records = tuple(
            PersistedExecutionRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("*.json"))
        )
        for record in records:
            if record.experiment != experiment:
                raise ValueError("persisted execution record experiment mismatch")
        return records

    def read_planned_outcomes(
        self, planned: PlannedExperiment
    ) -> tuple[PersistedExecutionRecord, ...]:
        return planned_execution_records(planned, self.read_all_outcomes(planned.definition.name))


class MetricCellKey(FrozenDomainModel):
    dataset: DatasetId
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    master_seed: MasterSeed
    method: MethodName


class MetricCellRecord(FrozenDomainModel):
    key: MetricCellKey
    metrics: tuple[MetricObservation, ...]


class ExperimentExecutionDigestInput(FrozenDomainModel):
    experiment: ExperimentName
    lifecycle_state: ExperimentLifecycleState
    semantic_keys: tuple[ScientificCellSemanticKey, ...]


def _merge_metric_record(
    records: tuple[MetricCellRecord, ...], incoming: MetricCellRecord
) -> tuple[MetricCellRecord, ...]:
    retained = tuple(record for record in records if record.key != incoming.key)
    return (*retained, incoming)


def _metric_value(
    records: tuple[MetricCellRecord, ...], key: MetricCellKey, metric: MetricName
) -> MetricValue | None:
    for record in reversed(records):
        if record.key != key:
            continue
        for metric_name, metric_result in reversed(record.metrics):
            if metric_name == metric:
                return metric_result
    return None


def _metric_index_from_outcomes(
    dataset: DatasetId, outcomes: tuple[CellExecutionOutcome, ...]
) -> tuple[MetricCellRecord, ...]:
    records: tuple[MetricCellRecord, ...] = ()
    for outcome in outcomes:
        if outcome.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        records = _merge_metric_record(
            records,
            MetricCellRecord(
                key=MetricCellKey(
                    dataset=dataset,
                    experiment=outcome.cell.experiment,
                    scientific_scenario=outcome.cell.condition,
                    master_seed=outcome.cell.master_seed,
                    method=outcome.cell.method,
                ),
                metrics=outcome.metrics,
            ),
        )
    return records


def _extend_index_from_records(
    records: tuple[MetricCellRecord, ...],
    dataset: DatasetId,
    persisted_records: tuple[PersistedExecutionRecord, ...],
) -> tuple[MetricCellRecord, ...]:
    merged = records
    for record in persisted_records:
        if record.terminal_state is not ExperimentLifecycleState.COMPLETED:
            continue
        merged = _merge_metric_record(
            merged,
            MetricCellRecord(
                key=MetricCellKey(
                    dataset=dataset,
                    experiment=record.experiment,
                    scientific_scenario=record.condition,
                    master_seed=record.master_seed,
                    method=record.method,
                ),
                metrics=record.metrics,
            ),
        )
    return merged


def _benefit_difference(
    orientation: ComparisonOrientation,
    effect_scale: ComparisonEffectScale,
    method_value: MetricValue,
    reference_value: MetricValue,
) -> PairedDifference | None:
    absolute_difference = (
        method_value - reference_value
        if orientation is ComparisonOrientation.HIGHER_IS_BETTER
        else reference_value - method_value
    )
    if effect_scale is ComparisonEffectScale.ABSOLUTE:
        return absolute_difference
    if reference_value == 0.0:
        return None
    return absolute_difference / abs(reference_value)


def _comparison_pairs(
    definition: ComparisonDefinition,
    dataset: DatasetId,
    metric_index: tuple[MetricCellRecord, ...],
    master_seeds: tuple[MasterSeed, ...],
) -> tuple[PairedDifference, ...]:
    paired: list[PairedDifference] = []
    for seed in master_seeds:
        method_key = MetricCellKey(
            dataset=dataset,
            experiment=definition.experiment,
            scientific_scenario=definition.scientific_scenario,
            master_seed=seed,
            method=definition.method,
        )
        method_value = _metric_value(metric_index, method_key, definition.metric.value)
        if method_value is None:
            continue
        if definition.reference_kind is ComparisonReferenceKind.ZERO:
            reference_value: MetricValue | None = 0.0
        else:
            reference_key = MetricCellKey(
                dataset=dataset,
                experiment=definition.reference_experiment,
                scientific_scenario=definition.reference_scenario,
                master_seed=seed,
                method=definition.reference_method,
            )
            reference_value = _metric_value(metric_index, reference_key, definition.metric.value)
        if reference_value is None:
            continue
        difference = _benefit_difference(
            definition.orientation, definition.effect_scale, method_value, reference_value
        )
        if difference is not None:
            paired.append(difference)
    return tuple(paired)


def comparison_results_for_experiment(
    experiment: ExperimentName,
    dataset: DatasetId,
    outcomes: tuple[CellExecutionOutcome, ...],
    store: ExecutionRecordStore | None = None,
) -> tuple[ComparisonFamilyResult, ...]:
    config = current_application_context().scientific_config
    definitions = tuple(
        definition
        for definition in build_comparison_registry()
        if definition.experiment == experiment
    )
    if not definitions:
        return ()
    execution_store = store or ExecutionRecordStore(
        Path(config.runtime.repository_layout.execution_workspace)
    )
    metric_index = _metric_index_from_outcomes(dataset, outcomes)
    reference_experiments = frozenset(
        definition.reference_experiment
        for definition in definitions
        if definition.reference_kind is ComparisonReferenceKind.SCIENTIFIC_CELL
        and definition.reference_experiment != experiment
    )
    for reference_experiment in sorted(reference_experiments):
        reference_definition = experiment_by_name(reference_experiment)
        if reference_definition.dataset is not dataset:
            raise ValueError(
                f"comparison reference {reference_experiment} uses "
                f"{reference_definition.dataset.value}, expected {dataset.value}"
            )
        metric_index = _extend_index_from_records(
            metric_index, dataset, execution_store.read_all_outcomes(reference_experiment)
        )
    minimum_complete_pairs = (
        config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support
    )
    families: list[ComparisonFamilyResult] = []
    for family in ClaimFamily:
        family_definitions = tuple(
            definition for definition in definitions if definition.family is family
        )
        if not family_definitions:
            continue
        results: list[ComparisonResult] = []
        for definition in family_definitions:
            paired = _comparison_pairs(
                definition, dataset, metric_index, config.seeds_and_determinism.master_seeds
            )
            complete_seeds: CompleteSeedCount = len(paired)
            if complete_seeds < minimum_complete_pairs:
                state = (
                    ComparisonState.UNDEFINED
                    if complete_seeds == 0
                    else ComparisonState.INCONCLUSIVE_TECHNICAL
                )
                results.append(
                    ComparisonResult(
                        definition=definition,
                        paired_differences=paired,
                        complete_seed_count=complete_seeds,
                        mean_paired_difference=None,
                        median_paired_difference=None,
                        paired_standardized_effect=None,
                        raw_p_value=None,
                        adjusted_p_value=None,
                        confidence_interval=None,
                        materiality_passes=None,
                        comparison_state=state,
                    )
                )
                continue
            results.append(
                evaluate_comparison(
                    definition,
                    paired,
                    config.metrics_and_statistics.bootstrap,
                    config.seeds_and_determinism.analysis_seed,
                )
            )
        families.append(
            apply_holm_adjustment(
                ComparisonFamilyResult(family=family, comparisons=tuple(results)),
                config.metrics_and_statistics.multiplicity,
            )
        )
    return tuple(families)


def _record_metric(record: PersistedExecutionRecord, metric: MetricName) -> MetricValue | None:
    for metric_name, metric_result in reversed(record.metrics):
        if metric_name == metric:
            return metric_result
    return None


def _record_metric_for_seed_and_method(
    records: tuple[PersistedExecutionRecord, ...],
    condition: ScenarioName,
    master_seed: MasterSeed,
    method: MethodName,
    metric: MetricName,
) -> MetricValue | None:
    for record in reversed(records):
        if (
            record.terminal_state is ExperimentLifecycleState.COMPLETED
            and record.condition == condition
            and (record.master_seed == master_seed)
            and (record.method == method)
        ):
            return _record_metric(record, metric)
    return None


def _paired_constraint_means(
    records: tuple[PersistedExecutionRecord, ...],
    method: MethodName,
    reference: MethodName,
    conditions: tuple[ScenarioName, ...],
    metric: MetricName,
    *,
    orientation: ComparisonOrientation,
    minimum_complete_pairs: MinimumCompletePairCount,
) -> tuple[MetricDifference, ...] | None:
    means: list[MetricDifference] = []
    for condition in conditions:
        seeds = tuple(
            sorted(
                frozenset(
                    record.master_seed
                    for record in records
                    if record.terminal_state is ExperimentLifecycleState.COMPLETED
                    and record.condition == condition
                    and (record.method in (method, reference))
                )
            )
        )
        differences: list[MetricDifference] = []
        for seed in seeds:
            method_value = _record_metric_for_seed_and_method(
                records, condition, seed, method, metric
            )
            reference_value = _record_metric_for_seed_and_method(
                records, condition, seed, reference, metric
            )
            if method_value is None or reference_value is None:
                continue
            differences.append(
                method_value - reference_value
                if orientation is ComparisonOrientation.LOWER_IS_BETTER
                else reference_value - method_value
            )
        if len(differences) < minimum_complete_pairs:
            return None
        means.append(sum(differences) / len(differences))
    return tuple(means)


def _maximum_constraint(values: tuple[MetricDifference, ...] | None) -> MetricDifference | None:
    return None if values is None else max(values)


def collapse_evaluation_from_records(
    experiment: ExperimentName, records: tuple[PersistedExecutionRecord, ...]
) -> CollapseEvaluationInput | None:
    config = current_application_context().scientific_config
    minimum_pairs = (
        config.metrics_and_statistics.technical_completion.minimum_complete_pairs_for_claim_support
    )
    if experiment == PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME:
        legitimate = _maximum_constraint(
            _paired_constraint_means(
                records,
                OpeningMode.PROPOSAL_ASSISTED.value,
                OpeningMode.CANDIDATE_FREE.value,
                (ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,),
                ComparisonMetric.LEGITIMATE_ADMISSION.value,
                orientation=ComparisonOrientation.HIGHER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        malicious = _maximum_constraint(
            _paired_constraint_means(
                records,
                OpeningMode.PROPOSAL_ASSISTED.value,
                OpeningMode.CANDIDATE_FREE.value,
                (ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,),
                ComparisonMetric.MALICIOUS_ADMISSION.value,
                orientation=ComparisonOrientation.LOWER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        return CollapseEvaluationInput(
            proposal_legitimate_admission_degradation=legitimate,
            proposal_malicious_admission_worsening=malicious,
            plurality_legitimate_admission_degradation=None,
            plurality_supported_harm=None,
            source_exclusion_target_f1_drop=None,
            source_exclusion_supported_harm=None,
            source_exclusion_benign_far_increase=None,
            external_verification_legitimate_admission_degradation=None,
        )
    if experiment == SINGLE_REPRODUCTION_NECESSITY_NAME:
        conditions = tuple(condition.value for condition in PluralityCondition)
        legitimate = _maximum_constraint(
            _paired_constraint_means(
                records,
                CoreMethodIdentity.FULL_PLURALITY_PATH.value,
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                conditions,
                ComparisonMetric.LEGITIMATE_ADMISSION.value,
                orientation=ComparisonOrientation.HIGHER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        supported = _maximum_constraint(
            _paired_constraint_means(
                records,
                CoreMethodIdentity.FULL_PLURALITY_PATH.value,
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                conditions,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM.value,
                orientation=ComparisonOrientation.LOWER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        return CollapseEvaluationInput(
            proposal_legitimate_admission_degradation=None,
            proposal_malicious_admission_worsening=None,
            plurality_legitimate_admission_degradation=legitimate,
            plurality_supported_harm=supported,
            source_exclusion_target_f1_drop=None,
            source_exclusion_supported_harm=None,
            source_exclusion_benign_far_increase=None,
            external_verification_legitimate_admission_degradation=None,
        )
    if experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
        conditions = (PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,)
        method = SourceExclusionMethod.FULL_FEDSIRA.value
        reference = BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value
        target = _maximum_constraint(
            _paired_constraint_means(
                records,
                method,
                reference,
                conditions,
                ComparisonMetric.TARGET_F1.value,
                orientation=ComparisonOrientation.HIGHER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        supported = _maximum_constraint(
            _paired_constraint_means(
                records,
                method,
                reference,
                conditions,
                ComparisonMetric.SUPPORTED_MACRO_F1_HARM.value,
                orientation=ComparisonOrientation.LOWER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        benign = _maximum_constraint(
            _paired_constraint_means(
                records,
                method,
                reference,
                conditions,
                ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE.value,
                orientation=ComparisonOrientation.LOWER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        return CollapseEvaluationInput(
            proposal_legitimate_admission_degradation=None,
            proposal_malicious_admission_worsening=None,
            plurality_legitimate_admission_degradation=None,
            plurality_supported_harm=None,
            source_exclusion_target_f1_drop=target,
            source_exclusion_supported_harm=supported,
            source_exclusion_benign_far_increase=benign,
            external_verification_legitimate_admission_degradation=None,
        )
    if experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME:
        legitimate = _maximum_constraint(
            _paired_constraint_means(
                records,
                SourceExclusionMethod.FULL_FEDSIRA.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
                (ExternalVerificationCondition.LEGITIMATE_TRANSFERABLE_CAPABILITY.value,),
                ComparisonMetric.LEGITIMATE_ADMISSION.value,
                orientation=ComparisonOrientation.HIGHER_IS_BETTER,
                minimum_complete_pairs=minimum_pairs,
            )
        )
        return CollapseEvaluationInput(
            proposal_legitimate_admission_degradation=None,
            proposal_malicious_admission_worsening=None,
            plurality_legitimate_admission_degradation=None,
            plurality_supported_harm=None,
            source_exclusion_target_f1_drop=None,
            source_exclusion_supported_harm=None,
            source_exclusion_benign_far_increase=None,
            external_verification_legitimate_admission_degradation=legitimate,
        )
    return None


def _digest_execution_result(
    experiment: ExperimentName,
    lifecycle_state: ExperimentLifecycleState,
    outcomes: tuple[CellExecutionOutcome, ...],
) -> ArtifactDigest:
    payload = ExperimentExecutionDigestInput(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        semantic_keys=tuple(outcome.cell.semantic_key for outcome in outcomes),
    )
    return hashlib.sha256(payload.model_dump_json().encode("utf-8")).hexdigest()


def _execute_cell_with_retry(cell: ScientificCell, executor: CellExecutor) -> CellExecutionOutcome:
    config = current_application_context().scientific_config
    attempts = config.runtime.automatic_infrastructure_retries_per_cell_phase + 1
    last_outcome: CellExecutionOutcome | None = None
    for attempt in range(attempts):
        outcome = executor.execute_cell(cell)
        validate_cell_terminal_record(cell, outcome.terminal_state)
        if outcome.terminal_state is not ExperimentLifecycleState.FAILED:
            return outcome
        if outcome.failure is None or not automatic_recovery_permitted(
            outcome.failure.failure_class,
            attempt,
            config.runtime.automatic_infrastructure_retries_per_cell_phase,
        ):
            return outcome
        last_outcome = outcome
    if last_outcome is None:
        raise RuntimeError("cell retry loop produced no outcome")
    return last_outcome


def _planned_semantic_keys(planned: PlannedExperiment) -> frozenset[ScientificCellSemanticKey]:
    return frozenset(cell.semantic_key for cell in planned.cells)


def planned_execution_records(
    planned: PlannedExperiment, records: tuple[PersistedExecutionRecord, ...]
) -> tuple[PersistedExecutionRecord, ...]:
    planned_keys = _planned_semantic_keys(planned)
    return tuple(record for record in records if record.semantic_key in planned_keys)


def _record_for_cell(
    records: tuple[PersistedExecutionRecord, ...], cell: ScientificCell
) -> PersistedExecutionRecord | None:
    for record in records:
        if record.semantic_key == cell.semantic_key:
            return record
    return None


def derive_experiment_lifecycle(
    planned: PlannedExperiment, records: tuple[PersistedExecutionRecord, ...]
) -> ExperimentLifecycleState:
    if planned.lifecycle_state is ExperimentLifecycleState.BLOCKED:
        return ExperimentLifecycleState.BLOCKED
    relevant = planned_execution_records(planned, records)
    if not relevant:
        return ExperimentLifecycleState.READY
    if any(record.terminal_state is ExperimentLifecycleState.INVALID for record in relevant):
        return ExperimentLifecycleState.INVALID
    if any(record.terminal_state is ExperimentLifecycleState.FAILED for record in relevant):
        return ExperimentLifecycleState.FAILED
    complete = all(
        (record := _record_for_cell(relevant, cell)) is not None
        and record.terminal_state is ExperimentLifecycleState.COMPLETED
        for cell in planned.cells
    )
    return ExperimentLifecycleState.COMPLETED if complete else ExperimentLifecycleState.RUNNING


def _prerequisite_states_from_store(
    plan: ExperimentPlan, experiment: ExperimentName, store: ExecutionRecordStore
) -> tuple[ExperimentPrerequisiteState, ...]:
    definition = experiment_by_name(experiment)
    return tuple(
        ExperimentPrerequisiteState(
            experiment=prerequisite,
            lifecycle_state=derive_experiment_lifecycle(
                plan.experiment(prerequisite),
                store.read_planned_outcomes(plan.experiment(prerequisite)),
            ),
        )
        for prerequisite in definition.prerequisites
    )


def execute_experiment(
    experiment: ExperimentName,
    executor: CellExecutor,
    *,
    overwrite: OverwriteExisting = False,
    resolved_core_complete: ResolvedCoreComplete = False,
    prerequisite_states: tuple[ExperimentPrerequisiteState, ...] | None = None,
) -> ExperimentExecutionResult:
    resolved_config = current_application_context().scientific_config
    definition = experiment_by_name(experiment)
    plan = build_plan(
        resolved_core_complete=resolved_core_complete,
        master_seeds=resolved_config.seeds_and_determinism.master_seeds,
        smoke_seed=resolved_config.seeds_and_determinism.smoke_seed,
    )
    validate_condition_vocabulary(plan)
    validate_no_duplicate_semantic_cells(plan)
    planned = plan.experiment(experiment)
    if planned.lifecycle_state is ExperimentLifecycleState.BLOCKED:
        return ExperimentExecutionResult(
            experiment=experiment, lifecycle_state=ExperimentLifecycleState.BLOCKED, outcomes=()
        )
    store = ExecutionRecordStore(
        Path(resolved_config.runtime.repository_layout.execution_workspace)
    )
    states = prerequisite_states or _prerequisite_states_from_store(plan, experiment, store)
    validate_experiment_prerequisites_met(experiment, states)
    outcomes: list[CellExecutionOutcome] = []
    for cell in planned.cells:
        existing = store.read_outcome(experiment, cell.semantic_key)
        if existing is not None and (not overwrite):
            outcomes.append(
                CellExecutionOutcome(
                    cell=cell,
                    terminal_state=existing.terminal_state,
                    failure=None
                    if existing.failure is None
                    else FailureDetail(
                        failure_class=existing.failure.failure_class,
                        message=existing.failure.message,
                        cell_phase=existing.failure.cell_phase,
                    ),
                    metrics=existing.metrics,
                )
            )
            continue
        outcome = _execute_cell_with_retry(cell, executor)
        store.write_outcome(outcome)
        outcomes.append(outcome)
    outcome_tuple = tuple(outcomes)
    persisted = store.read_planned_outcomes(planned)
    lifecycle_state = derive_experiment_lifecycle(planned, persisted)
    comparison_results = comparison_results_for_experiment(
        experiment, definition.dataset, outcome_tuple, store
    )
    return ExperimentExecutionResult(
        experiment=experiment,
        lifecycle_state=lifecycle_state,
        outcomes=outcome_tuple,
        comparison_results=comparison_results,
        execution_digest=_digest_execution_result(experiment, lifecycle_state, outcome_tuple),
    )


ANCHOR_TRAINING_ALGORITHM_TOKEN = "ANCHOR_FEDAVG"
SOURCE_TRAINING_ALGORITHM_TOKEN = "SOURCE_CANDIDATE"
GENERIC_HARD_SUPPORTED_EXAMPLES_TRAINING_ALGORITHM_TOKEN = "GENERIC_HARD_SUPPORTED_EXAMPLES"
REPRODUCTION_TRAINING_ALGORITHM_TOKEN = "REPRODUCTION"
FEDAVG_REFERENCE_TRAINING_ALGORITHM_TOKEN = "FEDAVG_REFERENCE"
SECURE_CONTINUAL_ASSESSMENT_TRAINING_ALGORITHM_TOKEN = "SECURE_CONTINUAL_ASSESSMENT"
LOCAL_ONLY_REFERENCE_TRAINING_ALGORITHM_TOKEN = "LOCAL_ONLY_REFERENCE"
CENTRALIZED_REFERENCE_TRAINING_ALGORITHM_TOKEN = "CENTRALIZED_REFERENCE"
DENSITY_CLUSTER_TRIMMED_MEAN_TRAINING_ALGORITHM_TOKEN = "DENSITY_CLUSTER_TRIMMED_MEAN"
CALIBRATION_TRAINING_ALGORITHM_TOKEN = "ANCHOR_ROUND_CALIBRATION"
UPDATE_RECONSTRUCTION_FILTER_TRAINING_ALGORITHM_TOKEN = "UPDATE_RECONSTRUCTION_FILTER"
RECOVERY_AFTER_SOURCE_ADMISSION_TRAINING_ALGORITHM_TOKEN = "RECOVERY_AFTER_SOURCE_ADMISSION"
CERTIFIED_ENSEMBLE_ANCHOR_TRAINING_ALGORITHM_TOKEN = "CERTIFIED_ENSEMBLE_ANCHOR"
CERTIFIED_ENSEMBLE_POST_REFERENCE_TRAINING_ALGORITHM_TOKEN = "CERTIFIED_ENSEMBLE_POST_REFERENCE"
CLEAN_TRAINING_CONDITION_TOKEN = ReproducerCondition.CLEAN.value


@dataclass(frozen=True)
class PreparedRows:
    sample_ids: tuple[ArtifactDigest, ...]
    features: tuple[tuple[FeatureMoment, ...], ...]
    labels: tuple[ClassLabel, ...]

    @property
    def row_count(self) -> ExampleCount:
        return len(self.sample_ids)


@dataclass(frozen=True)
class RealAnchor:
    input_width: FeatureCount
    output_width: FeatureCount
    flat_parameters: torch.Tensor
    dataset_manifest_hash: ArtifactDigest
    round_start_flat_parameters: tuple[torch.Tensor, ...]


@dataclass(frozen=True)
class DomainTargetMetrics:
    target_f1: MetricResult
    supported_macro_f1: MetricResult
    benign_far: MetricResult


@dataclass(frozen=True)
class RootCauseScope:
    contract_scope: CapabilityContractScope
    feature_names: tuple[FeatureName, ...]
    root_cause_a_feature_name: FeatureName
    root_cause_b_feature_name: FeatureName
    shift_value: TriggerFeatureValue
    balanced_selection_seed: DerivedSeed | None = None


@dataclass(frozen=True)
class BackdoorScope:
    attack_generation_seed: DerivedSeed
    poison_fraction: Probability
    trigger_feature_indices: tuple[FeatureIndex, ...]
    trigger_value: TriggerFeatureValue


def _poison_backdoor_rows(rows: PreparedRows, scope: BackdoorScope) -> PreparedRows:
    poisoned_ids = select_source_backdoor_poison_rows(
        rows.sample_ids, scope.poison_fraction, scope.attack_generation_seed
    )
    if not poisoned_ids:
        return rows
    poisoned_id_set = frozenset(poisoned_ids)
    labels_by_row_id = OrderedDict(
        zip(rows.sample_ids, (NBaiotClass(label) for label in rows.labels), strict=True)
    )
    relabeled = relabel_triggered_rows_as_benign(labels_by_row_id, poisoned_ids)
    kept_features: list[tuple[float, ...]] = []
    kept_labels: list[ClassLabel] = []
    for sample_id, features in zip(rows.sample_ids, rows.features, strict=True):
        if sample_id not in poisoned_id_set:
            kept_features.append(features)
            kept_labels.append(relabeled[sample_id].value)
            continue
        triggered = apply_trigger_transform(
            torch.tensor(features, dtype=torch.float32),
            scope.trigger_feature_indices,
            scope.trigger_value,
        )
        kept_features.append(tuple(float(value) for value in triggered))
        kept_labels.append(relabeled[sample_id].value)
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(kept_features), labels=tuple(kept_labels)
    )


@dataclass(frozen=True)
class HeterogeneityScope:
    heterogeneity_namespace_seed: DerivedSeed
    selected_feature_names: tuple[FeatureName, ...]
    feature_names: tuple[FeatureName, ...]
    shift_magnitude: TriggerFeatureValue


def _apply_heterogeneity_shift(
    rows: PreparedRows, domain: NBaiotDomain, scope: HeterogeneityScope
) -> PreparedRows:
    feature_indices_and_signs = tuple(
        (
            scope.feature_names.index(feature_name),
            feature_shift_sign(domain, feature_name, scope.heterogeneity_namespace_seed),
        )
        for feature_name in scope.selected_feature_names
    )
    shifted_features: list[tuple[float, ...]] = []
    for features in rows.features:
        tensor = torch.tensor(features, dtype=torch.float32)
        for feature_index, sign in feature_indices_and_signs:
            tensor[feature_index] = tensor[feature_index] + sign * scope.shift_magnitude
        shifted_features.append(tuple(float(value) for value in tensor))
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(shifted_features), labels=rows.labels
    )


def _scope_and_shift_rows(
    rows: PreparedRows, root_cause_scope: RootCauseScope
) -> PreparedRows | None:
    root_cause_a_ids = frozenset(
        sample_id
        for sample_id in rows.sample_ids
        if root_cause_for_sample(sample_id) is RootCause.A
    )
    root_cause_b_ids = frozenset(rows.sample_ids) - root_cause_a_ids
    if root_cause_scope.balanced_selection_seed is not None:
        selected_a_ids, selected_b_ids = balanced_capability_selection(
            sorted(root_cause_a_ids),
            sorted(root_cause_b_ids),
            root_cause_scope.balanced_selection_seed,
        )
        root_cause_a_ids = frozenset(selected_a_ids)
        root_cause_b_ids = frozenset(selected_b_ids)
    allowed_ids = target_row_ids_for_contract(
        root_cause_scope.contract_scope, root_cause_a_ids, root_cause_b_ids
    )
    a_index = root_cause_scope.feature_names.index(root_cause_scope.root_cause_a_feature_name)
    b_index = root_cause_scope.feature_names.index(root_cause_scope.root_cause_b_feature_name)
    kept_sample_ids: list[ArtifactDigest] = []
    kept_features: list[tuple[float, ...]] = []
    kept_labels: list[ClassLabel] = []
    for sample_id, features, label in zip(rows.sample_ids, rows.features, rows.labels, strict=True):
        if sample_id not in allowed_ids:
            continue
        row_root_cause = root_cause_for_sample(sample_id)
        shifted = apply_root_cause_feature_shift(
            torch.tensor(features, dtype=torch.float32),
            row_root_cause,
            a_index,
            b_index,
            root_cause_scope.shift_value,
        )
        kept_sample_ids.append(sample_id)
        kept_features.append(tuple(float(value) for value in shifted))
        kept_labels.append(label)
    if not kept_sample_ids:
        return None
    return PreparedRows(
        sample_ids=tuple(kept_sample_ids), features=tuple(kept_features), labels=tuple(kept_labels)
    )


@dataclass(frozen=True)
class EpistemicFailureScope:
    failure_type: EpistemicFailureType
    strength: TriggerFeatureValue
    attack_generation_seed: DerivedSeed
    feature_names: tuple[FeatureName, ...]
    spurious_feature_name: FeatureName
    spurious_feature_value: TriggerFeatureValue
    common_context_feature_names: tuple[FeatureName, ...]
    common_context_trigger_value: TriggerFeatureValue


def _relabel_shared_label_error_rows(
    rows: PreparedRows, scope: EpistemicFailureScope
) -> tuple[PreparedRows, tuple[BooleanValue, ...]]:
    selected = (
        select_shared_label_error_rows(
            rows.sample_ids, scope.strength, scope.attack_generation_seed
        )
        or ()
    )
    selected_ids = frozenset(selected)
    labels_by_row_id = OrderedDict(
        (
            (sample_id, NBaiotClass(label))
            for sample_id, label in zip(rows.sample_ids, rows.labels, strict=True)
        )
    )
    relabeled = relabel_shared_label_error_rows(labels_by_row_id, selected)
    new_labels = tuple(relabeled[sample_id].value for sample_id in rows.sample_ids)
    is_supported_mask = tuple(sample_id not in selected_ids for sample_id in rows.sample_ids)
    return (
        PreparedRows(sample_ids=rows.sample_ids, features=rows.features, labels=new_labels),
        is_supported_mask,
    )


def _mark_rows(
    rows: PreparedRows, scope: EpistemicFailureScope, selected_ids: frozenset[ArtifactDigest]
) -> PreparedRows:
    if not selected_ids:
        return rows
    is_common_context = scope.failure_type is EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT
    if is_common_context:
        feature_indices = tuple(
            scope.feature_names.index(name) for name in scope.common_context_feature_names
        )
        trigger_value = scope.common_context_trigger_value
    else:
        feature_indices = (scope.feature_names.index(scope.spurious_feature_name),)
        trigger_value = scope.spurious_feature_value
    marked_features: list[tuple[float, ...]] = []
    for sample_id, features in zip(rows.sample_ids, rows.features, strict=True):
        if sample_id not in selected_ids:
            marked_features.append(features)
            continue
        tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
        if is_common_context:
            shifted = apply_attacker_induced_common_context(tensor, feature_indices, trigger_value)
        else:
            shifted = apply_shared_spurious_feature(tensor, feature_indices[0], trigger_value)
        marked_features.append(tuple(float(value) for value in shifted.squeeze(0)))
    return PreparedRows(
        sample_ids=rows.sample_ids, features=tuple(marked_features), labels=rows.labels
    )


def _apply_epistemic_target_marker(
    rows: PreparedRows, scope: EpistemicFailureScope
) -> PreparedRows:
    selected = (
        select_spurious_feature_rows(rows.sample_ids, scope.strength, scope.attack_generation_seed)
        or ()
    )
    return _mark_rows(rows, scope, frozenset(selected))


def _view_key(domain: NBaiotDomain, class_id: NBaiotClass, role: Role) -> PreparedViewKey:
    return f"{nbaiot_domain_hash_token(domain)}_{class_id.value}_{role_hash_token(role)}"


def real_evidence_available(prepared_root: Path) -> PreparedEvidencePresent:
    return prepared_root.exists() and any(prepared_root.glob("*.parquet"))


def load_prepared_rows(
    prepared_root: Path, domain: NBaiotDomain, class_id: NBaiotClass, role: Role
) -> PreparedRows | None:
    path = view_parquet_path(prepared_root, _view_key(domain, class_id, role))
    if not path.exists():
        return None
    frame: pandas.DataFrame = pandas.read_parquet(path)
    if len(frame) == 0:
        return None
    feature_names = tuple(
        column for column in frame.columns if column not in ("sample_id", "label")
    )
    sample_id_column: pandas.Series[str] = frame["sample_id"].astype(str)
    sample_ids = tuple(sample_id_column)
    features = tuple(
        tuple(float(value) for value in row)
        for row in frame[list(feature_names)].itertuples(index=False)
    )
    label_column: pandas.Series[str] = frame["label"].astype(str)
    labels = tuple(label_column)
    return PreparedRows(sample_ids=sample_ids, features=features, labels=labels)


def prepared_feature_names(prepared_root: Path) -> tuple[FeatureName, ...] | None:
    parquet_files = tuple(sorted(prepared_root.glob("*.parquet")))
    if not parquet_files:
        return None
    frame: pandas.DataFrame = pandas.read_parquet(parquet_files[0])
    return tuple(column for column in frame.columns if column not in ("sample_id", "label"))


def dataset_manifest_hash(prepared_root: Path) -> ArtifactDigest:
    parquet_files = tuple(sorted(prepared_root.glob("*.parquet")))
    if not parquet_files:
        return "0" * 64
    hasher = hashlib.sha256()
    for path in parquet_files:
        hasher.update(framed_bytes(path.name, path.stat().st_size))
    return hasher.hexdigest()


def _tensor_view(
    rows: PreparedRows | None,
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...]] | None:
    if rows is None:
        return None
    features = torch.tensor(rows.features, dtype=torch.float32)
    label_to_index: OrderedDict[ClassLabel, ClassIndex] = OrderedDict(
        ((class_id.value, index) for index, class_id in enumerate(NBAIOT_CLASS_ORDER))
    )
    labels = torch.tensor([label_to_index[label] for label in rows.labels], dtype=torch.long)
    return (features, labels, rows.sample_ids)


def _training_seed(
    master_seed: MasterSeed,
    manifest_hash: ArtifactDigest,
    start_checkpoint_identity: ArtifactDigest,
    algorithm_token: AlgorithmName,
    domain: NBaiotDomain,
    round_index: RoundIndex,
) -> DerivedSeed:
    local_training_namespace_seed = namespace_seed(master_seed, SeedNamespace.LOCAL_TRAINING)
    return local_training_seed(
        local_training_namespace_seed,
        manifest_hash,
        start_checkpoint_identity,
        algorithm_token,
        nbaiot_domain_hash_token(domain),
        CLEAN_TRAINING_CONDITION_TOKEN,
        round_index,
    )


def flat_parameters_identity(flat_parameters: torch.Tensor) -> ArtifactDigest:
    values = flat_parameters.detach().cpu()
    joined = "|".join(repr(values[index].item()) for index in range(values.numel()))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def domain_anchor_train_feature_mean(
    prepared_root: Path, domain: NBaiotDomain
) -> torch.Tensor | None:
    combined_features: list[torch.Tensor] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        tensor_view = _tensor_view(
            load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
        )
        if tensor_view is None:
            continue
        features, _labels, _sample_ids = tensor_view
        combined_features.append(features)
    if not combined_features:
        return None
    return torch.cat(combined_features, dim=0).mean(dim=0)


def train_anchor(prepared_root: Path, master_seed: MasterSeed) -> RealAnchor | None:
    config = current_application_context().scientific_config
    first_rows = load_prepared_rows(
        prepared_root, NBAIOT_DOMAIN_ORDER[0], NBaiotClass.BENIGN, Role.ANCHOR_TRAIN
    )
    if first_rows is None:
        return None
    input_width = len(first_rows.features[0])
    output_width = len(NBAIOT_CLASS_ORDER)
    manifest_hash = dataset_manifest_hash(prepared_root)
    initialization_seed = namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION)
    seed_job_local_rng_streams(initialization_seed)
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    clients_per_round: list[tuple[LocalTrainingClient, ...]] = []
    for round_index in range(config.model.anchor_fedavg.rounds):
        round_clients: list[LocalTrainingClient] = []
        for domain in NBAIOT_DOMAIN_ORDER:
            combined_features: list[torch.Tensor] = []
            combined_labels: list[torch.Tensor] = []
            combined_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                tensor_view = _tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
                )
                if tensor_view is None:
                    continue
                features, labels, sample_ids = tensor_view
                combined_features.append(features)
                combined_labels.append(labels)
                combined_sample_ids.extend(sample_ids)
            if not combined_features:
                continue
            training_seed = _training_seed(
                master_seed,
                manifest_hash,
                "anchor-start",
                ANCHOR_TRAINING_ALGORITHM_TOKEN,
                domain,
                round_index,
            )
            round_clients.append(
                LocalTrainingClient(
                    features=torch.cat(combined_features, dim=0),
                    labels=torch.cat(combined_labels, dim=0),
                    sample_ids=tuple(combined_sample_ids),
                    training_seed=training_seed,
                )
            )
        if not round_clients:
            return None
        clients_per_round.append(tuple(round_clients))
    final_state, round_checkpoints = run_anchor_fedavg_training(
        input_width,
        output_width,
        initial_state,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        config.model.anchor_fedavg,
        tuple(clients_per_round),
    )
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, final_state)
    round_start_flat_parameters = tuple(
        _flatten_model_state(input_width, output_width, state)
        for state in (initial_state, *round_checkpoints[:-1])
    )
    return RealAnchor(
        input_width=input_width,
        output_width=output_width,
        flat_parameters=flatten_trainable_parameters(model),
        dataset_manifest_hash=manifest_hash,
        round_start_flat_parameters=round_start_flat_parameters,
    )


def _client_delta_from_role(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: NBaiotDomain,
    round_index: RoundIndex,
    round_start_flat: torch.Tensor,
    role: Role,
    local_epochs: LocalEpochCount,
    algorithm_token: AlgorithmName,
) -> tuple[torch.Tensor, NonNegativeInt] | None:
    config = current_application_context().scientific_config
    combined_features: list[torch.Tensor] = []
    combined_labels: list[torch.Tensor] = []
    combined_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        tensor_view = _tensor_view(load_prepared_rows(prepared_root, domain, class_id, role))
        if tensor_view is None:
            continue
        features, labels, sample_ids = tensor_view
        combined_features.append(features)
        combined_labels.append(labels)
        combined_sample_ids.extend(sample_ids)
    if not combined_features:
        return None
    features = torch.cat(combined_features, dim=0)
    labels = torch.cat(combined_labels, dim=0)
    sample_ids = tuple(combined_sample_ids)
    training_seed = _training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        flat_parameters_identity(round_start_flat),
        algorithm_token,
        domain,
        round_index,
    )
    round_start_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(round_start_model, round_start_flat)
    round_start_state = model_state_from_classifier(round_start_model)
    client_result = train_one_client_locally(
        round_start_state,
        anchor.input_width,
        anchor.output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        local_epochs,
        LocalTrainingClient(
            features=features, labels=labels, sample_ids=sample_ids, training_seed=training_seed
        ),
    )
    client_flat = _flatten_model_state(anchor.input_width, anchor.output_width, client_result.state)
    return (client_flat - round_start_flat, client_result.example_count)


def anchor_round_calibration_updates(
    prepared_root: Path, master_seed: MasterSeed, anchor: RealAnchor
) -> tuple[torch.Tensor, ...]:
    updates: list[torch.Tensor] = []
    for round_index, round_start_flat in enumerate(anchor.round_start_flat_parameters):
        for domain in NBAIOT_DOMAIN_ORDER:
            result = _client_delta_from_role(
                prepared_root,
                master_seed,
                anchor,
                domain,
                round_index,
                round_start_flat,
                Role.ANCHOR_VALIDATION,
                1,
                CALIBRATION_TRAINING_ALGORITHM_TOKEN,
            )
            if result is None:
                continue
            updates.append(result[0])
    return tuple(updates)


def anchor_round_reconstruction_calibration_errors(
    prepared_root: Path, master_seed: MasterSeed, anchor: RealAnchor
) -> tuple[FeatureMoment, ...]:
    config = current_application_context().scientific_config
    errors: list[FiniteFloat] = []
    expected_maximum_count = reconstruction_filter_calibration_error_count(
        len(anchor.round_start_flat_parameters), len(NBAIOT_DOMAIN_ORDER)
    )
    for round_index, round_start_flat in enumerate(anchor.round_start_flat_parameters):
        for domain in NBAIOT_DOMAIN_ORDER:
            submitted = _client_delta_from_role(
                prepared_root,
                master_seed,
                anchor,
                domain,
                round_index,
                round_start_flat,
                Role.ANCHOR_TRAIN,
                config.model.anchor_fedavg.local_epochs_per_round,
                ANCHOR_TRAINING_ALGORITHM_TOKEN,
            )
            reconstructed = _client_delta_from_role(
                prepared_root,
                master_seed,
                anchor,
                domain,
                round_index,
                round_start_flat,
                Role.ANCHOR_VALIDATION,
                1,
                CALIBRATION_TRAINING_ALGORITHM_TOKEN,
            )
            if submitted is None or reconstructed is None:
                continue
            errors.append(
                reconstruction_error(
                    submitted[0],
                    reconstructed[0],
                    config.baselines.reconstruction_filter.normalization_epsilon,
                )
            )
    if len(errors) > expected_maximum_count:
        raise ValueError(
            f"computed {len(errors)} calibration errors, exceeding the derived maximum of "
            f"{expected_maximum_count} for {len(NBAIOT_DOMAIN_ORDER)} domains and "
            f"{len(anchor.round_start_flat_parameters)} anchor rounds"
        )
    return tuple(errors)


def train_update_reconstruction_filter_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    calibration_errors = anchor_round_reconstruction_calibration_errors(
        prepared_root, master_seed, anchor
    )
    if not calibration_errors:
        return None
    rejection_threshold = reconstruction_rejection_threshold(
        calibration_errors, config.baselines.reconstruction_filter.calibration_percentile
    )
    source_rows_available = (
        source_domain is not None
        and load_prepared_rows(
            prepared_root, source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
        )
        is not None
    )
    participants = fedavg_reference_post_reference_participants(
        non_source_domains(source_domain), source_domain, source_rows_available
    )
    if not participants:
        return None
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state = model_state_from_classifier(model)
    any_round_trained = False
    for round_index in range(post_reference_retrain_maximum_local_epochs()):
        current_flat = _flatten_model_state(anchor.input_width, anchor.output_width, state)
        accepted_states: list[WeightedModelState] = []
        for domain in participants:
            target_role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = _combined_post_reference_rows(prepared_root, domain, target_role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            training_seed = _training_seed(
                master_seed,
                anchor.dataset_manifest_hash,
                flat_parameters_identity(anchor.flat_parameters),
                UPDATE_RECONSTRUCTION_FILTER_TRAINING_ALGORITHM_TOKEN,
                domain,
                round_index,
            )
            client_result = train_one_client_locally(
                state,
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed,
                ),
            )
            client_flat = _flatten_model_state(
                anchor.input_width, anchor.output_width, client_result.state
            )
            submitted_delta = client_flat - current_flat
            reconstructed = _client_delta_from_role(
                prepared_root,
                master_seed,
                anchor,
                domain,
                round_index,
                current_flat,
                Role.ANCHOR_VALIDATION,
                1,
                CALIBRATION_TRAINING_ALGORITHM_TOKEN,
            )
            if reconstructed is None:
                continue
            error = reconstruction_error(
                submitted_delta,
                reconstructed[0],
                config.baselines.reconstruction_filter.normalization_epsilon,
            )
            if reconstruction_filter_accepts(error, rejection_threshold):
                accepted_states.append(client_result)
        if not accepted_states:
            continue
        reweighted = reconstruction_filter_reweight(tuple(accepted_states))
        if reweighted is None:
            continue
        state = reweighted
        any_round_trained = True
    if not any_round_trained:
        return None
    final_flat = _flatten_model_state(anchor.input_width, anchor.output_width, state)
    return final_flat - anchor.flat_parameters


def train_source_update_sanitization_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    if source_domain is None:
        return None
    source_delta = train_source_candidate_delta(prepared_root, master_seed, anchor, source_domain)
    if source_delta is None:
        return None
    calibration_updates = anchor_round_calibration_updates(prepared_root, master_seed, anchor)
    if not calibration_updates:
        return None
    clip_bounds = sanitization_clip_bounds(
        calibration_updates, config.baselines.source_update_sanitization.coordinate_bound_percentile
    )
    return clip_source_update(source_delta, clip_bounds)


def train_local_only_reference_checkpoint(
    prepared_root: Path, master_seed: MasterSeed, domain: NBaiotDomain
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    training_role = local_only_reference_training_role()
    combined_features: list[torch.Tensor] = []
    combined_labels: list[torch.Tensor] = []
    combined_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        tensor_view = _tensor_view(
            load_prepared_rows(prepared_root, domain, class_id, training_role)
        )
        if tensor_view is None:
            continue
        features, labels, sample_ids = tensor_view
        combined_features.append(features)
        combined_labels.append(labels)
        combined_sample_ids.extend(sample_ids)
    if not combined_features:
        return None
    features = torch.cat(combined_features, dim=0)
    labels = torch.cat(combined_labels, dim=0)
    sample_ids = tuple(combined_sample_ids)
    input_width = features.shape[1]
    output_width = len(NBAIOT_CLASS_ORDER)
    initialization_seed = derive_uint32(
        "LOCAL_ONLY_REFERENCE_INIT",
        namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
        nbaiot_domain_hash_token(domain),
    )
    seed_job_local_rng_streams(initialization_seed)
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    training_seed = _training_seed(
        master_seed,
        dataset_manifest_hash(prepared_root),
        "local-only-start",
        LOCAL_ONLY_REFERENCE_TRAINING_ALGORITHM_TOKEN,
        domain,
        0,
    )
    client_result = train_one_client_locally(
        initial_state,
        input_width,
        output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        local_only_reference_local_epochs(config.baselines),
        LocalTrainingClient(
            features=features, labels=labels, sample_ids=sample_ids, training_seed=training_seed
        ),
    )
    final_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(final_model, client_result.state)
    return flatten_trainable_parameters(final_model)


def train_centralized_reference_checkpoint(
    prepared_root: Path, master_seed: MasterSeed
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    domain_features: OrderedDict[NBaiotDomain, torch.Tensor] = OrderedDict()
    domain_labels: OrderedDict[NBaiotDomain, torch.Tensor] = OrderedDict()
    domain_sample_ids: OrderedDict[NBaiotDomain, tuple[ArtifactDigest, ...]] = OrderedDict()
    for domain in NBAIOT_DOMAIN_ORDER:
        combined_features: list[torch.Tensor] = []
        combined_labels: list[torch.Tensor] = []
        combined_sample_ids: list[ArtifactDigest] = []
        for class_id in NBAIOT_CLASS_ORDER:
            if class_id is NBaiotClass.GAFGYT_COMBO:
                continue
            tensor_view = _tensor_view(
                load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
            )
            if tensor_view is None:
                continue
            features, labels, sample_ids = tensor_view
            combined_features.append(features)
            combined_labels.append(labels)
            combined_sample_ids.extend(sample_ids)
        if not combined_features:
            continue
        domain_features[domain] = torch.cat(combined_features, dim=0)
        domain_labels[domain] = torch.cat(combined_labels, dim=0)
        domain_sample_ids[domain] = tuple(combined_sample_ids)
    if not domain_features:
        return None
    pooled_features = centralized_reference_pooled_rows(domain_features)
    pooled_labels = centralized_reference_pooled_rows(domain_labels)
    pooled_sample_ids = tuple(
        sample_id
        for domain in NBAIOT_DOMAIN_ORDER
        if domain in domain_sample_ids
        for sample_id in domain_sample_ids[domain]
    )
    input_width = pooled_features.shape[1]
    output_width = len(NBAIOT_CLASS_ORDER)
    initialization_seed = derive_uint32(
        "CENTRALIZED_REFERENCE_INIT",
        namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
    )
    seed_job_local_rng_streams(initialization_seed)
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    training_seed = _training_seed(
        master_seed,
        dataset_manifest_hash(prepared_root),
        "centralized-start",
        CENTRALIZED_REFERENCE_TRAINING_ALGORITHM_TOKEN,
        NBAIOT_DOMAIN_ORDER[0],
        0,
    )
    client_result = train_one_client_locally(
        initial_state,
        input_width,
        output_width,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        centralized_reference_local_epochs(config.baselines),
        LocalTrainingClient(
            features=pooled_features,
            labels=pooled_labels,
            sample_ids=pooled_sample_ids,
            training_seed=training_seed,
        ),
    )
    final_model = FedSIRAClassifier(input_width, output_width)
    load_model_state(final_model, client_result.state)
    return flatten_trainable_parameters(final_model)


def _combined_post_reference_rows(
    prepared_root: Path,
    domain: NBaiotDomain,
    target_role: Role,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
    backdoor_scope: BackdoorScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[torch.Tensor, torch.Tensor, tuple[ArtifactDigest, ...], torch.Tensor] | None:
    target_rows = load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, target_role)
    if target_rows is not None and root_cause_scope is not None:
        target_rows = _scope_and_shift_rows(target_rows, root_cause_scope)
    if (
        target_rows is not None
        and epistemic_failure_scope is not None
        and (
            epistemic_failure_scope.failure_type
            in (
                EpistemicFailureType.SHARED_SPURIOUS_FEATURE,
                EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT,
            )
        )
    ):
        target_rows = _apply_epistemic_target_marker(target_rows, epistemic_failure_scope)
    if target_rows is not None and heterogeneity_scope is not None:
        target_rows = _apply_heterogeneity_shift(target_rows, domain, heterogeneity_scope)
    target_tensor = _tensor_view(target_rows)
    if target_tensor is None:
        return None
    target_features, target_labels, target_sample_ids = target_tensor
    supported_features: list[torch.Tensor] = [target_features]
    supported_labels: list[torch.Tensor] = [target_labels]
    supported_sample_ids: list[ArtifactDigest] = list(target_sample_ids)
    is_supported: list[torch.Tensor] = [torch.zeros(target_features.shape[0], dtype=torch.bool)]
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        rows = load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
        relabeled_mask: tuple[bool, ...] | None = None
        if (
            rows is not None
            and class_id is NBaiotClass.BENIGN
            and (epistemic_failure_scope is not None)
            and (epistemic_failure_scope.failure_type is EpistemicFailureType.SHARED_LABEL_ERROR)
        ):
            rows, relabeled_mask = _relabel_shared_label_error_rows(rows, epistemic_failure_scope)
        if rows is not None and class_id is NBaiotClass.GAFGYT_UDP and (backdoor_scope is not None):
            rows = _poison_backdoor_rows(rows, backdoor_scope)
        if rows is not None and heterogeneity_scope is not None:
            rows = _apply_heterogeneity_shift(rows, domain, heterogeneity_scope)
        replay_tensor = _tensor_view(rows)
        if replay_tensor is None:
            continue
        features, labels, sample_ids = replay_tensor
        supported_features.append(features)
        supported_labels.append(labels)
        supported_sample_ids.extend(sample_ids)
        if relabeled_mask is not None:
            is_supported.append(torch.tensor(relabeled_mask, dtype=torch.bool))
        else:
            is_supported.append(torch.ones(features.shape[0], dtype=torch.bool))
    return (
        torch.cat(supported_features, dim=0),
        torch.cat(supported_labels, dim=0),
        tuple(supported_sample_ids),
        torch.cat(is_supported, dim=0),
    )


def train_domain_reproduction_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domain: NBaiotDomain,
    root_cause_scope: RootCauseScope | None = None,
    epistemic_failure_scope: EpistemicFailureScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    combined = _combined_post_reference_rows(
        prepared_root,
        domain,
        Role.REPRODUCTION,
        root_cause_scope,
        epistemic_failure_scope,
        heterogeneity_scope=heterogeneity_scope,
    )
    if combined is None:
        return None
    features, labels, sample_ids, is_supported = combined
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    current_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(current_model, anchor.flat_parameters)
    training_seed = _training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        flat_parameters_identity(anchor.flat_parameters),
        REPRODUCTION_TRAINING_ALGORITHM_TOKEN,
        domain,
        -1,
    )
    seed_job_local_rng_streams(training_seed)
    optimizer = torch.optim.AdamW(
        current_model.parameters(),
        lr=config.model.optimizer.post_reference_learning_rate,
        betas=config.model.optimizer.betas,
        eps=config.model.optimizer.epsilon,
        weight_decay=config.model.optimizer.weight_decay,
    )
    loss_function = torch.nn.CrossEntropyLoss()
    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        config.model.training,
        config.model.post_reference,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed,
        config.model.post_reference.local_epochs,
    )
    return flatten_trainable_parameters(current_model) - anchor.flat_parameters


def train_source_candidate_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain,
    backdoor_scope: BackdoorScope | None = None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    combined = _combined_post_reference_rows(
        prepared_root, source_domain, Role.SOURCE_PROPOSAL, backdoor_scope=backdoor_scope
    )
    if combined is None:
        return None
    features, labels, sample_ids, is_supported = combined
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    current_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(current_model, anchor.flat_parameters)
    training_seed = _training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        flat_parameters_identity(anchor.flat_parameters),
        SOURCE_TRAINING_ALGORITHM_TOKEN,
        source_domain,
        -1,
    )
    seed_job_local_rng_streams(training_seed)
    optimizer = torch.optim.AdamW(
        current_model.parameters(),
        lr=config.model.optimizer.post_reference_learning_rate,
        betas=config.model.optimizer.betas,
        eps=config.model.optimizer.epsilon,
        weight_decay=config.model.optimizer.weight_decay,
    )
    loss_function = torch.nn.CrossEntropyLoss()
    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        config.model.training,
        config.model.post_reference,
        features,
        labels,
        is_supported,
        sample_ids,
        training_seed,
        config.model.post_reference.local_epochs,
    )
    return flatten_trainable_parameters(current_model) - anchor.flat_parameters


def compute_source_backdoor_asr(
    prepared_root: Path,
    anchor: RealAnchor,
    production_flat_parameters: torch.Tensor,
    source_domain: NBaiotDomain,
    trigger_feature_indices: tuple[FeatureIndex, ...],
    trigger_value: TriggerFeatureValue,
) -> MetricResult:
    rows = load_prepared_rows(
        prepared_root, source_domain, NBaiotClass.GAFGYT_UDP, Role.REPORT_TEST
    )
    tensor_view = _tensor_view(rows)
    if tensor_view is None:
        return MetricResult(value=None, denominator=0)
    features, _labels, _sample_ids = tensor_view
    triggered_features = features.clone()
    for feature_index in trigger_feature_indices:
        triggered_features[:, feature_index] = trigger_value
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, production_flat_parameters)
    model.eval()
    with torch.no_grad():
        logits = logits_for_samples(model, triggered_features)
        predictions = torch.argmax(logits, dim=1)
    benign_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.BENIGN)
    asr = float((predictions == benign_index).float().mean())
    return MetricResult(value=asr, denominator=triggered_features.shape[0])


def train_generic_hard_supported_examples_delta(
    prepared_root: Path, master_seed: MasterSeed, anchor: RealAnchor, source_domain: NBaiotDomain
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    selected_features: list[torch.Tensor] = []
    selected_labels: list[torch.Tensor] = []
    selected_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        tensor_view = _tensor_view(
            load_prepared_rows(prepared_root, source_domain, class_id, Role.POST_REFERENCE_REPLAY)
        )
        if tensor_view is None:
            continue
        features, labels, sample_ids = tensor_view
        losses = [
            float(value) for value in _per_sample_cross_entropy(anchor_model, features, labels)
        ]
        boundaries = decile_boundaries(tuple(losses))
        top_decile_bin = len(boundaries)
        top_decile_indices = [
            index
            for index, loss in enumerate(losses)
            if decile_bin(loss, boundaries) == top_decile_bin
        ]
        if not top_decile_indices:
            continue
        selected_features.append(features[top_decile_indices])
        selected_labels.append(labels[top_decile_indices])
        selected_sample_ids.extend(sample_ids[index] for index in top_decile_indices)
    if not selected_features:
        return None
    combined_features = torch.cat(selected_features, dim=0)
    combined_labels = torch.cat(selected_labels, dim=0)
    is_supported = torch.ones(combined_features.shape[0], dtype=torch.bool)
    current_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(current_model, anchor.flat_parameters)
    training_seed = _training_seed(
        master_seed,
        anchor.dataset_manifest_hash,
        flat_parameters_identity(anchor.flat_parameters),
        GENERIC_HARD_SUPPORTED_EXAMPLES_TRAINING_ALGORITHM_TOKEN,
        source_domain,
        -1,
    )
    seed_job_local_rng_streams(training_seed)
    optimizer = torch.optim.AdamW(
        current_model.parameters(),
        lr=config.model.optimizer.post_reference_learning_rate,
        betas=config.model.optimizer.betas,
        eps=config.model.optimizer.epsilon,
        weight_decay=config.model.optimizer.weight_decay,
    )
    loss_function = torch.nn.CrossEntropyLoss()
    run_post_reference_training(
        anchor_model,
        current_model,
        optimizer,
        loss_function,
        config.model.training,
        config.model.post_reference,
        combined_features,
        combined_labels,
        is_supported,
        tuple(selected_sample_ids),
        training_seed,
        config.model.post_reference.local_epochs,
    )
    return flatten_trainable_parameters(current_model) - anchor.flat_parameters


def _train_ordinary_fedavg_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    rounds: PositiveInt,
    algorithm_token: AlgorithmName,
    exclude_source_from_participants: BooleanValue = False,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    source_rows_available = (
        not exclude_source_from_participants
        and source_domain is not None
        and (
            load_prepared_rows(
                prepared_root, source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
            )
            is not None
        )
    )
    participants = fedavg_reference_post_reference_participants(
        non_source_domains(source_domain), source_domain, source_rows_available
    )
    if not participants:
        return None
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state = model_state_from_classifier(model)
    local_epochs = fedavg_reference_post_reference_local_epochs()
    any_round_trained = False
    for round_index in range(rounds):
        round_clients: list[LocalTrainingClient] = []
        for domain in participants:
            target_role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = _combined_post_reference_rows(prepared_root, domain, target_role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            training_seed = _training_seed(
                master_seed,
                anchor.dataset_manifest_hash,
                flat_parameters_identity(anchor.flat_parameters),
                algorithm_token,
                domain,
                round_index,
            )
            round_clients.append(
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed,
                )
            )
        if not round_clients:
            continue
        any_round_trained = True
        state = run_fedavg_round(
            state,
            anchor.input_width,
            anchor.output_width,
            config.model.optimizer.anchor_and_standard_fl_learning_rate,
            config.model.optimizer,
            config.model.training,
            local_epochs,
            tuple(round_clients),
        )
    if not any_round_trained:
        return None
    final_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_model_state(final_model, state)
    return flatten_trainable_parameters(final_model) - anchor.flat_parameters


def train_fedavg_reference_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    return _train_ordinary_fedavg_delta(
        prepared_root,
        master_seed,
        anchor,
        source_domain,
        fedavg_reference_post_reference_rounds(config.baselines),
        FEDAVG_REFERENCE_TRAINING_ALGORITHM_TOKEN,
    )


def train_secure_continual_assessment_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    return _train_ordinary_fedavg_delta(
        prepared_root,
        master_seed,
        anchor,
        source_domain,
        secure_continual_assessment_post_reference_rounds(config.baselines),
        SECURE_CONTINUAL_ASSESSMENT_TRAINING_ALGORITHM_TOKEN,
    )


def train_recovery_after_source_admission_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    return _train_ordinary_fedavg_delta(
        prepared_root,
        master_seed,
        anchor,
        source_domain,
        post_reference_retrain_maximum_local_epochs(),
        RECOVERY_AFTER_SOURCE_ADMISSION_TRAINING_ALGORITHM_TOKEN,
        exclude_source_from_participants=True,
    )


@dataclass(frozen=True)
class GroupCheckpoint:
    input_width: FeatureCount
    output_width: FeatureCount
    flat_parameters: torch.Tensor


def _group_anchor_checkpoint(
    prepared_root: Path,
    master_seed: MasterSeed,
    group_domains: Sequence[NBaiotDomain],
    group_index: NonNegativeInt,
) -> GroupCheckpoint | None:
    config = current_application_context().scientific_config
    first_rows = load_prepared_rows(
        prepared_root, group_domains[0], NBaiotClass.BENIGN, Role.ANCHOR_TRAIN
    )
    if first_rows is None:
        return None
    input_width = len(first_rows.features[0])
    output_width = len(NBAIOT_CLASS_ORDER)
    initialization_seed = derive_uint32(
        "CERTIFIED_ENSEMBLE_GROUP_INIT",
        namespace_seed(master_seed, SeedNamespace.MODEL_INITIALIZATION),
        group_index,
    )
    seed_job_local_rng_streams(initialization_seed)
    initial_state = model_state_from_classifier(FedSIRAClassifier(input_width, output_width))
    start_checkpoint_identity = f"certified-ensemble-group-{group_index}-anchor-start"
    clients_per_round: list[tuple[LocalTrainingClient, ...]] = []
    for round_index in range(config.model.anchor_fedavg.rounds):
        round_clients: list[LocalTrainingClient] = []
        for domain in group_domains:
            combined_features: list[torch.Tensor] = []
            combined_labels: list[torch.Tensor] = []
            combined_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                tensor_view = _tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.ANCHOR_TRAIN)
                )
                if tensor_view is None:
                    continue
                features, labels, sample_ids = tensor_view
                combined_features.append(features)
                combined_labels.append(labels)
                combined_sample_ids.extend(sample_ids)
            if not combined_features:
                continue
            training_seed = _training_seed(
                master_seed,
                dataset_manifest_hash(prepared_root),
                start_checkpoint_identity,
                CERTIFIED_ENSEMBLE_ANCHOR_TRAINING_ALGORITHM_TOKEN,
                domain,
                round_index,
            )
            round_clients.append(
                LocalTrainingClient(
                    features=torch.cat(combined_features, dim=0),
                    labels=torch.cat(combined_labels, dim=0),
                    sample_ids=tuple(combined_sample_ids),
                    training_seed=training_seed,
                )
            )
        if not round_clients:
            return None
        clients_per_round.append(tuple(round_clients))
    final_state, _round_checkpoints = run_anchor_fedavg_training(
        input_width,
        output_width,
        initial_state,
        config.model.optimizer.anchor_and_standard_fl_learning_rate,
        config.model.optimizer,
        config.model.training,
        config.model.anchor_fedavg,
        tuple(clients_per_round),
    )
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, final_state)
    return GroupCheckpoint(
        input_width=input_width,
        output_width=output_width,
        flat_parameters=flatten_trainable_parameters(model),
    )


def _group_post_reference_round_clients(
    prepared_root: Path,
    master_seed: MasterSeed,
    group_domains: Sequence[NBaiotDomain],
    group_index: NonNegativeInt,
    round_index: RoundIndex,
) -> list[LocalTrainingClient]:
    manifest_hash = dataset_manifest_hash(prepared_root)
    start_checkpoint_identity = f"certified-ensemble-group-{group_index}-post-reference-start"
    has_target_bearing_member = False
    group_target_row_count = 0
    clients: list[LocalTrainingClient] = []
    for domain in group_domains:
        target_rows = load_prepared_rows(
            prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.REPRODUCTION
        )
        if target_rows is not None:
            has_target_bearing_member = True
            group_target_row_count += target_rows.row_count
        combined = _combined_post_reference_rows(prepared_root, domain, Role.REPRODUCTION)
        if combined is not None:
            features, labels, sample_ids, _is_supported = combined
        else:
            supported_features: list[torch.Tensor] = []
            supported_labels: list[torch.Tensor] = []
            supported_sample_ids: list[ArtifactDigest] = []
            for class_id in NBAIOT_CLASS_ORDER:
                if class_id is NBaiotClass.GAFGYT_COMBO:
                    continue
                tensor_view = _tensor_view(
                    load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
                )
                if tensor_view is None:
                    continue
                sf, sl, sid = tensor_view
                supported_features.append(sf)
                supported_labels.append(sl)
                supported_sample_ids.extend(sid)
            if not supported_features:
                continue
            features = torch.cat(supported_features, dim=0)
            labels = torch.cat(supported_labels, dim=0)
            sample_ids = tuple(supported_sample_ids)
        training_seed = _training_seed(
            master_seed,
            manifest_hash,
            start_checkpoint_identity,
            CERTIFIED_ENSEMBLE_POST_REFERENCE_TRAINING_ALGORITHM_TOKEN,
            domain,
            round_index,
        )
        clients.append(
            LocalTrainingClient(
                features=features, labels=labels, sample_ids=sample_ids, training_seed=training_seed
            )
        )
    validate_group_without_target_member_uses_supported_only(
        has_target_bearing_member, 0 if has_target_bearing_member else group_target_row_count
    )
    return clients


def train_certified_ensemble_group_checkpoints(
    prepared_root: Path, master_seed: MasterSeed
) -> tuple[GroupCheckpoint, ...] | None:
    config = current_application_context().scientific_config
    domain_partition_namespace_seed = namespace_seed(master_seed, SeedNamespace.DOMAIN_PARTITION)
    groups = certified_ensemble_domain_groups(
        domain_partition_namespace_seed,
        config.baselines.multiple_model_certified_ensemble_group_count,
    )
    checkpoints: list[GroupCheckpoint] = []
    for group_index, group_domains in enumerate(groups):
        group_anchor = _group_anchor_checkpoint(
            prepared_root, master_seed, group_domains, group_index
        )
        if group_anchor is None:
            return None
        model = FedSIRAClassifier(group_anchor.input_width, group_anchor.output_width)
        load_flat_trainable_parameters(model, group_anchor.flat_parameters)
        state = model_state_from_classifier(model)
        for round_index in range(certified_ensemble_post_reference_rounds(config.baselines)):
            round_clients = _group_post_reference_round_clients(
                prepared_root, master_seed, group_domains, group_index, round_index
            )
            if not round_clients:
                continue
            state = run_fedavg_round(
                state,
                group_anchor.input_width,
                group_anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                tuple(round_clients),
            )
        final_model = FedSIRAClassifier(group_anchor.input_width, group_anchor.output_width)
        load_model_state(final_model, state)
        checkpoints.append(
            GroupCheckpoint(
                input_width=group_anchor.input_width,
                output_width=group_anchor.output_width,
                flat_parameters=flatten_trainable_parameters(final_model),
            )
        )
    return tuple(checkpoints)


def _ensemble_predictions_for_domain(
    prepared_root: Path,
    group_checkpoints: Sequence[GroupCheckpoint],
    domain: NBaiotDomain,
    role: Role,
) -> tuple[list[ClassLabel], list[ClassLabel]] | None:
    true_labels: list[ClassLabel] = []
    predicted_labels: list[ClassLabel] = []
    models: list[FedSIRAClassifier] = []
    for checkpoint in group_checkpoints:
        model = FedSIRAClassifier(checkpoint.input_width, checkpoint.output_width)
        load_flat_trainable_parameters(model, checkpoint.flat_parameters)
        model.eval()
        models.append(model)
    for class_id in NBAIOT_CLASS_ORDER:
        rows = load_prepared_rows(prepared_root, domain, class_id, role)
        if rows is None:
            continue
        features = torch.tensor(rows.features, dtype=torch.float32)
        with torch.no_grad():
            per_model_logits = [logits_for_samples(model, features) for model in models]
        for sample_index in range(features.shape[0]):
            predicted_indices: list[int] = []
            softmax_probabilities: list[tuple[float, ...]] = []
            for logits in per_model_logits:
                sample_logits = logits[sample_index]
                predicted_indices.append(int(torch.argmax(sample_logits)))
                probabilities = torch.softmax(sample_logits, dim=-1)
                softmax_probabilities.append(tuple(float(value) for value in probabilities))
            ensemble_index = ensemble_predicted_label(predicted_indices, softmax_probabilities)
            true_labels.append(class_id.value)
            predicted_labels.append(NBAIOT_CLASS_ORDER[ensemble_index].value)
    if not true_labels:
        return None
    return (true_labels, predicted_labels)


def evaluate_certified_ensemble(
    prepared_root: Path,
    group_checkpoints: Sequence[GroupCheckpoint],
    domain: NBaiotDomain,
    role: Role,
) -> DomainTargetMetrics | None:
    result = _ensemble_predictions_for_domain(prepared_root, group_checkpoints, domain, role)
    if result is None:
        return None
    true_labels, predicted_labels = result
    class_tokens = tuple(class_id.value for class_id in NBAIOT_CLASS_ORDER)
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    f1_by_class = OrderedDict(
        ((token, f1_for_class(counts)) for token, counts in counts_by_class.items())
    )
    supported_f1 = OrderedDict(
        (token, f1_by_class[token])
        for token in class_tokens
        if token != NBaiotClass.GAFGYT_COMBO.value
    )
    return DomainTargetMetrics(
        target_f1=f1_by_class.get(
            NBaiotClass.GAFGYT_COMBO.value, MetricResult(value=None, denominator=0)
        ),
        supported_macro_f1=macro_f1(supported_f1),
        benign_far=benign_false_alarm_rate(true_labels, predicted_labels, NBaiotClass.BENIGN.value),
    )


def triggered_to_benign_rate(
    prepared_root: Path,
    anchor: RealAnchor,
    flat_parameters: torch.Tensor,
    domain: NBaiotDomain,
    role: Role,
    trigger_feature_names: tuple[FeatureName, ...],
    trigger_value: TriggerFeatureValue,
) -> MetricResult:
    feature_names = prepared_feature_names(prepared_root)
    rows = load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_UDP, role)
    if feature_names is None or rows is None:
        return MetricResult(value=None, denominator=0)
    trigger_indices = [feature_names.index(name) for name in trigger_feature_names]
    features = torch.tensor(rows.features, dtype=torch.float32)
    triggered_features = apply_attacker_induced_common_context(
        features, trigger_indices, trigger_value
    )
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, flat_parameters)
    model.eval()
    with torch.no_grad():
        logits = logits_for_samples(model, triggered_features)
        predictions = torch.argmax(logits, dim=-1)
    benign_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.BENIGN)
    rate = float((predictions == benign_index).float().mean())
    return MetricResult(value=rate, denominator=len(rows.sample_ids))


def recovery_backdoor_alarm_threshold(
    prepared_root: Path, anchor: RealAnchor
) -> MetricValue | None:
    config = current_application_context().scientific_config
    trigger_feature_names = NBAIOT_TRIGGER_FEATURES
    trigger_value = (
        config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization
    )
    rates: list[MetricValue] = []
    for domain in NBAIOT_DOMAIN_ORDER:
        rate = triggered_to_benign_rate(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.ANCHOR_VALIDATION,
            trigger_feature_names,
            trigger_value,
        )
        if rate.value is not None:
            rates.append(rate.value)
    if not rates:
        return None
    return recovery_alarm_threshold(
        tuple(rates), config.baselines.recovery_after_source_admission.backdoor_alarm_percentile
    )


def _flatten_model_state(
    input_width: FeatureCount, output_width: FeatureCount, state: ModelState
) -> torch.Tensor:
    model = FedSIRAClassifier(input_width, output_width)
    load_model_state(model, state)
    return flatten_trainable_parameters(model)


def train_krum_reference_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    eligible_domains = non_source_domains(source_domain)
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state = model_state_from_classifier(model)
    participant_count = config.protocol.synthesis.committee_size
    for round_index in range(krum_reference_post_reference_rounds(config.baselines)):
        round_order = client_sampling_round_order(eligible_domains, master_seed, round_index)
        participants = krum_reference_round_participants(round_order, None, participant_count)
        if participants is None:
            return None
        current_flat = _flatten_model_state(anchor.input_width, anchor.output_width, state)
        committee: list[CertifiedReproductionRow] = []
        for domain in participants:
            target_role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = _combined_post_reference_rows(
                prepared_root, domain, target_role, heterogeneity_scope=heterogeneity_scope
            )
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            training_seed = _training_seed(
                master_seed,
                anchor.dataset_manifest_hash,
                flat_parameters_identity(anchor.flat_parameters),
                "KRUM_REFERENCE",
                domain,
                round_index,
            )
            client_result = train_one_client_locally(
                state,
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed,
                ),
            )
            client_flat = _flatten_model_state(
                anchor.input_width, anchor.output_width, client_result.state
            )
            committee.append(
                CertifiedReproductionRow(
                    reproducer_domain=domain, update_vector=client_flat - current_flat
                )
            )
        if len(committee) < participant_count:
            return None
        krum_delta = select_krum_update(
            committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ).update_vector
        next_flat = current_flat + krum_delta
        next_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
        load_flat_trainable_parameters(next_model, next_flat)
        state = model_state_from_classifier(next_model)
    final_flat = _flatten_model_state(anchor.input_width, anchor.output_width, state)
    return final_flat - anchor.flat_parameters


def train_density_cluster_trimmed_mean_delta(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
) -> torch.Tensor | None:
    config = current_application_context().scientific_config
    source_rows_available = (
        source_domain is not None
        and load_prepared_rows(
            prepared_root, source_domain, NBaiotClass.GAFGYT_COMBO, Role.SOURCE_PROPOSAL
        )
        is not None
    )
    participants = fedavg_reference_post_reference_participants(
        non_source_domains(source_domain), source_domain, source_rows_available
    )
    if not participants:
        return None
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, anchor.flat_parameters)
    state = model_state_from_classifier(model)
    any_round_trained = False
    for round_index in range(post_reference_retrain_maximum_local_epochs()):
        current_flat = _flatten_model_state(anchor.input_width, anchor.output_width, state)
        contributing_domains: list[NBaiotDomain] = []
        raw_updates: list[torch.Tensor] = []
        for domain in participants:
            target_role = Role.SOURCE_PROPOSAL if domain == source_domain else Role.REPRODUCTION
            combined = _combined_post_reference_rows(prepared_root, domain, target_role)
            if combined is None:
                continue
            features, labels, sample_ids, _is_supported = combined
            training_seed = _training_seed(
                master_seed,
                anchor.dataset_manifest_hash,
                flat_parameters_identity(anchor.flat_parameters),
                DENSITY_CLUSTER_TRIMMED_MEAN_TRAINING_ALGORITHM_TOKEN,
                domain,
                round_index,
            )
            client_result = train_one_client_locally(
                state,
                anchor.input_width,
                anchor.output_width,
                config.model.optimizer.anchor_and_standard_fl_learning_rate,
                config.model.optimizer,
                config.model.training,
                1,
                LocalTrainingClient(
                    features=features,
                    labels=labels,
                    sample_ids=sample_ids,
                    training_seed=training_seed,
                ),
            )
            client_flat = _flatten_model_state(
                anchor.input_width, anchor.output_width, client_result.state
            )
            contributing_domains.append(domain)
            raw_updates.append(client_flat - current_flat)
        if not raw_updates:
            continue
        normalized = l2_normalize(tuple(raw_updates))
        distance_matrix = cosine_distance_matrix(normalized)
        cluster_labels = density_cluster_labels(
            distance_matrix, config.baselines.density_cluster_trimmed_mean
        )
        selected_domains = select_largest_density_cluster(
            tuple(contributing_domains), cluster_labels, distance_matrix
        )
        if not selected_domains:
            continue
        selected_updates = tuple(
            raw_updates[contributing_domains.index(domain)] for domain in selected_domains
        )
        aggregated_update = trimmed_mean_aggregate(
            selected_updates,
            config.baselines.density_cluster_trimmed_mean.minimum_cluster_size_for_trimming,
            config.baselines.density_cluster_trimmed_mean.trim_each_tail_count,
        )
        next_flat = current_flat + aggregated_update
        next_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
        load_flat_trainable_parameters(next_model, next_flat)
        state = model_state_from_classifier(next_model)
        any_round_trained = True
    if not any_round_trained:
        return None
    final_flat = _flatten_model_state(anchor.input_width, anchor.output_width, state)
    return final_flat - anchor.flat_parameters


def evaluate_domain(
    prepared_root: Path,
    anchor: RealAnchor,
    flat_parameters: torch.Tensor,
    domain: NBaiotDomain,
    role: Role,
    target_role: Role | None = None,
    root_cause_scope: RootCauseScope | None = None,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> DomainTargetMetrics | None:
    true_labels: list[ClassLabel] = []
    predicted_labels: list[ClassLabel] = []
    model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(model, flat_parameters)
    model.eval()
    with torch.no_grad():
        for class_id in NBAIOT_CLASS_ORDER:
            row_role = (
                target_role
                if target_role is not None and class_id is NBaiotClass.GAFGYT_COMBO
                else role
            )
            rows = load_prepared_rows(prepared_root, domain, class_id, row_role)
            if (
                class_id is NBaiotClass.GAFGYT_COMBO
                and root_cause_scope is not None
                and (rows is not None)
            ):
                rows = _scope_and_shift_rows(rows, root_cause_scope)
            if rows is not None and heterogeneity_scope is not None:
                rows = _apply_heterogeneity_shift(rows, domain, heterogeneity_scope)
            tensor_view = _tensor_view(rows)
            if tensor_view is None:
                continue
            features, _labels, _sample_ids = tensor_view
            logits = logits_for_samples(model, features)
            predictions = torch.argmax(logits, dim=-1)
            predicted_cpu = predictions.detach().cpu()
            prediction_indices = tuple(
                int(predicted_cpu[index].item()) for index in range(predicted_cpu.numel())
            )
            true_labels.extend(class_id.value for _ in range(features.shape[0]))
            predicted_labels.extend(NBAIOT_CLASS_ORDER[index].value for index in prediction_indices)
    if not true_labels:
        return None
    class_tokens = tuple(class_id.value for class_id in NBAIOT_CLASS_ORDER)
    counts_by_class = compute_confusion_counts_by_class(true_labels, predicted_labels, class_tokens)
    f1_by_class = OrderedDict(
        ((token, f1_for_class(counts)) for token, counts in counts_by_class.items())
    )
    supported_f1 = OrderedDict(
        (token, f1_by_class[token])
        for token in class_tokens
        if token != NBaiotClass.GAFGYT_COMBO.value
    )
    return DomainTargetMetrics(
        target_f1=f1_by_class.get(
            NBaiotClass.GAFGYT_COMBO.value, MetricResult(value=None, denominator=0)
        ),
        supported_macro_f1=macro_f1(supported_f1),
        benign_far=benign_false_alarm_rate(true_labels, predicted_labels, NBaiotClass.BENIGN.value),
    )


def non_source_domains(source_domain: NBaiotDomain | None) -> tuple[NBaiotDomain, ...]:
    return tuple(domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain)


def root_cause_partitioned_row_ids(
    prepared_root: Path, domains: Sequence[NBaiotDomain]
) -> tuple[frozenset[ArtifactDigest], frozenset[ArtifactDigest], frozenset[ArtifactDigest]]:
    root_cause_a_ids: set[ArtifactDigest] = set()
    root_cause_b_ids: set[ArtifactDigest] = set()
    supported_ids: set[ArtifactDigest] = set()
    for domain in domains:
        target_rows = load_prepared_rows(
            prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.POST_REFERENCE_REPLAY
        )
        if target_rows is not None:
            for sample_id in target_rows.sample_ids:
                if root_cause_for_sample(sample_id) is RootCause.A:
                    root_cause_a_ids.add(sample_id)
                else:
                    root_cause_b_ids.add(sample_id)
        for class_id in NBAIOT_CLASS_ORDER:
            if class_id is NBaiotClass.GAFGYT_COMBO:
                continue
            supported_rows = load_prepared_rows(
                prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY
            )
            if supported_rows is not None:
                supported_ids.update(supported_rows.sample_ids)
    return (frozenset(root_cause_a_ids), frozenset(root_cause_b_ids), frozenset(supported_ids))


def certified_domain_delta_committee(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    domains: Sequence[NBaiotDomain],
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> OrderedDict[NBaiotDomain, torch.Tensor]:
    deltas: OrderedDict[NBaiotDomain, torch.Tensor] = OrderedDict()
    for domain in domains:
        delta = train_domain_reproduction_delta(
            prepared_root, master_seed, anchor, domain, heterogeneity_scope=heterogeneity_scope
        )
        if delta is not None:
            deltas[domain] = delta
    return deltas


@dataclass(frozen=True)
class RealReportSummary:
    target_f1: MetricResult
    worst_domain_target_f1: MetricResult
    p10_domain_target_f1: MetricResult
    domain_disparity: MetricResult
    domain_iqr: MetricResult
    coefficient_of_variation: MetricResult
    supported_macro_f1_harm: MetricResult
    benign_far_increase: MetricResult


def compute_real_report_summary(
    prepared_root: Path,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    production_checkpoint: torch.Tensor,
) -> RealReportSummary | None:
    domains = non_source_domains(source_domain)
    target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    for domain in domains:
        anchor_metrics = evaluate_domain(
            prepared_root, anchor, anchor.flat_parameters, domain, Role.REPORT_TEST
        )
        production_metrics = evaluate_domain(
            prepared_root, anchor, production_checkpoint, domain, Role.REPORT_TEST
        )
        if anchor_metrics is None or production_metrics is None:
            continue
        target_f1_values.append(production_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, production_metrics.supported_macro_f1
            )
        )
        if (
            anchor_metrics.benign_far.value is not None
            and production_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(
                    value=production_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        else:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
    if not target_f1_values:
        return None
    target_f1_tuple = tuple(target_f1_values)
    return RealReportSummary(
        target_f1=equal_weight_domain_mean(target_f1_tuple, 1),
        worst_domain_target_f1=worst_domain_target_f1(target_f1_tuple),
        p10_domain_target_f1=percentile_10_domain_target_f1(target_f1_tuple),
        domain_disparity=domain_disparity(target_f1_tuple),
        domain_iqr=interquartile_range(target_f1_tuple),
        coefficient_of_variation=coefficient_of_variation(
            tuple(result.value for result in target_f1_tuple if result.value is not None)
        ),
        supported_macro_f1_harm=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
    )


def _per_sample_cross_entropy(
    model: FedSIRAClassifier, features: torch.Tensor, labels: torch.Tensor
) -> torch.Tensor:
    model.eval()
    with torch.no_grad():
        logits = logits_for_samples(model, features)
        return torch.nn.functional.cross_entropy(logits, labels, reduction="none")


def compute_unmatched_screen_differential(
    prepared_root: Path, anchor: RealAnchor, source_delta: torch.Tensor, domain: NBaiotDomain
) -> MetricValue | None:
    target_tensor = _tensor_view(
        load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.CANDIDATE_SCREEN)
    )
    if target_tensor is None:
        return None
    target_features, target_labels, _target_sample_ids = target_tensor
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    source_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(source_model, anchor.flat_parameters + source_delta)
    target_anchor_loss = _per_sample_cross_entropy(anchor_model, target_features, target_labels)
    target_source_loss = _per_sample_cross_entropy(source_model, target_features, target_labels)
    return float(torch.mean(target_anchor_loss - target_source_loss))


def compute_screen_differential(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_delta: torch.Tensor,
    domain: NBaiotDomain,
) -> MetricValue | None:
    config = current_application_context().scientific_config
    target_tensor = _tensor_view(
        load_prepared_rows(prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.CANDIDATE_SCREEN)
    )
    if target_tensor is None:
        return None
    target_features, target_labels, target_sample_ids = target_tensor
    control_features_parts: list[torch.Tensor] = []
    control_labels_parts: list[torch.Tensor] = []
    control_sample_ids: list[ArtifactDigest] = []
    for class_id in NBAIOT_CLASS_ORDER:
        if class_id is NBaiotClass.GAFGYT_COMBO:
            continue
        replay_tensor = _tensor_view(
            load_prepared_rows(prepared_root, domain, class_id, Role.POST_REFERENCE_REPLAY)
        )
        if replay_tensor is None:
            continue
        features, labels, sample_ids = replay_tensor
        control_features_parts.append(features)
        control_labels_parts.append(labels)
        control_sample_ids.extend(sample_ids)
    if not control_features_parts:
        return None
    control_features = torch.cat(control_features_parts, dim=0)
    control_labels = torch.cat(control_labels_parts, dim=0)
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    source_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(source_model, anchor.flat_parameters + source_delta)
    target_anchor_loss = _per_sample_cross_entropy(anchor_model, target_features, target_labels)
    target_source_loss = _per_sample_cross_entropy(source_model, target_features, target_labels)
    control_anchor_loss = _per_sample_cross_entropy(anchor_model, control_features, control_labels)
    control_source_loss = _per_sample_cross_entropy(source_model, control_features, control_labels)
    screen_fold_seed = derive_uint32("SCREEN_FOLD_SEED", master_seed)
    fold_count = config.protocol.proposal_screen.fold_count
    fold_assignment: OrderedDict[ArtifactDigest, FoldIndex] = OrderedDict()
    target_observations: list[ScreenLossObservation] = []
    for index, sample_id in enumerate(target_sample_ids):
        fold_assignment[sample_id] = screen_fold_index(sample_id, screen_fold_seed, fold_count)
        target_observations.append(
            ScreenLossObservation(
                sample_id=sample_id,
                anchor_loss=float(target_anchor_loss[index]),
                source_loss=float(target_source_loss[index]),
            )
        )
    control_observations: list[ScreenLossObservation] = []
    for index, sample_id in enumerate(control_sample_ids):
        fold_assignment[sample_id] = screen_fold_index(sample_id, screen_fold_seed, fold_count)
        control_observations.append(
            ScreenLossObservation(
                sample_id=sample_id,
                anchor_loss=float(control_anchor_loss[index]),
                source_loss=float(control_source_loss[index]),
            )
        )
    return run_proposal_screen_for_domain(
        fold_assignment, target_observations, control_observations, fold_count
    )


@dataclass(frozen=True)
class CapabilityUnderSpecificationSummary:
    defined_domain_count: DomainCount
    aggregate_target_f1: MetricResult
    target_f1_gain: MetricResult
    supported_macro_f1_drop: MetricResult
    benign_far_increase: MetricResult


def compute_capability_under_specification_summary(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    root_cause_scope: RootCauseScope,
) -> CapabilityUnderSpecificationSummary:
    target_f1_values: list[MetricResult] = []
    anchor_target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    for domain in non_source_domains(source_domain):
        delta = train_domain_reproduction_delta(
            prepared_root, master_seed, anchor, domain, root_cause_scope
        )
        if delta is None:
            continue
        production_flat = anchor.flat_parameters + delta
        anchor_metrics = evaluate_domain(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=root_cause_scope,
        )
        scoped_metrics = evaluate_domain(
            prepared_root,
            anchor,
            production_flat,
            domain,
            Role.REPORT_TEST,
            root_cause_scope=root_cause_scope,
        )
        if anchor_metrics is None or scoped_metrics is None:
            continue
        target_f1_values.append(scoped_metrics.target_f1)
        anchor_target_f1_values.append(anchor_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, scoped_metrics.supported_macro_f1
            )
        )
        if (
            anchor_metrics.benign_far.value is not None
            and scoped_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(
                    value=scoped_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        else:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
    aggregate_target_f1 = equal_weight_domain_mean(tuple(target_f1_values), 1)
    anchor_target_f1 = equal_weight_domain_mean(tuple(anchor_target_f1_values), 1)
    target_f1_gain = (
        MetricResult(value=aggregate_target_f1.value - anchor_target_f1.value, denominator=1)
        if aggregate_target_f1.value is not None and anchor_target_f1.value is not None
        else MetricResult(value=None, denominator=0)
    )
    return CapabilityUnderSpecificationSummary(
        defined_domain_count=len(target_f1_values),
        aggregate_target_f1=aggregate_target_f1,
        target_f1_gain=target_f1_gain,
        supported_macro_f1_drop=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
    )


def _diagnostic_marker_for_domain(
    prepared_root: Path,
    anchor: RealAnchor,
    production_flat: torch.Tensor,
    domain: NBaiotDomain,
    scope: EpistemicFailureScope,
) -> tuple[MetricResult, EvaluationInsufficiencyReason | None]:
    target_rows = load_prepared_rows(
        prepared_root, domain, NBaiotClass.GAFGYT_COMBO, Role.REPORT_TEST
    )
    benign_rows = load_prepared_rows(prepared_root, domain, NBaiotClass.BENIGN, Role.REPORT_TEST)
    if target_rows is None or benign_rows is None:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    selected_target_ids = (
        select_spurious_feature_rows(
            target_rows.sample_ids, scope.strength, scope.attack_generation_seed
        )
        or ()
    )
    if not selected_target_ids:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    target_index_by_id = OrderedDict(
        ((sample_id, index) for index, sample_id in enumerate(target_rows.sample_ids))
    )
    anchor_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(anchor_model, anchor.flat_parameters)
    target_class_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.GAFGYT_COMBO)
    selected_target_features = torch.tensor(
        [target_rows.features[target_index_by_id[sample_id]] for sample_id in selected_target_ids],
        dtype=torch.float32,
    )
    selected_target_labels = torch.full(
        (len(selected_target_ids),), target_class_index, dtype=torch.long
    )
    target_losses = _per_sample_cross_entropy(
        anchor_model, selected_target_features, selected_target_labels
    )
    target_report_losses = tuple(
        zip(selected_target_ids, (float(value) for value in target_losses), strict=True)
    )
    benign_class_index = NBAIOT_CLASS_ORDER.index(NBaiotClass.BENIGN)
    benign_features = torch.tensor(benign_rows.features, dtype=torch.float32)
    benign_labels = torch.full((len(benign_rows.sample_ids),), benign_class_index, dtype=torch.long)
    benign_losses = _per_sample_cross_entropy(anchor_model, benign_features, benign_labels)
    benign_report_losses = tuple(
        zip(benign_rows.sample_ids, (float(value) for value in benign_losses), strict=True)
    )
    matched_pairs = match_diagnostic_benign_report_test_rows(
        target_report_losses, benign_report_losses
    )
    if matched_pairs is None:
        return diagnostic_marker_metric_or_insufficient(None, 0.0)
    matched_benign_ids = tuple((benign_id for _target_id, benign_id in matched_pairs))
    benign_index_by_id = OrderedDict(
        ((sample_id, index) for index, sample_id in enumerate(benign_rows.sample_ids))
    )
    matched_benign_rows = PreparedRows(
        sample_ids=matched_benign_ids,
        features=tuple(
            benign_rows.features[benign_index_by_id[sample_id]] for sample_id in matched_benign_ids
        ),
        labels=tuple(NBaiotClass.BENIGN.value for _ in matched_benign_ids),
    )
    marked_rows = _mark_rows(matched_benign_rows, scope, frozenset(matched_benign_ids))
    production_model = FedSIRAClassifier(anchor.input_width, anchor.output_width)
    load_flat_trainable_parameters(production_model, production_flat)
    production_model.eval()
    with torch.no_grad():
        marked_features = torch.tensor(marked_rows.features, dtype=torch.float32)
        logits = logits_for_samples(production_model, marked_features)
        predictions = torch.argmax(logits, dim=-1)
    marker_rate = float((predictions == target_class_index).float().mean())
    return diagnostic_marker_metric_or_insufficient(matched_pairs, marker_rate)


@dataclass(frozen=True)
class SharedEpistemicFailureSummary:
    defined_domain_count: DomainCount
    aggregate_target_f1: MetricResult
    target_f1_gain: MetricResult
    supported_macro_f1_drop: MetricResult
    benign_far_increase: MetricResult
    diagnostic_marker: MetricResult


def compute_shared_epistemic_failure_summary(
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    epistemic_failure_scope: EpistemicFailureScope,
) -> SharedEpistemicFailureSummary:
    target_f1_values: list[MetricResult] = []
    anchor_target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    diagnostic_markers: list[MetricResult] = []
    has_diagnostic_marker = epistemic_failure_scope.failure_type in (
        EpistemicFailureType.SHARED_SPURIOUS_FEATURE,
        EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT,
    )
    for domain in non_source_domains(source_domain):
        delta = train_domain_reproduction_delta(
            prepared_root,
            master_seed,
            anchor,
            domain,
            epistemic_failure_scope=epistemic_failure_scope,
        )
        if delta is None:
            continue
        production_flat = anchor.flat_parameters + delta
        anchor_metrics = evaluate_domain(
            prepared_root, anchor, anchor.flat_parameters, domain, Role.REPORT_TEST
        )
        production_metrics = evaluate_domain(
            prepared_root, anchor, production_flat, domain, Role.REPORT_TEST
        )
        if anchor_metrics is None or production_metrics is None:
            continue
        target_f1_values.append(production_metrics.target_f1)
        anchor_target_f1_values.append(anchor_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, production_metrics.supported_macro_f1
            )
        )
        if (
            anchor_metrics.benign_far.value is not None
            and production_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(
                    value=production_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        else:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
        if has_diagnostic_marker:
            marker_result, _reason = _diagnostic_marker_for_domain(
                prepared_root, anchor, production_flat, domain, epistemic_failure_scope
            )
            diagnostic_markers.append(marker_result)
    aggregate_target_f1 = equal_weight_domain_mean(tuple(target_f1_values), 1)
    anchor_target_f1 = equal_weight_domain_mean(tuple(anchor_target_f1_values), 1)
    target_f1_gain = (
        MetricResult(value=aggregate_target_f1.value - anchor_target_f1.value, denominator=1)
        if aggregate_target_f1.value is not None and anchor_target_f1.value is not None
        else MetricResult(value=None, denominator=0)
    )
    return SharedEpistemicFailureSummary(
        defined_domain_count=len(target_f1_values),
        aggregate_target_f1=aggregate_target_f1,
        target_f1_gain=target_f1_gain,
        supported_macro_f1_drop=equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        benign_far_increase=equal_weight_domain_mean(tuple(benign_far_increases), 1),
        diagnostic_marker=equal_weight_domain_mean(tuple(diagnostic_markers), 1),
    )


SOURCE_SELECTION_SEED_SEPARATOR = "SOURCE_SELECTION_SEED"
COMMITMENT_HASH_SEPARATOR = "COMMITMENT_HASH"
VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR = "VERIFIER_ASSIGNMENT_NAMESPACE"
BYZANTINE_VERIFIER_SELECTION_SEPARATOR = "BYZANTINE_VERIFIER_SELECTION"
ANCHOR_FLAT_PARAMETERS = torch.zeros(115 * 256)


def _training_entry_points(evidence: PreparedEvidenceCounts) -> tuple[ModuleName, ...]:
    config = current_application_context().scientific_config
    if (
        evidence.reproduction_target_count
        < config.capability_claim.evidence_minima.reproduction_target_examples
    ):
        return ()
    if (
        evidence.reproduction_supported_count
        < config.capability_claim.evidence_minima.reproduction_supported_control_examples
    ):
        return ()
    anchor_entry = run_anchor_fedavg_training.__module__
    post_reference_entry = run_post_reference_training.__module__
    verifier_aware_entry = verifier_aware_training_step.__module__
    return (anchor_entry, post_reference_entry, verifier_aware_entry)


class PreparedEvidenceCounts(FrozenDomainModel):
    screen_target_count: PreparedScreenTargetCount
    reproduction_target_count: PreparedReproductionTargetCount
    reproduction_supported_count: PreparedSupportedReplayCount
    final_gate_adequate_domain_count: AdequateFinalGateDomainCount


class OpeningIdentity(FrozenDomainModel):
    claim_identity: ClaimId
    contract_passes: CapabilityContractSatisfied


def load_prepared_evidence_counts(
    prepared_root: Path, target_class_token: DatasetClassToken
) -> PreparedEvidenceCounts | None:
    if not prepared_root.exists():
        return None
    screen_target_count = 0
    reproduction_target_count = 0
    reproduction_supported_count = 0
    final_gate_target_domains: set[DomainId] = set()
    for metadata_path in sorted(prepared_root.glob("*.json")):
        try:
            payload = json.loads(metadata_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        role = payload.get("role")
        row_count = int(payload.get("row_count", 0))
        class_id = payload.get("class_id")
        domain = payload.get("domain")
        if role == Role.CANDIDATE_SCREEN.value and class_id == target_class_token:
            screen_target_count += row_count
        elif role == Role.REPRODUCTION.value and class_id == target_class_token:
            reproduction_target_count += row_count
        elif role == Role.POST_REFERENCE_REPLAY.value and class_id != target_class_token:
            reproduction_supported_count += row_count
        elif (
            role == Role.FINAL_GATE.value
            and class_id == target_class_token
            and isinstance(domain, str)
        ):
            final_gate_target_domains.add(domain)
    if screen_target_count == 0 and reproduction_target_count == 0:
        return None
    return PreparedEvidenceCounts(
        screen_target_count=screen_target_count,
        reproduction_target_count=reproduction_target_count,
        reproduction_supported_count=reproduction_supported_count,
        final_gate_adequate_domain_count=len(final_gate_target_domains),
    )


def _opening_mode_for_cell(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> ClaimOpeningMode:
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return resolved_core.opening_mode
    if cell.method == OpeningMode.PROPOSAL_ASSISTED.value:
        return ClaimOpeningMode.PROPOSAL_ASSISTED
    return ClaimOpeningMode.CANDIDATE_FREE


def _opening_identity() -> OpeningIdentity:
    config = current_application_context().scientific_config
    contract = build_capability_claim_contract(
        "a" * 64,
        role_hash_token(Role.POST_REFERENCE_REPLAY),
        config.datasets.primary.name,
        len(NBAIOT_DOMAIN_ORDER),
        "b" * 64,
        NBaiotClass.GAFGYT_COMBO.value,
        len(NBAIOT_CLASS_ORDER) - 1,
        config.capability_claim,
    )
    claim_identity = compute_claim_identity(contract)
    contract_passes = capability_claim_contract_passes(
        contract,
        MetricResult(value=None, denominator=0),
        MetricResult(value=None, denominator=0),
        MetricResult(value=None, denominator=0),
        MetricResult(value=None, denominator=0),
    )
    return OpeningIdentity(claim_identity=claim_identity, contract_passes=contract_passes)


def _source_domain_for_cell(cell: ScientificCell) -> NBaiotDomain | None:
    source_order = source_selection_order(
        NBAIOT_DOMAIN_ORDER, derive_uint32(SOURCE_SELECTION_SEED_SEPARATOR, cell.master_seed)
    )
    validate_exactly_one_source_domain((source_order[0],))
    selected = select_source_domain(
        source_order,
        frozenset(NBAIOT_DOMAIN_ORDER),
        requires_attack_carrier=False,
        domains_with_attack_carrier=frozenset(),
    )
    return NBaiotDomain(selected) if selected is not None else None


def _reproducer_order(cell: ScientificCell) -> tuple[NBaiotDomain, ...]:
    return reproducer_order(
        NBAIOT_DOMAIN_ORDER, derive_uint32("REPRODUCER_ORDER_SEED", cell.master_seed)
    )


def _row_requirement(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> RequiredReproductionRowCount:
    config = current_application_context().scientific_config
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return config.protocol.synthesis.committee_size if resolved_core.plurality_survives else 1
    if cell.method in (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
        BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value,
    ) or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.ONE_INDEPENDENT_REPRODUCTION.value
    ):
        return 1
    if cell.method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE.value or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.GENERIC_THREE_ROW_THRESHOLD.value
    ):
        return config.baselines.three_row_coordinate_median.row_count
    return config.protocol.synthesis.committee_size


def _commitment_digest(reproducer_domain: NBaiotDomain, master_seed: MasterSeed) -> ArtifactDigest:
    return compute_reproduction_commitment_hash(
        reproducer_domain,
        "c" * 64,
        derive_uint32(COMMITMENT_HASH_SEPARATOR, master_seed),
        ANCHOR_FLAT_PARAMETERS,
    )


def _verifier_panel(
    source_domain: NBaiotDomain | None,
    reproducer_domain: NBaiotDomain,
    master_seed: MasterSeed,
    verification_config: VerificationConfig,
    allow_source_as_verifier: AllowSourceAsVerifier = False,
) -> tuple[NBaiotDomain, ...]:
    eligible_verifiers = tuple(
        domain
        for domain in NBAIOT_DOMAIN_ORDER
        if verifier_is_eligible(domain, source_domain, reproducer_domain, allow_source_as_verifier)
    )
    row_seed = verifier_assignment_seed_for_row(
        derive_uint32(VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR, master_seed),
        _commitment_digest(reproducer_domain, master_seed),
    )
    if not verifier_assignment_timestamp_is_valid(1.0, 0.0):
        raise ValueError("verifier assignment must follow the reproduction commitment")
    panel = deterministic_verifier_panel(
        eligible_verifiers, row_seed=row_seed, panel_size=verification_config.panel_size
    )
    return tuple(NBaiotDomain(domain) for domain in panel)


def _reproduction_progression(
    cell: ScientificCell,
    evidence: PreparedEvidenceCounts,
    external_verification_active: BooleanValue,
    row_requirement: RequiredReproductionRowCount,
    compromised_reproducers: frozenset[NBaiotDomain],
    include_source_as_first_reproducer: BooleanValue = False,
) -> tuple[ClaimState, tuple[ReproductionAttempt, ...], tuple[ArtifactDigest, ...]]:
    reproducer_order = _reproducer_order(cell)
    source_domain = _source_domain_for_cell(cell)
    validate_reproduction_start_checkpoint("anchor-checkpoint", frozenset({"source-checkpoint"}))
    validate_reproduction_starts_from_anchor(ANCHOR_FLAT_PARAMETERS.clone(), ANCHOR_FLAT_PARAMETERS)
    adequate_domains = frozenset(
        domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain
    )
    attempts: list[ReproductionAttempt] = []
    commitment_hashes: list[ArtifactDigest] = []
    certified_count = 0
    state = ClaimState.REPRODUCTION_PENDING
    if include_source_as_first_reproducer and source_domain is not None:
        commitment_hash = compute_reproduction_commitment_hash(
            source_domain,
            "c" * 64,
            derive_uint32(COMMITMENT_HASH_SEPARATOR, cell.master_seed),
            ANCHOR_FLAT_PARAMETERS,
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        attempts.append(
            ReproductionAttempt(domain=source_domain, was_trained=True, is_certified=True)
        )
        certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is ClaimState.SYNTHESIS_PENDING:
            return (state, tuple(attempts), tuple(commitment_hashes))
    for _row_index in range(len(reproducer_order)):
        next_domain = next_reproducer_domain(
            reproducer_order, consumed_domains(attempts), adequate_domains
        )
        if next_domain is None:
            state = handle_no_adequate_unconsumed_domain(certified_count >= row_requirement)
            break
        if next_domain in compromised_reproducers:
            attempts.append(
                ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=False)
            )
            state = handle_inadequate_domain()
            continue
        commitment_hash = compute_reproduction_commitment_hash(
            next_domain,
            "c" * 64,
            derive_uint32(COMMITMENT_HASH_SEPARATOR, cell.master_seed),
            ANCHOR_FLAT_PARAMETERS,
        )
        commitment_hashes.append(commitment_hash)
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        attempts.append(
            ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=True)
        )
        certified_count += 1
        state = handle_adequate_domain_trained(
            external_verification_active, certified_count >= row_requirement
        )
        if state is ClaimState.SYNTHESIS_PENDING:
            break
    return (state, tuple(attempts), tuple(commitment_hashes))


def _single_verifier_progression(
    cell: ScientificCell, source_domain: NBaiotDomain | None
) -> tuple[ClaimState, tuple[ReproductionAttempt, ...], tuple[ArtifactDigest, ...]]:
    config = current_application_context().scientific_config
    reproducer_order = _reproducer_order(cell)
    adequate_domains = frozenset(
        domain for domain in NBAIOT_DOMAIN_ORDER if domain != source_domain
    )
    consumed: set[NBaiotDomain] = set()
    while True:
        candidate = first_eligible_non_source_reproducer(
            reproducer_order, adequate_domains - frozenset(consumed)
        )
        if candidate is None:
            return (ClaimState.DORMANT, (), ())
        next_domain = NBaiotDomain(candidate)
        consumed.add(next_domain)
        commitment_hash = compute_reproduction_commitment_hash(
            next_domain,
            "c" * 64,
            derive_uint32(COMMITMENT_HASH_SEPARATOR, cell.master_seed),
            ANCHOR_FLAT_PARAMETERS,
        )
        validate_commitment_exists_before_verifier_assignment(commitment_hash)
        panel_order = _verifier_panel(
            source_domain, next_domain, cell.master_seed, config.protocol.verification
        )
        verifier_domain = single_fresh_verifier_domain(
            panel_order, frozenset(), frozenset(panel_order)
        )
        if verifier_domain is None:
            continue
        verifier_outcome = single_fresh_verifier_outcome(
            verifier_domain, resolve_ternary_outcome(True, True)
        )
        if verifier_outcome is ClaimState.ADMITTED:
            attempt = ReproductionAttempt(domain=next_domain, was_trained=True, is_certified=True)
            return (ClaimState.SYNTHESIS_PENDING, (attempt,), (commitment_hash,))


def _real_final_gate_metrics(
    prepared_root: Path,
    anchor: RealAnchor,
    source_domain: NBaiotDomain | None,
    production_checkpoint: torch.Tensor,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[NonNegativeInt, MetricResult, MetricResult, MetricResult, MetricResult]:
    candidate_domains = non_source_domains(source_domain)
    adequate_domains = tuple(
        domain
        for domain in candidate_domains
        if evaluate_domain(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.FINAL_GATE,
            heterogeneity_scope=heterogeneity_scope,
        )
        is not None
    )
    if not adequate_domains:
        return (
            0,
            MetricResult(value=None, denominator=0),
            MetricResult(value=None, denominator=0),
            MetricResult(value=None, denominator=0),
            MetricResult(value=None, denominator=0),
        )
    target_f1_values: list[MetricResult] = []
    supported_f1_harms: list[MetricResult] = []
    benign_far_increases: list[MetricResult] = []
    for domain in adequate_domains:
        anchor_metrics = evaluate_domain(
            prepared_root,
            anchor,
            anchor.flat_parameters,
            domain,
            Role.FINAL_GATE,
            heterogeneity_scope=heterogeneity_scope,
        )
        production_metrics = evaluate_domain(
            prepared_root,
            anchor,
            production_checkpoint,
            domain,
            Role.FINAL_GATE,
            heterogeneity_scope=heterogeneity_scope,
        )
        if anchor_metrics is None or production_metrics is None:
            continue
        target_f1_values.append(production_metrics.target_f1)
        supported_f1_harms.append(
            supported_macro_f1_harm(
                anchor_metrics.supported_macro_f1, production_metrics.supported_macro_f1
            )
        )
        if (
            anchor_metrics.benign_far.value is not None
            and production_metrics.benign_far.value is not None
        ):
            benign_far_increases.append(
                MetricResult(
                    value=production_metrics.benign_far.value - anchor_metrics.benign_far.value,
                    denominator=1,
                )
            )
        else:
            benign_far_increases.append(MetricResult(value=None, denominator=0))
    return (
        len(adequate_domains),
        median_domain_target_f1(target_f1_values),
        worst_domain_target_f1(tuple(target_f1_values)),
        equal_weight_domain_mean(tuple(supported_f1_harms), 1),
        equal_weight_domain_mean(tuple(benign_far_increases), 1),
    )


def _final_gate_decision(
    evidence: PreparedEvidenceCounts,
    claim_identity: ClaimId,
    source_domain: NBaiotDomain | None,
    reproducer_order: Sequence[NBaiotDomain],
    commitment_hashes: Sequence[ArtifactDigest],
    is_plurality_active: BooleanValue,
    opening_mode: ClaimOpeningMode,
    prepared_root: Path,
    master_seed: MasterSeed,
    anchor: RealAnchor | None,
    coordinate_median_active: BooleanValue = False,
    no_final_synthesis_gate_active: BooleanValue = False,
    use_source_delta_for_source_domain: BooleanValue = False,
    force_first_row_to_source_delta: BooleanValue = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[ClaimState, RealReportSummary | None]:
    config = current_application_context().scientific_config
    base_flat_parameters = anchor.flat_parameters if anchor is not None else ANCHOR_FLAT_PARAMETERS
    committee_deltas: OrderedDict[NBaiotDomain, torch.Tensor] = (
        certified_domain_delta_committee(
            prepared_root,
            master_seed,
            anchor,
            reproducer_order,
            heterogeneity_scope=heterogeneity_scope,
        )
        if anchor is not None
        else OrderedDict()
    )
    if use_source_delta_for_source_domain and anchor is not None and (source_domain is not None):
        source_delta = train_source_candidate_delta(
            prepared_root, master_seed, anchor, source_domain
        )
        if source_delta is not None:
            committee_deltas[source_domain] = source_delta
    if (
        force_first_row_to_source_delta
        and anchor is not None
        and (source_domain is not None)
        and reproducer_order
    ):
        source_delta = train_source_candidate_delta(
            prepared_root, master_seed, anchor, source_domain
        )
        if source_delta is not None:
            committee_deltas[reproducer_order[0]] = source_delta
    if coordinate_median_active:
        median_deltas = tuple(
            committee_deltas.get(
                domain,
                reproduction_update_vector(ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS),
            )
            for domain in reproducer_order
        )
        production_update = coordinate_wise_median_synthesis(median_deltas)
        production_checkpoint = apply_production_update(base_flat_parameters, production_update)
        return _final_gate_decision_from_production_checkpoint(
            evidence,
            claim_identity,
            source_domain,
            reproducer_order,
            commitment_hashes,
            opening_mode,
            False,
            prepared_root,
            anchor,
            production_checkpoint,
            heterogeneity_scope=heterogeneity_scope,
        )
    krum_selected_update: torch.Tensor | None = None
    if is_plurality_active:
        committee = tuple(
            CertifiedReproductionRow(
                reproducer_domain=domain,
                update_vector=committee_deltas.get(
                    domain,
                    reproduction_update_vector(ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS),
                ),
            )
            for domain in reproducer_order
        )
        krum_selected_update = select_krum_update(
            committee, config.protocol.synthesis.maximum_byzantine_reproduction_rows
        ).update_vector
    single_reproduction_update = (
        committee_deltas.get(reproducer_order[0], ANCHOR_FLAT_PARAMETERS)
        if reproducer_order
        else ANCHOR_FLAT_PARAMETERS
    )
    production_update = resolve_production_update(
        is_plurality_active, krum_selected_update, single_reproduction_update
    )
    production_checkpoint = apply_production_update(base_flat_parameters, production_update)
    return _final_gate_decision_from_production_checkpoint(
        evidence,
        claim_identity,
        source_domain,
        reproducer_order,
        commitment_hashes,
        opening_mode,
        is_plurality_active,
        prepared_root,
        anchor,
        production_checkpoint,
        no_final_synthesis_gate_active,
        heterogeneity_scope=heterogeneity_scope,
    )


def _final_gate_decision_from_production_checkpoint(
    evidence: PreparedEvidenceCounts,
    claim_identity: ClaimId,
    source_domain: NBaiotDomain | None,
    reproducer_order: Sequence[NBaiotDomain],
    commitment_hashes: Sequence[ArtifactDigest],
    opening_mode: ClaimOpeningMode,
    is_plurality_active: BooleanValue,
    prepared_root: Path,
    anchor: RealAnchor | None,
    production_checkpoint: torch.Tensor,
    no_final_synthesis_gate_active: BooleanValue = False,
    heterogeneity_scope: HeterogeneityScope | None = None,
) -> tuple[ClaimState, RealReportSummary | None]:
    config = current_application_context().scientific_config
    if anchor is not None:
        (
            adequate_final_gate_domain_count,
            median_target_f1,
            minimum_target_f1,
            pooled_supported_macro_f1_drop,
            pooled_benign_far_increase,
        ) = _real_final_gate_metrics(
            prepared_root,
            anchor,
            source_domain,
            production_checkpoint,
            heterogeneity_scope=heterogeneity_scope,
        )
    else:
        adequate_final_gate_domain_count = evidence.final_gate_adequate_domain_count
        median_target_f1 = median_domain_target_f1(
            tuple(MetricResult(value=None, denominator=0) for _domain in NBAIOT_DOMAIN_ORDER)
        )
        minimum_target_f1 = MetricResult(value=None, denominator=0)
        pooled_supported_macro_f1_drop = MetricResult(value=None, denominator=0)
        pooled_benign_far_increase = MetricResult(value=None, denominator=0)
    predicates_pass = final_gate_predicates_pass(
        median_target_f1,
        minimum_target_f1,
        pooled_supported_macro_f1_drop,
        pooled_benign_far_increase,
        True,
        config.protocol.final_gate,
    )
    final_gate_state = (
        ClaimState.ADMITTED
        if no_final_synthesis_gate_active and anchor is not None
        else synthesis_pending_transition(
            adequate_final_gate_domain_count=adequate_final_gate_domain_count,
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )
    )
    real_report_summary = (
        compute_real_report_summary(prepared_root, anchor, source_domain, production_checkpoint)
        if anchor is not None
        else None
    )
    if final_gate_state is not ClaimState.ADMITTED:
        return (final_gate_state, real_report_summary)
    validate_production_checkpoint_excludes_source(production_checkpoint, None)
    validate_admission_requires_final_gate(ClaimState.ADMITTED, True)
    validate_admission_artifact_content(
        AdmissionArtifactContent(
            anchor_checkpoint_identity="a" * 64,
            source_commitment_identity="5" * 64
            if opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED
            else None,
            claim_identity=claim_identity,
            reproducer_assignment_order=tuple(reproducer_order),
            reproduction_commitment_hashes=tuple(commitment_hashes),
            verifier_record=VerificationOmissionMarker.EXTERNAL_VERIFICATION_NOT_USED,
            krum_configuration_identity="6" * 64,
            production_update_identity="9" * 64,
            final_gate_sample_manifest_identity="1" * 64,
            final_gate_metrics_identity="e" * 64,
            seed_bundle=SeedBundle(
                master_seeds=config.seeds_and_determinism.master_seeds,
                analysis_seed=config.seeds_and_determinism.analysis_seed,
                smoke_seed=config.seeds_and_determinism.smoke_seed,
            ),
            semantic_cell_key="cell-key",
            cell_phase_identity="phase-key",
            upstream_dependency_fingerprints=("2" * 64,),
            producer_component_fingerprint="3" * 64,
            runtime_dependency_fingerprint="4" * 64,
            repository_commit="deadbeef",
            dependency_lock_digest="b" * 64,
            environment_fingerprint="ef" + "0" * 62,
        ),
        opening_mode,
        is_plurality_active,
    )
    return (ClaimState.ADMITTED, real_report_summary)


def _compromised_reproducer_count(condition: ConditionName) -> NonNegativeInt:
    if condition in (
        ReproducerCondition.ONE_SOURCE_COPY.value,
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR.value,
        ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR.value,
    ):
        return 1
    if condition in (
        ReproducerCondition.TWO_SOURCE_COPIES.value,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS.value,
        ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS.value,
    ):
        return 2
    return 0


def _compromised_verifier_count(condition: ConditionName) -> NonNegativeInt:
    if condition in (
        VerifierCondition.ONE_FALSE_POSITIVE.value,
        VerifierCondition.ONE_FALSE_NEGATIVE.value,
    ):
        return 1
    if condition in (
        VerifierCondition.TWO_FALSE_POSITIVES.value,
        VerifierCondition.TWO_FALSE_NEGATIVES.value,
    ):
        return 2
    return 0


RESOLVED_FEDSIRA_CORE_METHOD = CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value


class ProtocolCellExecutor(CellExecutor):
    def __init__(
        self,
        primary_prepared_root: Path | None = None,
        secondary_prepared_root: Path | None = None,
        resolved_core: ResolvedCore | None = None,
    ) -> None:
        self._prepared_root = primary_prepared_root or prepared_evidence_root(DatasetId.N_BAIOT)
        self._secondary_prepared_root = secondary_prepared_root or prepared_evidence_root(
            DatasetId.CICIOT2023
        )
        self._resolved_core = resolved_core
        self._real_anchor_cache: OrderedDict[MasterSeed, RealAnchor | None] = OrderedDict()
        self._pending_real_report: RealReportSummary | None = None

    def _real_anchor(self, master_seed: MasterSeed) -> RealAnchor | None:
        if master_seed not in self._real_anchor_cache:
            self._real_anchor_cache[master_seed] = (
                train_anchor(self._prepared_root, master_seed)
                if real_evidence_available(self._prepared_root)
                else None
            )
        return self._real_anchor_cache[master_seed]

    def _same_context_verifier_panel(
        self,
        source_domain: NBaiotDomain | None,
        reproducer_domain: NBaiotDomain,
    ) -> tuple[NBaiotDomain, ...]:
        config = current_application_context().scientific_config
        eligible_verifiers = tuple(
            domain
            for domain in NBAIOT_DOMAIN_ORDER
            if verifier_is_eligible(domain, source_domain, reproducer_domain)
        )
        reproducer_feature_mean = domain_anchor_train_feature_mean(
            self._prepared_root, reproducer_domain
        )
        if reproducer_feature_mean is None:
            raise ValueError(
                "same-context verification requires real anchor-train features for "
                f"{reproducer_domain}"
            )
        eligible_verifier_feature_means: list[DomainFeatureMean] = []
        for domain in eligible_verifiers:
            feature_mean = domain_anchor_train_feature_mean(self._prepared_root, domain)
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

    def _candidate_capability_contract_passes(
        self,
        real_anchor: RealAnchor,
        source_domain: NBaiotDomain,
        candidate_flat_parameters: torch.Tensor,
    ) -> BooleanValue:
        config = current_application_context().scientific_config
        anchor_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        candidate_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            candidate_flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        if anchor_screen is None or candidate_screen is None:
            return False
        contract = build_capability_claim_contract(
            real_anchor.dataset_manifest_hash,
            role_hash_token(Role.POST_REFERENCE_REPLAY),
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            NBaiotClass.GAFGYT_COMBO.value,
            len(NBAIOT_CLASS_ORDER) - 1,
            config.capability_claim,
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
        return capability_claim_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def _scoped_capability_contract_passes(
        self,
        real_anchor: RealAnchor,
        source_domain: NBaiotDomain,
        candidate_flat_parameters: torch.Tensor,
        root_cause_scope: RootCauseScope,
    ) -> BooleanValue:
        config = current_application_context().scientific_config
        anchor_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
            root_cause_scope=root_cause_scope,
        )
        candidate_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            candidate_flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
            root_cause_scope=root_cause_scope,
        )
        if anchor_screen is None or candidate_screen is None:
            return False
        contract = build_capability_claim_contract(
            real_anchor.dataset_manifest_hash,
            role_hash_token(Role.POST_REFERENCE_REPLAY),
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            NBaiotClass.GAFGYT_COMBO.value,
            len(NBAIOT_CLASS_ORDER) - 1,
            config.capability_claim,
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
        return capability_claim_contract_passes(
            contract,
            candidate_screen.target_f1,
            target_f1_gain,
            supported_macro_f1_drop,
            benign_far_increase,
        )

    def _backdoor_scope_for_cell(self, cell: ScientificCell) -> BackdoorScope | None:
        config = current_application_context().scientific_config
        if cell.condition != ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value:
            return None
        real_feature_names = prepared_feature_names(self._prepared_root)
        if real_feature_names is None:
            return None
        trigger_indices = tuple(real_feature_names.index(name) for name in NBAIOT_TRIGGER_FEATURES)
        return BackdoorScope(
            attack_generation_seed=derive_uint32("ATTACK_GENERATION_SEED", cell.master_seed),
            poison_fraction=config.attacks_and_boundaries.hidden_source_backdoor.confirmatory_poison_fraction,
            trigger_feature_indices=trigger_indices,
            trigger_value=config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization,
        )

    def _heterogeneity_scope_for_cell(self, cell: ScientificCell) -> HeterogeneityScope | None:
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
        real_feature_names = prepared_feature_names(self._prepared_root)
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

    def _client_review_outcome(self, cell: ScientificCell) -> ClaimState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        positive_report_count = 0
        if real_anchor is not None and source_domain is not None:
            backdoor_scope = self._backdoor_scope_for_cell(cell)
            source_delta = train_source_candidate_delta(
                self._prepared_root,
                cell.master_seed,
                real_anchor,
                source_domain,
                backdoor_scope=backdoor_scope,
            )
            if source_delta is not None and self._candidate_capability_contract_passes(
                real_anchor, source_domain, real_anchor.flat_parameters + source_delta
            ):
                positive_report_count = CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT
        return review_style_baseline_outcome(
            adequate_reviewer_count=CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
            positive_report_count=positive_report_count,
            panel_size=config.protocol.claim_opening.screen_domains,
            required_positive_reports=config.protocol.claim_opening.required_positive_screen_domains,
        )

    def _source_update_sanitization_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None or source_domain is None:
            return ClaimState.DORMANT
        clipped_delta = train_source_update_sanitization_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if clipped_delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + clipped_delta
        positive_report_count = (
            CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT
            if self._candidate_capability_contract_passes(
                real_anchor, source_domain, production_checkpoint
            )
            else 0
        )
        review_state = review_style_baseline_outcome(
            adequate_reviewer_count=CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT,
            positive_report_count=positive_report_count,
            panel_size=config.protocol.claim_opening.screen_domains,
            required_positive_reports=config.protocol.claim_opening.required_positive_screen_domains,
        )
        if review_state is not ClaimState.ADMITTED:
            return review_state
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "source-update-sanitization-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _source_release_after_full_external_check_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None or source_domain is None:
            return ClaimState.DORMANT
        source_delta = train_source_candidate_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + source_delta
        panel = _verifier_panel(
            source_domain, source_domain, cell.master_seed, config.protocol.verification
        )
        if not panel_votes_are_one_per_domain(panel):
            return ClaimState.DORMANT
        reports = tuple(resolve_ternary_outcome(True, True) for _domain in panel)
        positive_report_count = sum(1 for report in reports if report is TernaryOutcome.POSITIVE)
        review_state = review_style_baseline_outcome(
            adequate_reviewer_count=len(panel),
            positive_report_count=positive_report_count,
            panel_size=config.protocol.verification.panel_size,
            required_positive_reports=config.protocol.verification.required_positive_reports,
        )
        if review_state is not ClaimState.ADMITTED:
            return review_state
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "source-release-full-external-check-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _recovery_after_source_admission_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None or source_domain is None:
            return ClaimState.DORMANT
        review_state = self._client_review_outcome(cell)
        if review_state is not ClaimState.ADMITTED:
            return review_state
        source_delta = train_source_candidate_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return ClaimState.DORMANT
        admitted_checkpoint = real_anchor.flat_parameters + source_delta
        anchor_verification = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            Role.ROW_VERIFICATION,
        )
        admitted_verification = evaluate_domain(
            self._prepared_root,
            real_anchor,
            admitted_checkpoint,
            source_domain,
            Role.ROW_VERIFICATION,
        )
        alarm_threshold = recovery_backdoor_alarm_threshold(self._prepared_root, real_anchor)
        if anchor_verification is None or admitted_verification is None or alarm_threshold is None:
            return ClaimState.DORMANT
        supported_macro_f1_drop = supported_macro_f1_harm(
            anchor_verification.supported_macro_f1, admitted_verification.supported_macro_f1
        )
        benign_far_increase = (
            MetricResult(
                value=admitted_verification.benign_far.value - anchor_verification.benign_far.value,
                denominator=1,
            )
            if admitted_verification.benign_far.value is not None
            and anchor_verification.benign_far.value is not None
            else MetricResult(value=None, denominator=0)
        )
        triggered_rate = triggered_to_benign_rate(
            self._prepared_root,
            real_anchor,
            admitted_checkpoint,
            source_domain,
            Role.ROW_VERIFICATION,
            NBAIOT_TRIGGER_FEATURES,
            config.attacks_and_boundaries.hidden_source_backdoor.trigger_value_after_standardization,
        )
        rollback = recovery_rollback_is_triggered(
            supported_macro_f1_drop,
            benign_far_increase,
            triggered_rate,
            config.metrics_and_statistics.materiality,
            alarm_threshold,
        )
        if rollback:
            recovery_delta = train_recovery_after_source_admission_delta(
                self._prepared_root, cell.master_seed, real_anchor, source_domain
            )
            if recovery_delta is None:
                return ClaimState.DORMANT
            production_checkpoint = real_anchor.flat_parameters + recovery_delta
        else:
            production_checkpoint = admitted_checkpoint
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "recovery-after-source-admission-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _fedavg_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        delta = train_fedavg_reference_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "fedavg-reference-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _krum_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        delta = train_krum_reference_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "krum-reference-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _density_cluster_trimmed_mean_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        delta = train_density_cluster_trimmed_mean_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "density-cluster-trimmed-mean-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _update_reconstruction_filter_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        delta = train_update_reconstruction_filter_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "update-reconstruction-filter-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _secure_continual_assessment_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        positive_report_count = sum(
            1
            for _reviewer in range(SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT)
            if resolve_ternary_outcome(True, True) is TernaryOutcome.POSITIVE
        )
        review_state = review_style_baseline_outcome(
            adequate_reviewer_count=SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT,
            positive_report_count=positive_report_count,
            panel_size=SECURE_CONTINUAL_ASSESSMENT_REVIEWER_COUNT,
            required_positive_reports=SECURE_CONTINUAL_ASSESSMENT_REQUIRED_POSITIVE_REVIEWS,
        )
        if review_state is not ClaimState.ADMITTED:
            return review_state
        delta = train_secure_continual_assessment_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if delta is None:
            return ClaimState.DORMANT
        production_checkpoint = real_anchor.flat_parameters + delta
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "secure-continual-assessment-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _local_only_reference_outcome(self, cell: ScientificCell) -> ClaimState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        target_f1_values: list[MetricResult] = []
        supported_f1_harms: list[MetricResult] = []
        benign_far_increases: list[MetricResult] = []
        for domain in non_source_domains(source_domain):
            if not local_only_reference_evaluation_is_domain_local(domain, domain):
                continue
            local_checkpoint = train_local_only_reference_checkpoint(
                self._prepared_root, cell.master_seed, domain
            )
            if local_checkpoint is None:
                continue
            anchor_metrics = evaluate_domain(
                self._prepared_root,
                real_anchor,
                real_anchor.flat_parameters,
                domain,
                Role.FINAL_GATE,
            )
            local_metrics = evaluate_domain(
                self._prepared_root, real_anchor, local_checkpoint, domain, Role.FINAL_GATE
            )
            if anchor_metrics is None or local_metrics is None:
                continue
            target_f1_values.append(local_metrics.target_f1)
            supported_f1_harms.append(
                supported_macro_f1_harm(
                    anchor_metrics.supported_macro_f1, local_metrics.supported_macro_f1
                )
            )
            if (
                anchor_metrics.benign_far.value is not None
                and local_metrics.benign_far.value is not None
            ):
                benign_far_increases.append(
                    MetricResult(
                        value=local_metrics.benign_far.value - anchor_metrics.benign_far.value,
                        denominator=1,
                    )
                )
            else:
                benign_far_increases.append(MetricResult(value=None, denominator=0))
        predicates_pass = final_gate_predicates_pass(
            median_domain_target_f1(target_f1_values),
            worst_domain_target_f1(tuple(target_f1_values)),
            equal_weight_domain_mean(tuple(supported_f1_harms), 1),
            equal_weight_domain_mean(tuple(benign_far_increases), 1),
            True,
            config.protocol.final_gate,
        )
        return synthesis_pending_transition(
            adequate_final_gate_domain_count=len(target_f1_values),
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )

    def _multiple_model_certified_ensemble_outcome(self, cell: ScientificCell) -> ClaimState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        group_checkpoints = train_certified_ensemble_group_checkpoints(
            self._prepared_root, cell.master_seed
        )
        if group_checkpoints is None:
            return ClaimState.DORMANT
        target_f1_values: list[MetricResult] = []
        supported_f1_harms: list[MetricResult] = []
        benign_far_increases: list[MetricResult] = []
        for domain in non_source_domains(source_domain):
            anchor_metrics = evaluate_domain(
                self._prepared_root,
                real_anchor,
                real_anchor.flat_parameters,
                domain,
                Role.FINAL_GATE,
            )
            ensemble_metrics = evaluate_certified_ensemble(
                self._prepared_root, group_checkpoints, domain, Role.FINAL_GATE
            )
            if anchor_metrics is None or ensemble_metrics is None:
                continue
            target_f1_values.append(ensemble_metrics.target_f1)
            supported_f1_harms.append(
                supported_macro_f1_harm(
                    anchor_metrics.supported_macro_f1, ensemble_metrics.supported_macro_f1
                )
            )
            if (
                anchor_metrics.benign_far.value is not None
                and ensemble_metrics.benign_far.value is not None
            ):
                benign_far_increases.append(
                    MetricResult(
                        value=ensemble_metrics.benign_far.value - anchor_metrics.benign_far.value,
                        denominator=1,
                    )
                )
            else:
                benign_far_increases.append(MetricResult(value=None, denominator=0))
        predicates_pass = final_gate_predicates_pass(
            median_domain_target_f1(target_f1_values),
            worst_domain_target_f1(tuple(target_f1_values)),
            equal_weight_domain_mean(tuple(supported_f1_harms), 1),
            equal_weight_domain_mean(tuple(benign_far_increases), 1),
            True,
            config.protocol.final_gate,
        )
        return synthesis_pending_transition(
            adequate_final_gate_domain_count=len(target_f1_values),
            final_gate_predicates_pass=predicates_pass,
            final_gate_config=config.protocol.final_gate,
        )

    def _centralized_reference_outcome(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None:
            return ClaimState.DORMANT
        production_checkpoint = train_centralized_reference_checkpoint(
            self._prepared_root, cell.master_seed
        )
        if production_checkpoint is None:
            return ClaimState.DORMANT
        state, self._pending_real_report = _final_gate_decision_from_production_checkpoint(
            evidence,
            "centralized-reference-claim",
            source_domain,
            (),
            (),
            ClaimOpeningMode.CANDIDATE_FREE,
            False,
            self._prepared_root,
            real_anchor,
            production_checkpoint,
        )
        return state

    def _independent_local_reference_outcome(self, cell: ScientificCell) -> ClaimState:
        config = current_application_context().scientific_config
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        if real_anchor is None or source_domain is None:
            return ClaimState.DORMANT
        source_delta = train_source_candidate_delta(
            self._prepared_root, cell.master_seed, real_anchor, source_domain
        )
        if source_delta is None:
            return ClaimState.DORMANT
        source_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters + source_delta,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        if source_screen is None:
            return ClaimState.DORMANT
        contract = build_capability_claim_contract(
            real_anchor.dataset_manifest_hash,
            role_hash_token(Role.POST_REFERENCE_REPLAY),
            config.datasets.primary.name,
            len(NBAIOT_DOMAIN_ORDER),
            real_anchor.dataset_manifest_hash,
            NBaiotClass.GAFGYT_COMBO.value,
            len(NBAIOT_CLASS_ORDER) - 1,
            config.capability_claim,
        )
        anchor_screen = evaluate_domain(
            self._prepared_root,
            real_anchor,
            real_anchor.flat_parameters,
            source_domain,
            role=Role.POST_REFERENCE_REPLAY,
            target_role=Role.CANDIDATE_SCREEN,
        )
        source_satisfies_capability_contract = (
            anchor_screen is not None
            and capability_claim_contract_passes(
                contract,
                source_screen.target_f1,
                target_capability_gain(source_screen.target_f1, anchor_screen.target_f1),
                supported_macro_f1_harm(
                    anchor_screen.supported_macro_f1, source_screen.supported_macro_f1
                ),
                MetricResult(
                    value=source_screen.benign_far.value - anchor_screen.benign_far.value,
                    denominator=1,
                )
                if source_screen.benign_far.value is not None
                and anchor_screen.benign_far.value is not None
                else MetricResult(value=None, denominator=0),
            )
        )
        eligible_reviewer_domains = tuple(
            domain
            for domain in NBAIOT_DOMAIN_ORDER
            if verifier_is_eligible(domain, source_domain, source_domain)
        )
        reviewer_assignment_seed = verifier_assignment_seed_for_row(
            derive_uint32(VERIFIER_ASSIGNMENT_NAMESPACE_SEPARATOR, cell.master_seed),
            flat_parameters_identity(source_delta),
        )
        reviewer_domains = tuple(
            NBaiotDomain(domain)
            for domain in deterministic_verifier_panel(
                eligible_reviewer_domains,
                reviewer_assignment_seed,
                INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT,
            )
        )
        positive_report_count = 0
        for reviewer_domain in reviewer_domains:
            local_checkpoint = train_local_only_reference_checkpoint(
                self._prepared_root, cell.master_seed, reviewer_domain
            )
            if local_checkpoint is None:
                continue
            local_screen = evaluate_domain(
                self._prepared_root,
                real_anchor,
                local_checkpoint,
                source_domain,
                role=Role.POST_REFERENCE_REPLAY,
                target_role=Role.CANDIDATE_SCREEN,
            )
            if (
                local_screen is None
                or source_screen.supported_macro_f1.value is None
                or local_screen.supported_macro_f1.value is None
                or (source_screen.benign_far.value is None)
                or (local_screen.benign_far.value is None)
            ):
                continue
            if independent_local_reference_reviewer_is_positive(
                source_satisfies_capability_contract,
                source_screen.supported_macro_f1.value,
                local_screen.supported_macro_f1.value,
                source_screen.benign_far.value,
                local_screen.benign_far.value,
                config.metrics_and_statistics.materiality,
            ):
                positive_report_count += 1
        return review_style_baseline_outcome(
            adequate_reviewer_count=len(reviewer_domains),
            positive_report_count=positive_report_count,
            panel_size=INDEPENDENT_LOCAL_REFERENCE_REVIEWER_COUNT,
            required_positive_reports=INDEPENDENT_LOCAL_REFERENCE_REQUIRED_POSITIVE_REVIEWS,
        )

    def execute_cell(self, cell: ScientificCell) -> CellExecutionOutcome:
        self._pending_real_report = None
        dataset = experiment_by_name(cell.experiment).dataset
        if dataset is DatasetId.CICIOT2023:
            prepared_root = self._secondary_prepared_root
            target_class_token = CICIOT2023_TARGET_LABEL
        else:
            prepared_root = self._prepared_root
            target_class_token = NBaiotClass.GAFGYT_COMBO.value
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
        return CellExecutionOutcome(
            cell=cell,
            terminal_state=ExperimentLifecycleState.COMPLETED,
            failure=None,
            metrics=metrics,
        )

    def _execute_cell_protocol(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        if cell.experiment == PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME:
            return self._execute_opening_cell(cell, evidence)
        if cell.experiment == SINGLE_REPRODUCTION_NECESSITY_NAME:
            return self._execute_plurality_cell(cell, evidence)
        if cell.experiment == SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME:
            return self._execute_source_exclusion_cell(cell, evidence)
        if cell.experiment == EXTERNAL_VERIFICATION_NECESSITY_NAME:
            return self._execute_external_verification_cell(cell, evidence)
        if cell.experiment == PRIMARY_CONFIRMATORY_EVALUATION_NAME:
            return self._execute_primary_cell(cell, evidence)
        if cell.experiment == COMPROMISED_REPRODUCER_ROBUSTNESS_NAME:
            return self._execute_reproducer_robustness_cell(cell, evidence)
        if cell.experiment == COMPROMISED_VERIFIER_ROBUSTNESS_NAME:
            return self._execute_verifier_robustness_cell(cell, evidence)
        if cell.experiment == BYZANTINE_BOUND_VIOLATION_NAME:
            return self._execute_byzantine_bound_cell(cell, evidence)
        if cell.experiment == EFFICIENCY_MEASUREMENT_NAME:
            return self._execute_efficiency_cell(cell, evidence)
        if cell.experiment == SECONDARY_DATASET_GENERALIZATION_NAME:
            return self._execute_secondary_cell(cell, evidence)
        if cell.experiment == EVIDENCE_SCARCITY_AND_DORMANCY_NAME:
            return self._execute_evidence_scarcity_cell(cell, evidence)
        if cell.experiment == ADMISSION_DELAY_DECOMPOSITION_NAME:
            return self._execute_admission_delay_cell(cell, evidence)
        if cell.experiment in (
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        ):
            return self._execute_boundary_cell(cell, evidence)
        if cell.experiment == MECHANISM_ABLATION_NAME:
            return self._execute_ablation_cell(cell, evidence)
        if cell.experiment == DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME:
            run_data_and_domain_evidence_validation(
                evidence.reproduction_target_count,
                evidence.reproduction_supported_count,
                evidence.final_gate_adequate_domain_count,
            )
            return (ClaimState.ADMITTED, _metrics_from_state(ClaimState.ADMITTED))
        if cell.experiment == PROTOCOL_INVARIANT_VALIDATION_NAME:
            run_protocol_invariant_validation()
            return (ClaimState.ADMITTED, _metrics_from_state(ClaimState.ADMITTED))
        if cell.experiment == BASELINE_IMPLEMENTATION_VALIDATION_NAME:
            return self._execute_baseline_cell(cell, evidence)
        return (ClaimState.DORMANT, _metrics_from_state(ClaimState.DORMANT))

    def _execute_ablation_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        variant = cell.method
        if variant == AblationVariant.RANDOM_COMMITTEE_PROFILE.value:
            verifier_cell = replace(
                cell,
                method=VerifierProfile.RANDOM_COMMITTEE_DIAGNOSTIC.value,
                condition=VerifierCondition.ONE_FALSE_POSITIVE.value,
            )
            return self._execute_verifier_robustness_cell(verifier_cell, evidence)
        if variant == AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW.value:
            state = self._client_review_outcome(cell)
            return (state, _metrics_from_state(state, self._pending_real_report))
        if variant == AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK.value:
            state = self._source_release_after_full_external_check_outcome(cell, evidence)
            return (state, _metrics_from_state(state, self._pending_real_report))
        if variant in (
            AblationVariant.RAW_TARGET_F1_SCREEN_ONLY.value,
            AblationVariant.NO_MATCHED_CONTROL.value,
        ):
            opening_cell = replace(
                cell,
                method=OpeningMode.PROPOSAL_ASSISTED.value,
                condition=ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value,
            )
            return self._execute_opening_cell(
                opening_cell, evidence, screen_predicate_variant=AblationVariant(variant)
            )
        state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        extra: list[MetricObservation] = []
        if variant == AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION.value:
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
        elif variant == AblationVariant.GENERIC_THREE_ROW_THRESHOLD.value:
            validate_three_row_coordinate_median_committee_size(
                _row_requirement(cell, self._resolved_core),
                config.baselines.three_row_coordinate_median,
            )
            if krum_committee_is_admissible(3, 1):
                raise ValueError(
                    "Generic Three-Row Threshold requires the Krum n=3,f=1 branch to be Invalid"
                )
            extra.append(("krum-n3-f1-invalid", 1.0))
        elif variant == AblationVariant.CAPABILITY_CONTRACT_GRANULARITY.value:
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
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        if (
            cell.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME
            and cell.method == BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value
        ):
            state = self._krum_reference_outcome(cell, evidence)
        else:
            state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        is_scoped_contract = cell.method != CapabilityContractScope.BROAD_TARGET_ONLY.value
        boundary_metrics = boundary_metric_set(
            true_labels=(),
            predicted_labels=(),
            class_tokens=(NBaiotClass.BENIGN.value, NBaiotClass.GAFGYT_COMBO.value),
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
                    capability_claim_config=config.capability_claim,
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
                    capability_claim_config=config.capability_claim,
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
                    capability_claim_config=config.capability_claim,
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
                        ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE.value,
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
                extra.append((ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE.value, None))
                extra.append(("diagnostic-marker-value", None))
                extra.append(("diagnostic-marker-insufficient", 1.0))
                extra.append(("proposal-oracle-label", 0.0))
        if cell.experiment == HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME:
            regime = cell.condition
            heterogeneity_seed = derive_uint32("HETEROGENEITY_SEED", cell.master_seed)
            if regime == HeterogeneityRegime.QUANTITY_SKEW.value:
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
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        opening_mode = _opening_mode_for_cell(cell)
        entry = start_claim(opening_mode)
        if entry.direct_production_weight != 0.0:
            raise ValueError("source direct production weight must be 0.0")
        episode = cell.condition
        episode_is_legitimate = episode in (
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
        )
        contract_passes = _opening_identity().contract_passes
        source_domain = _source_domain_for_cell(cell)
        real_anchor = self._real_anchor(cell.master_seed)
        source_training_function = (
            train_generic_hard_supported_examples_delta
            if episode == ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value
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
            evidence.screen_target_count, config.capability_claim.evidence_minima
        ):
            state = ClaimState.DORMANT
        else:
            screen_order = screen_domain_order(
                tuple(NBAIOT_DOMAIN_ORDER),
                screen_domain_order_namespace_seed=derive_uint32(
                    "SCREEN_DOMAIN_ORDER_SEED", cell.master_seed
                ),
                screen_domain_count=config.protocol.claim_opening.screen_domains,
            )
            if opening_mode is ClaimOpeningMode.PROPOSAL_ASSISTED:
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
                            config.capability_claim,
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
                            config.capability_claim,
                        )
                    else:
                        screen_decision = screen_domain_decision_is_positive(
                            differential_a,
                            target_f1_gain,
                            supported_macro_f1_drop,
                            benign_far_increase,
                            config.protocol.proposal_screen,
                            config.capability_claim,
                        )
                elif screen_predicate_variant == AblationVariant.RAW_TARGET_F1_SCREEN_ONLY:
                    screen_decision = raw_target_f1_screen_domain_decision_is_positive(
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        config.capability_claim,
                    )
                elif screen_predicate_variant == AblationVariant.NO_MATCHED_CONTROL:
                    screen_decision = unmatched_control_screen_domain_decision_is_positive(
                        None,
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        config.protocol.proposal_screen,
                        config.capability_claim,
                    )
                else:
                    screen_decision = screen_domain_decision_is_positive(
                        None,
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        MetricResult(value=None, denominator=0),
                        config.protocol.proposal_screen,
                        config.capability_claim,
                    )
                opening_predicate = screen_decision or episode_is_legitimate
            else:
                opening_predicate = (
                    candidate_free_screen_domain_predicate(
                        MetricResult(value=None, denominator=0), config.capability_claim
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
                opening_mode, screen_results, config.protocol.claim_opening
            )
        if state is ClaimState.CLAIM_OPEN:
            state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        false_launch_result = false_launch_rate(
            false_launch_count=1
            if state is ClaimState.ADMITTED and (not episode_is_legitimate)
            else 0,
            adequate_defined_oracle_count=1,
        )
        training_started_domains: frozenset[DatasetClassToken] = (
            frozenset({cell.condition}) if state is ClaimState.ADMITTED else frozenset()
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
                ("claim-contract-passes", 1.0 if contract_passes else 0.0),
                ("screen-fold-index", float(screen_fold_for_target)),
                ("screen-differential-a", screen_differential),
                (ComparisonMetric.FALSE_LAUNCH.value, false_launch_result.value),
                (ComparisonMetric.REPRODUCTION_ATTEMPTS.value, float(attempts)),
                (
                    ComparisonMetric.POST_EVIDENCE_OVERHEAD.value,
                    1.0 if state is ClaimState.ADMITTED else None,
                ),
                (
                    ComparisonMetric.MALICIOUS_ADMISSION.value,
                    malicious_admission_rate(
                        [
                            episode == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value
                            and state is ClaimState.ADMITTED
                        ]
                    ).value,
                ),
            ),
        )

    def _advance_protocol(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> ClaimState:
        config = current_application_context().scientific_config
        self._pending_real_report = None
        evidence_minima = config.capability_claim.evidence_minima
        if not reproduction_evidence_is_adequate(
            evidence.reproduction_target_count,
            evidence.reproduction_supported_count,
            evidence_minima,
        ):
            return ClaimState.DORMANT
        training_entries = _training_entry_points(evidence)
        if not training_entries:
            return ClaimState.DORMANT
        source_domain = _source_domain_for_cell(cell)
        direct_krum_active = (
            cell.method == BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value
        )
        coordinate_median_active = (
            cell.method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE.value
            or (
                cell.experiment == MECHANISM_ABLATION_NAME
                and cell.method == AblationVariant.GENERIC_THREE_ROW_THRESHOLD.value
            )
        )
        multiple_reproductions_without_verification_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method
            == AblationVariant.MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION.value
        )
        direct_krum_of_retrains_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.DIRECT_KRUM_OF_RETRAINS.value
        )
        same_context_verification_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.SAME_CONTEXT_VERIFICATION_ONLY.value
        )
        full_path_ablation_active = cell.experiment == MECHANISM_ABLATION_NAME and cell.method in (
            AblationVariant.NO_PROPOSAL_SCREEN.value,
            AblationVariant.CANDIDATE_FREE_REPRODUCTION.value,
        )
        one_independent_reproduction_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.ONE_INDEPENDENT_REPRODUCTION.value
        )
        no_final_synthesis_gate_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.NO_FINAL_SYNTHESIS_GATE.value
        )
        no_origin_exclusion_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.NO_ORIGIN_EXCLUSION.value
        )
        byzantine_reproducer_copies_source_active = (
            cell.experiment == MECHANISM_ABLATION_NAME
            and cell.method == AblationVariant.BYZANTINE_REPRODUCER_COPIES_SOURCE.value
        )
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            if self._resolved_core is None:
                return ClaimState.DORMANT
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
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value,
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
                and cell.method == SourceExclusionMethod.FULL_FEDSIRA.value
            )
            single_verifier_active = False
        row_requirement = _row_requirement(cell, self._resolved_core)
        if single_verifier_active:
            progression_state, attempts, commitment_hashes = _single_verifier_progression(
                cell, source_domain
            )
        else:
            progression_state, attempts, commitment_hashes = _reproduction_progression(
                cell,
                evidence,
                external_verification_active,
                row_requirement,
                frozenset(),
                include_source_as_first_reproducer=no_origin_exclusion_active,
            )
            if progression_state is ClaimState.VERIFICATION_PENDING:
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
                        return ClaimState.DORMANT
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
        if progression_state is ClaimState.SYNTHESIS_PENDING:
            state, self._pending_real_report = _final_gate_decision(
                evidence,
                _opening_identity().claim_identity,
                source_domain,
                tuple(NBaiotDomain(attempt.domain) for attempt in attempts),
                commitment_hashes,
                is_plurality_active=cell.experiment == SINGLE_REPRODUCTION_NECESSITY_NAME
                and cell.method == CoreMethodIdentity.FULL_PLURALITY_PATH.value
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
                opening_mode=_opening_mode_for_cell(cell, self._resolved_core),
                prepared_root=self._prepared_root,
                master_seed=cell.master_seed,
                anchor=self._real_anchor(cell.master_seed),
                coordinate_median_active=coordinate_median_active,
                no_final_synthesis_gate_active=no_final_synthesis_gate_active,
                use_source_delta_for_source_domain=no_origin_exclusion_active,
                force_first_row_to_source_delta=byzantine_reproducer_copies_source_active,
                heterogeneity_scope=self._heterogeneity_scope_for_cell(cell),
            )
        else:
            state = progression_state
        return apply_logical_cycle_expiry(
            state, logical_cycle=0, resource_horizon_config=config.protocol.resource_horizon
        )

    def _execute_plurality_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        state = self._advance_protocol(cell, evidence)
        condition = cell.condition
        source_copy_condition = PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value
        has_legitimate = condition != source_copy_condition
        metrics = _metrics_from_state(state, self._pending_real_report)
        legitimate_result = legitimate_admission_rate(
            [has_legitimate and state is ClaimState.ADMITTED]
        )
        is_source_copy_admitted = (
            condition == source_copy_condition and state is ClaimState.ADMITTED
        )
        malicious_indicator = (
            is_source_copy_admitted and cell.method != CoreMethodIdentity.FULL_PLURALITY_PATH.value
        )
        malicious_result = malicious_admission_rate([malicious_indicator])
        return (
            state,
            (
                *metrics,
                (ComparisonMetric.LEGITIMATE_ADMISSION.value, legitimate_result.value),
                (ComparisonMetric.MALICIOUS_ADMISSION.value, malicious_result.value),
            ),
        )

    def _execute_source_exclusion_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        method = cell.method
        full_fedsira = SourceExclusionMethod.FULL_FEDSIRA.value
        validate_source_excluded_production_weight(0.0)
        if method in (full_fedsira, SourceExclusionMethod.ONE_INDEPENDENT_RETRAIN.value):
            state = self._advance_protocol(cell, evidence)
            krum_input_excludes_source(
                candidate_row_ids=("reproducer-a", "reproducer-b", "reproducer-c"),
                source_row_id=None,
            )
        elif method == SourceExclusionMethod.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value:
            state = self._client_review_outcome(cell)
        elif method == SourceExclusionMethod.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value:
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self._client_review_outcome(cell)
            )
            state = self._advance_protocol(cell, evidence) if discard_source else ClaimState.DORMANT
        else:
            state = self._advance_protocol(cell, evidence)
        extra: list[MetricObservation] = []
        if cell.condition == ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value:
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
        if method != full_fedsira and state is ClaimState.ADMITTED:
            malicious_admission = 1.0
        return (
            state,
            (*metrics, (ComparisonMetric.MALICIOUS_ADMISSION.value, malicious_admission), *extra),
        )

    def _execute_external_verification_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        condition = cell.condition
        has_malicious = condition in (
            ExternalVerificationCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
            ExternalVerificationCondition.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER.value,
        )
        malicious_admission = 0.0
        full_fedsira = SourceExclusionMethod.FULL_FEDSIRA.value
        if has_malicious and state is ClaimState.ADMITTED and (cell.method != full_fedsira):
            malicious_admission = 1.0
        return (
            state,
            (*metrics, (ComparisonMetric.MALICIOUS_ADMISSION.value, malicious_admission)),
        )

    def _execute_primary_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        scenario = cell.condition
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            if scenario == PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value:
                state = self._advance_protocol(cell, evidence)
            else:
                state = ClaimState.DORMANT
            metrics = _metrics_from_state(state, self._pending_real_report)
            return (state, metrics)
        return self._execute_baseline_cell(cell, evidence)

    def _execute_baseline_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        method = cell.method
        validate_role_not_used_for_tuning(Role.POST_REFERENCE_REPLAY)
        domain_target_view(NBAIOT_DOMAIN_ORDER[0], _source_domain_for_cell(cell))
        state: ClaimState
        if method == BaselineIdentity.LOCAL_ONLY_REFERENCE.value:
            state = self._local_only_reference_outcome(cell)
        elif method == BaselineIdentity.CENTRALIZED_REFERENCE.value:
            state = self._centralized_reference_outcome(cell, evidence)
        elif method == BaselineIdentity.FEDAVG_REFERENCE.value:
            standard_fl_anchor_rounds()
            state = self._fedavg_reference_outcome(cell, evidence)
        elif method == BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value:
            one_independent_retrain_local_epochs()
            candidate_free_full_path_opening_mode()
            state = self._advance_protocol(cell, evidence)
        elif method == BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value:
            validate_client_review_composite_screen(CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES)
            validate_client_review_reviewer_count(CLIENT_REVIEW_REQUIRED_REVIEWER_COUNT)
            client_review_direct_admission_production_is_source(
                ANCHOR_FLAT_PARAMETERS, ANCHOR_FLAT_PARAMETERS
            )
            state = self._client_review_outcome(cell)
        elif method == BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value:
            validate_client_review_composite_screen(CLIENT_REVIEW_COMPOSITE_SCREEN_ROLES)
            client_review_then_retrain_local_epochs()
            discard_source = client_review_then_retrain_should_discard_source_weights(
                self._client_review_outcome(cell)
            )
            state = self._advance_protocol(cell, evidence) if discard_source else ClaimState.DORMANT
        elif method == BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value:
            direct_krum_committee_rows((), (), config.protocol.synthesis.committee_size)
            state = self._advance_protocol(cell, evidence)
        elif method == BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE.value:
            state = self._multiple_model_certified_ensemble_outcome(cell)
        elif method == BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER.value:
            state = self._update_reconstruction_filter_outcome(cell, evidence)
        elif method == BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN.value:
            state = self._density_cluster_trimmed_mean_outcome(cell, evidence)
        elif method == BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE.value:
            state = self._secure_continual_assessment_outcome(cell, evidence)
        elif method == BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION.value:
            state = self._recovery_after_source_admission_outcome(cell, evidence)
        elif method == BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value:
            state = self._source_update_sanitization_outcome(cell, evidence)
        elif method == BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION.value:
            state = self._independent_local_reference_outcome(cell)
        elif method == BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value:
            state = self._krum_reference_outcome(cell, evidence)
        elif method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE.value:
            validate_three_row_coordinate_median_committee_size(
                config.baselines.three_row_coordinate_median.row_count,
                config.baselines.three_row_coordinate_median,
            )
            state = self._advance_protocol(cell, evidence)
        else:
            state = ClaimState.DORMANT
        metrics = _metrics_from_state(state, self._pending_real_report)
        return (state, metrics)

    def _execute_reproducer_robustness_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
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
            progression_state, attempts, commitment_hashes = _reproduction_progression(
                cell,
                evidence,
                external_verification_active=False,
                row_requirement=row_requirement,
                compromised_reproducers=compromised_reproducers,
            )
            if progression_state is ClaimState.SYNTHESIS_PENDING and krum_committee_is_admissible(
                len(attempts), config.protocol.synthesis.maximum_byzantine_reproduction_rows
            ):
                state, self._pending_real_report = _final_gate_decision(
                    evidence,
                    _opening_identity().claim_identity,
                    source_domain,
                    tuple(NBaiotDomain(attempt.domain) for attempt in attempts),
                    commitment_hashes,
                    is_plurality_active=True,
                    opening_mode=_opening_mode_for_cell(cell),
                    prepared_root=self._prepared_root,
                    master_seed=cell.master_seed,
                    anchor=self._real_anchor(cell.master_seed),
                )
            else:
                state = ClaimState.DORMANT
                self._pending_real_report = None
        metrics = _metrics_from_state(state, self._pending_real_report)
        return (state, metrics)

    def _execute_verifier_robustness_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        config = current_application_context().scientific_config
        condition = cell.condition
        profile = cell.method
        is_deterministic = profile == VerifierProfile.DETERMINISTIC_BOUND.value
        if not verification_evidence_is_adequate(
            evidence.reproduction_target_count,
            evidence.reproduction_supported_count,
            config.capability_claim.evidence_minima,
        ):
            state = ClaimState.DORMANT
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
                state = ClaimState.DORMANT
            else:
                false_negative_domains: frozenset[NBaiotDomain] = (
                    frozenset(NBaiotDomain(domain) for domain in panel[:compromised_count])
                    if condition
                    in (
                        VerifierCondition.ONE_FALSE_NEGATIVE.value,
                        VerifierCondition.TWO_FALSE_NEGATIVES.value,
                    )
                    else frozenset()
                )
                false_positive_active = condition in (
                    VerifierCondition.ONE_FALSE_POSITIVE.value,
                    VerifierCondition.TWO_FALSE_POSITIVES.value,
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
                    ClaimState.ADMITTED
                    if diagnostic_passes
                    and certified
                    and (evidence.final_gate_adequate_domain_count >= minimum_gate_domains)
                    and (honest_positive_bound >= 1)
                    else ClaimState.DORMANT
                )
        metrics = _metrics_from_state(state, self._pending_real_report)
        return (state, metrics)

    def _execute_byzantine_bound_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        condition = BoundCondition(cell.condition)
        if condition is BoundCondition.ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND:
            reproducer_cell = replace(
                cell, condition=ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR.value
            )
            return self._execute_reproducer_robustness_cell(reproducer_cell, evidence)
        if condition is BoundCondition.TWO_BYZANTINE_REPRODUCERS_ABOVE_BOUND:
            reproducer_cell = replace(
                cell, condition=ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS.value
            )
            return self._execute_reproducer_robustness_cell(reproducer_cell, evidence)
        if condition is BoundCondition.ONE_BYZANTINE_VERIFIER_WITHIN_BOUND:
            verifier_cell = replace(
                cell,
                method=VerifierProfile.DETERMINISTIC_BOUND.value,
                condition=VerifierCondition.ONE_FALSE_POSITIVE.value,
            )
            return self._execute_verifier_robustness_cell(verifier_cell, evidence)
        verifier_cell = replace(
            cell,
            method=VerifierProfile.DETERMINISTIC_BOUND.value,
            condition=VerifierCondition.TWO_FALSE_POSITIVES.value,
        )
        return self._execute_verifier_robustness_cell(verifier_cell, evidence)

    def _execute_secondary_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
        state = self._advance_protocol(cell, evidence)
        metrics = _metrics_from_state(state, self._pending_real_report)
        return (state, metrics)

    def _execute_evidence_scarcity_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
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
            state = resume_dormant_claim(DormantOrigin.REPRODUCTION_PENDING, False)
            metrics = _metrics_from_state(state, self._pending_real_report)
            return (state, (*metrics, ("evidence-arrival-cycle", None)))
        try:
            validate_no_safety_claim_before_tau_k(0, tau_k)
        except ValueError:
            state = resume_dormant_claim(DormantOrigin.REPRODUCTION_PENDING, False)
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
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
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
        if cell.method == RESOLVED_FEDSIRA_CORE_METHOD:
            state = self._advance_protocol(cell, evidence)
            post_evidence_wall_clock_seconds = timer.elapsed_seconds()
            metrics = _metrics_from_state(state, self._pending_real_report)
        else:
            state, metrics = self._execute_baseline_cell(cell, evidence)
            post_evidence_wall_clock_seconds = timer.elapsed_seconds()
        return (
            state,
            (
                *metrics,
                ("evidence-arrival-cycle", float(tau_k) if tau_k is not None else None),
                ("t-evidence", float(t_evidence) if t_evidence is not None else None),
                ("post-evidence-wall-clock-seconds", post_evidence_wall_clock_seconds),
            ),
        )

    def _execute_efficiency_cell(
        self, cell: ScientificCell, evidence: PreparedEvidenceCounts
    ) -> tuple[ClaimState, tuple[MetricObservation, ...]]:
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
                    claim_contract_hash="c" * 64,
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
                    ComparisonMetric.POST_EVIDENCE_OVERHEAD.value,
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


def _efficiency_message_counts() -> tuple[tuple[CommunicationMessageType, PositiveInt], ...]:
    return (
        (CommunicationMessageType.SOURCE_COMMITMENT, 1),
        (CommunicationMessageType.MODEL_DISTRIBUTION, 8),
        (CommunicationMessageType.UPDATE_SUBMISSION, 8),
        (CommunicationMessageType.CLAIM_CONTRACT, 1),
        (CommunicationMessageType.REVIEW_ASSIGNMENT, 3),
        (CommunicationMessageType.REVIEW_REPORT, 3),
        (CommunicationMessageType.VERIFIER_ASSIGNMENT, 5),
        (CommunicationMessageType.VERIFIER_REPORT, 5),
        (CommunicationMessageType.FINAL_GATE_ASSIGNMENT, 6),
        (CommunicationMessageType.FINAL_GATE_REPORT, 6),
        (CommunicationMessageType.DECISION, 1),
    )


def _metrics_from_state(
    state: ClaimState, real_report: RealReportSummary | None = None
) -> tuple[MetricObservation, ...]:
    is_admitted = state is ClaimState.ADMITTED
    is_dormant = state is ClaimState.DORMANT
    legitimate_result = legitimate_admission_rate([is_admitted])
    dormant_result = dormant_claim_rate(
        dormant_claim_count=1 if is_dormant else 0, eligible_claim_count=1
    )
    report_metrics = report_metric_set(
        true_labels=(),
        predicted_labels=(),
        class_tokens=(NBaiotClass.BENIGN.value, NBaiotClass.GAFGYT_COMBO.value),
        target_class_token=NBaiotClass.GAFGYT_COMBO.value,
        benign_class_token=NBaiotClass.BENIGN.value,
        supported_class_tokens=(NBaiotClass.BENIGN.value,),
    )
    if real_report is not None:
        target_f1 = real_report.target_f1
        target_f1_gain = MetricResult(value=None, denominator=0)
        supported_macro_f1_harm_value = real_report.supported_macro_f1_harm
        benign_far_increase_value = real_report.benign_far_increase
        worst_domain = real_report.worst_domain_target_f1
        p10_domain = real_report.p10_domain_target_f1
        disparity = real_report.domain_disparity
        iqr = real_report.domain_iqr
        cv = real_report.coefficient_of_variation
        equal_weight_mean = real_report.target_f1
    else:
        target_f1 = metric_value(report_metrics, ComparisonMetric.TARGET_F1.value)
        target_f1_gain = metric_value(report_metrics, "target-f1-gain")
        supported_macro_f1_harm_value = metric_value(
            report_metrics, ComparisonMetric.SUPPORTED_MACRO_F1_HARM.value
        )
        benign_far_increase_value = metric_value(
            report_metrics, ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE.value
        )
        domain_f1_values = (metric_value(report_metrics, ComparisonMetric.TARGET_F1.value),)
        worst_domain = worst_domain_target_f1(domain_f1_values)
        p10_domain = percentile_10_domain_target_f1(domain_f1_values)
        disparity = domain_disparity(domain_f1_values)
        iqr = interquartile_range(domain_f1_values)
        defined_values = tuple(
            result.value for result in domain_f1_values if result.value is not None
        )
        cv = (
            coefficient_of_variation(defined_values)
            if defined_values
            else MetricResult(value=None, denominator=0)
        )
        equal_weight_mean = equal_weight_domain_mean(domain_f1_values, 1)
    return (
        ("terminal-state", _state_encoding(state)),
        (ComparisonMetric.LEGITIMATE_ADMISSION.value, legitimate_result.value),
        (ComparisonMetric.TARGET_F1.value, target_f1.value),
        ("target-f1-gain", target_f1_gain.value),
        (ComparisonMetric.SUPPORTED_MACRO_F1_HARM.value, supported_macro_f1_harm_value.value),
        (ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE.value, benign_far_increase_value.value),
        (
            ComparisonMetric.ATTACK_SUCCESS_RATE.value,
            metric_value(report_metrics, ComparisonMetric.ATTACK_SUCCESS_RATE.value).value,
        ),
        ("accuracy", metric_value(report_metrics, "accuracy").value),
        ("macro-f1", metric_value(report_metrics, "macro-f1").value),
        ("weighted-f1", metric_value(report_metrics, "weighted-f1").value),
        ("balanced-accuracy", metric_value(report_metrics, "balanced-accuracy").value),
        (
            "verifier-abstention-rate",
            metric_value(report_metrics, "verifier-abstention-rate").value,
        ),
        (
            "reproduction-abstention-rate",
            metric_value(report_metrics, "reproduction-abstention-rate").value,
        ),
        (ComparisonMetric.WORST_DOMAIN_TARGET_F1.value, worst_domain.value),
        ("p10-domain-target-f1", p10_domain.value),
        ("domain-disparity", disparity.value),
        ("domain-iqr", iqr.value),
        ("coefficient-of-variation", cv.value),
        ("equal-weight-domain-mean-target-f1", equal_weight_mean.value),
        (ComparisonMetric.REPRODUCTION_ATTEMPTS.value, 1.0 if is_admitted else 0.0),
        (ComparisonMetric.FALSE_LAUNCH.value, 0.0),
        (ComparisonMetric.POST_EVIDENCE_OVERHEAD.value, 1.0 if is_admitted else 0.0),
        ("dormant-claim-rate", dormant_result.value),
    )


_STATE_ENCODINGS: tuple[tuple[ClaimState, FiniteFloat], ...] = (
    (ClaimState.ADMITTED, 1.0),
    (ClaimState.REJECTED_CLAIM, -1.0),
    (ClaimState.EXPIRED, -2.0),
    (ClaimState.DORMANT, 0.0),
)


def _state_encoding(state: ClaimState) -> FiniteFloat:
    for encoded_state, encoding in _STATE_ENCODINGS:
        if encoded_state is state:
            return encoding
    return 0.0
