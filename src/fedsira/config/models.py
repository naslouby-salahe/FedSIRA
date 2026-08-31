from __future__ import annotations

from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from fedsira.domain.enums import (
    ByteUnit,
    ByzantineVerifierBehavior,
    CapabilityContractScope,
    DatasetId,
    Role,
    RootCauseMixture,
)
from fedsira.domain.types import (
    AdmissionCount,
    AdmissionRateChange,
    AttackStrength,
    BatchSize,
    BenignFalseAlarmRateIncrease,
    BootstrapResampleCount,
    CadenceRounds,
    CapabilityCertificationRate,
    ClientDropout,
    ClusterSize,
    CommitteeSize,
    ConfidenceLevel,
    ConfigFormatVersion,
    ConfusionCount,
    ContaminationRisk,
    CosineSimilarity,
    DatasetClassToken,
    DbscanEpsilon,
    DecimalPlaces,
    DefinedDomainFraction,
    DeltaScale,
    DifferentialNatsPerExample,
    Doi,
    DomainCount,
    DurationToleranceSeconds,
    EnvironmentText,
    EvidenceCycleIndex,
    ExampleCount,
    FamilyWiseAlpha,
    FeatureCount,
    FeatureShiftMagnitude,
    FederatedRoundCount,
    FixtureCaseName,
    FoldCount,
    GigabyteCount,
    GpuCount,
    GradientL2Clip,
    GroupCount,
    HashModulus,
    HeterogeneityMultiplier,
    LearningRate,
    LocalEpochCount,
    LogicalEvidenceCycleCount,
    LossWeight,
    MasterSeed,
    MatchedControlCount,
    MetricTolerance,
    MetricValue,
    MinimumCompletePairCount,
    MinimumExampleCount,
    ModelInputWidth,
    ModelOutputWidth,
    NumericalEpsilon,
    OptimizerBeta,
    OptimizerEpsilon,
    PartitionSalt,
    Percentile,
    PersistentWorkersEnabled,
    PinMemoryEnabled,
    PoisonFraction,
    ProbabilityTolerance,
    ProductionWeight,
    PValue,
    PValueDisplayFloor,
    QuantileProbability,
    RateMargin,
    RateReduction,
    RateWorsening,
    RegularizationWeight,
    RepositoryPath,
    ReproductionRowCount,
    RetryCount,
    RoleBoundary,
    ScaleFactor,
    ScreenDomainCount,
    SeedCount,
    SignificantDigits,
    StandardizedValue,
    SupportedMacroF1Drop,
    TargetF1,
    TargetF1Change,
    TargetF1Gain,
    Temperature,
    TimeoutSeconds,
    TrimCount,
    UciDatasetId,
    VerifierCount,
    WallClockSeconds,
    WarmupPassCount,
    WeightDecay,
    WorkerCount,
)


class FrozenConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


def _validate_role_interval_bounds(
    value: tuple[RoleBoundary, RoleBoundary],
) -> tuple[RoleBoundary, RoleBoundary]:
    start, end = value
    if end <= start:
        raise ValueError("role interval end must be strictly greater than start")
    return value


RoleInterval = Annotated[
    tuple[RoleBoundary, RoleBoundary], AfterValidator(_validate_role_interval_bounds)
]


class SupportedRoleIntervals(FrozenConfigModel):
    anchor_train: RoleInterval = Field(alias=Role.ANCHOR_TRAIN.value)
    anchor_validation: RoleInterval = Field(alias=Role.ANCHOR_VALIDATION.value)
    post_reference_replay: RoleInterval = Field(alias=Role.POST_REFERENCE_REPLAY.value)
    row_verification: RoleInterval = Field(alias=Role.ROW_VERIFICATION.value)
    final_gate: RoleInterval = Field(alias=Role.FINAL_GATE.value)
    report_test: RoleInterval = Field(alias=Role.REPORT_TEST.value)

    def interval_for(self, role: Role) -> RoleInterval:
        if role is Role.ANCHOR_TRAIN:
            return self.anchor_train
        if role is Role.ANCHOR_VALIDATION:
            return self.anchor_validation
        if role is Role.POST_REFERENCE_REPLAY:
            return self.post_reference_replay
        if role is Role.ROW_VERIFICATION:
            return self.row_verification
        if role is Role.FINAL_GATE:
            return self.final_gate
        if role is Role.REPORT_TEST:
            return self.report_test
        raise ValueError(f"unsupported supported-data role: {role.value}")


class TargetRoleIntervals(FrozenConfigModel):
    source_proposal: RoleInterval = Field(alias=Role.SOURCE_PROPOSAL.value)
    candidate_screen: RoleInterval = Field(alias=Role.CANDIDATE_SCREEN.value)
    reproduction: RoleInterval = Field(alias=Role.REPRODUCTION.value)
    row_verification: RoleInterval = Field(alias=Role.ROW_VERIFICATION.value)
    final_gate: RoleInterval = Field(alias=Role.FINAL_GATE.value)
    report_test: RoleInterval = Field(alias=Role.REPORT_TEST.value)

    def interval_for(self, role: Role) -> RoleInterval:
        if role is Role.SOURCE_PROPOSAL:
            return self.source_proposal
        if role is Role.CANDIDATE_SCREEN:
            return self.candidate_screen
        if role is Role.REPRODUCTION:
            return self.reproduction
        if role is Role.ROW_VERIFICATION:
            return self.row_verification
        if role is Role.FINAL_GATE:
            return self.final_gate
        if role is Role.REPORT_TEST:
            return self.report_test
        raise ValueError(f"unsupported target-data role: {role.value}")


class RoleIntervals(FrozenConfigModel):
    supported: SupportedRoleIntervals
    target: TargetRoleIntervals


class SamplingCapsPerDomain(FrozenConfigModel):
    anchor_train_per_supported_class: MinimumExampleCount
    anchor_validation_per_supported_class: MinimumExampleCount
    source_proposal_target: MinimumExampleCount
    source_proposal_supported_replay_per_supported_class: MinimumExampleCount
    candidate_screen_target: MinimumExampleCount
    reproduction_target: MinimumExampleCount
    reproduction_supported_replay_per_supported_class: MinimumExampleCount
    row_verification_target: MinimumExampleCount
    row_verification_supported_per_supported_class: MinimumExampleCount
    final_gate_target: MinimumExampleCount
    final_gate_supported_per_supported_class: MinimumExampleCount
    report_test_target: MinimumExampleCount
    report_test_benign: MinimumExampleCount
    report_test_other_supported_per_class: MinimumExampleCount


class ScalingConfig(FrozenConfigModel):
    zero_standard_deviation_scale: ScaleFactor
    clip_min: StandardizedValue
    clip_max: StandardizedValue

    @model_validator(mode="after")
    def _clip_bounds_ordered(self) -> Self:
        if self.clip_max <= self.clip_min:
            raise ValueError("clip_max must be strictly greater than clip_min")
        return self


class PrimaryDatasetConfig(FrozenConfigModel):
    name: DatasetId
    uci_dataset_id: UciDatasetId
    doi: Doi
    target_class: DatasetClassToken
    minimum_target_holding_domains: DomainCount
    supported_metric_minimum_report_examples_per_class: MinimumExampleCount
    role_intervals: RoleIntervals
    sampling_caps_per_domain: SamplingCapsPerDomain
    scaling: ScalingConfig


class SecondaryDatasetConfig(FrozenConfigModel):
    name: DatasetId
    target_class: DatasetClassToken
    pseudo_domain_partition_salt: PartitionSalt


class DatasetsConfig(FrozenConfigModel):
    primary: PrimaryDatasetConfig
    secondary: SecondaryDatasetConfig

    @model_validator(mode="after")
    def _datasets_are_distinct(self) -> Self:
        if self.primary.name is self.secondary.name:
            raise ValueError("primary and secondary datasets must be distinct")
        return self


class EvidenceMinimaConfig(FrozenConfigModel):
    reproduction_target_examples: MinimumExampleCount
    reproduction_supported_control_examples: MinimumExampleCount
    verification_target_examples: MinimumExampleCount
    verification_supported_control_examples: MinimumExampleCount
    proposal_screen_target_examples: MinimumExampleCount


class CapabilityClaimConfig(FrozenConfigModel):
    target_f1_minimum: TargetF1
    target_f1_gain_over_anchor_minimum: TargetF1Gain
    supported_macro_f1_drop_maximum: SupportedMacroF1Drop
    benign_false_alarm_rate_increase_maximum: BenignFalseAlarmRateIncrease
    candidate_free_anchor_target_f1_maximum: TargetF1
    evidence_minima: EvidenceMinimaConfig


class ClaimOpeningConfig(FrozenConfigModel):
    screen_domains: ScreenDomainCount
    required_positive_screen_domains: ScreenDomainCount
    candidate_free_required_adequate_domains: DomainCount

    @model_validator(mode="after")
    def _required_within_screen_domains(self) -> Self:
        if self.required_positive_screen_domains > self.screen_domains:
            raise ValueError("required_positive_screen_domains cannot exceed screen_domains")
        return self


class ProposalScreenConfig(FrozenConfigModel):
    fold_count: FoldCount
    differential_minimum_nats_per_example: DifferentialNatsPerExample
    matched_controls_per_target: MatchedControlCount


class ResourceHorizonConfig(FrozenConfigModel):
    maximum_logical_evidence_cycles: LogicalEvidenceCycleCount
    measurement_cycle_start: EvidenceCycleIndex
    measurement_cycle_end: EvidenceCycleIndex

    @model_validator(mode="after")
    def _measurement_window_ordered(self) -> Self:
        if self.measurement_cycle_end <= self.measurement_cycle_start:
            raise ValueError(
                "measurement_cycle_end must be strictly greater than measurement_cycle_start"
            )
        if self.measurement_cycle_end > self.maximum_logical_evidence_cycles:
            raise ValueError("measurement_cycle_end cannot exceed maximum_logical_evidence_cycles")
        return self


class VerificationConfig(FrozenConfigModel):
    panel_size: VerifierCount
    maximum_byzantine_verifiers_per_panel: ReproductionRowCount
    required_positive_reports: VerifierCount

    @model_validator(mode="after")
    def _panel_consistency(self) -> Self:
        if self.required_positive_reports > self.panel_size:
            raise ValueError("required_positive_reports cannot exceed panel_size")
        if self.maximum_byzantine_verifiers_per_panel >= self.panel_size:
            raise ValueError(
                "maximum_byzantine_verifiers_per_panel must be smaller than panel_size"
            )
        return self


class SynthesisConfig(FrozenConfigModel):
    committee_size: CommitteeSize
    maximum_byzantine_reproduction_rows: ReproductionRowCount

    @model_validator(mode="after")
    def _committee_consistency(self) -> Self:
        if self.maximum_byzantine_reproduction_rows >= self.committee_size:
            raise ValueError(
                "maximum_byzantine_reproduction_rows must be smaller than committee_size"
            )
        return self


class FinalGateConfig(FrozenConfigModel):
    minimum_adequate_non_source_domains: DomainCount
    median_target_f1_minimum: TargetF1
    minimum_domain_target_f1: TargetF1
    supported_macro_f1_drop_maximum: SupportedMacroF1Drop
    benign_false_alarm_rate_increase_maximum: BenignFalseAlarmRateIncrease

    @model_validator(mode="after")
    def _target_f1_floor_is_consistent(self) -> Self:
        if self.minimum_domain_target_f1 > self.median_target_f1_minimum:
            raise ValueError("minimum_domain_target_f1 cannot exceed median_target_f1_minimum")
        return self


class DiagnosticRandomVerifierProfileConfig(FrozenConfigModel):
    byzantine_domain_count: ReproductionRowCount
    panel_size: VerifierCount
    required_positive_reports: VerifierCount
    tolerated_contamination_risk: ContaminationRisk

    @model_validator(mode="after")
    def _required_within_panel(self) -> Self:
        if self.required_positive_reports > self.panel_size:
            raise ValueError("required_positive_reports cannot exceed panel_size")
        if self.byzantine_domain_count < self.panel_size:
            return self
        raise ValueError("byzantine_domain_count must be smaller than panel_size")


class ProtocolConfig(FrozenConfigModel):
    claim_opening: ClaimOpeningConfig
    proposal_screen: ProposalScreenConfig
    resource_horizon: ResourceHorizonConfig
    verification: VerificationConfig
    synthesis: SynthesisConfig
    final_gate: FinalGateConfig
    diagnostic_random_verifier_profile: DiagnosticRandomVerifierProfileConfig


class OptimizerConfig(FrozenConfigModel):
    anchor_and_standard_fl_learning_rate: LearningRate
    post_reference_learning_rate: LearningRate
    betas: tuple[OptimizerBeta, OptimizerBeta]
    epsilon: OptimizerEpsilon
    weight_decay: WeightDecay

    @model_validator(mode="after")
    def _betas_are_valid(self) -> Self:
        beta_one, beta_two = self.betas
        if beta_one >= beta_two:
            raise ValueError("optimizer betas must satisfy beta_one < beta_two")
        return self


class TrainingConfig(FrozenConfigModel):
    batch_size: BatchSize
    gradient_global_l2_clip: GradientL2Clip


class AnchorFedAvgConfig(FrozenConfigModel):
    rounds: FederatedRoundCount
    local_epochs_per_round: LocalEpochCount
    client_dropout: ClientDropout
    checkpoint_cadence_rounds: CadenceRounds
    evaluation_cadence_rounds: CadenceRounds

    @model_validator(mode="after")
    def _cadences_fit_training_horizon(self) -> Self:
        if self.checkpoint_cadence_rounds > self.rounds:
            raise ValueError("checkpoint_cadence_rounds cannot exceed rounds")
        if self.evaluation_cadence_rounds > self.rounds:
            raise ValueError("evaluation_cadence_rounds cannot exceed rounds")
        return self


class PostReferenceConfig(FrozenConfigModel):
    local_epochs: LocalEpochCount
    stability_kl_temperature: Temperature
    stability_weight: LossWeight
    delta_l2_weight: RegularizationWeight


class VerifierAwareBackdoorOverrideConfig(FrozenConfigModel):
    local_epochs: LocalEpochCount
    triggered_backdoor_loss_weight: LossWeight


class ModelConfig(FrozenConfigModel):
    optimizer: OptimizerConfig
    training: TrainingConfig
    anchor_fedavg: AnchorFedAvgConfig
    post_reference: PostReferenceConfig
    verifier_aware_backdoor_override: VerifierAwareBackdoorOverrideConfig


class SeedsAndDeterminismConfig(FrozenConfigModel):
    master_seeds: tuple[MasterSeed, ...]
    analysis_seed: MasterSeed
    smoke_seed: MasterSeed

    @model_validator(mode="after")
    def _master_seeds_are_distinct(self) -> Self:
        if not self.master_seeds:
            raise ValueError("master_seeds must not be empty")
        if len(set(self.master_seeds)) != len(self.master_seeds):
            raise ValueError("master_seeds must not contain duplicates")
        if self.analysis_seed in self.master_seeds:
            raise ValueError("analysis_seed must be distinct from master_seeds")
        if self.smoke_seed in self.master_seeds or self.smoke_seed == self.analysis_seed:
            raise ValueError("smoke_seed must be distinct from confirmatory and analysis seeds")
        return self

    @property
    def confirmatory_seed_count(self) -> SeedCount:
        return len(self.master_seeds)


class ModelReplacementConfig(FrozenConfigModel):
    poison_fraction: PoisonFraction
    delta_scale: DeltaScale


class VerifierAwareConfig(FrozenConfigModel):
    delta_scale: DeltaScale


class HiddenSourceBackdoorConfig(FrozenConfigModel):
    trigger_value_after_standardization: StandardizedValue
    confirmatory_poison_fraction: PoisonFraction
    poison_fraction_sweep: tuple[PoisonFraction, ...]

    @model_validator(mode="after")
    def _confirmatory_fraction_is_in_sweep(self) -> Self:
        if not self.poison_fraction_sweep:
            raise ValueError("poison_fraction_sweep must not be empty")
        if len(set(self.poison_fraction_sweep)) != len(self.poison_fraction_sweep):
            raise ValueError("poison_fraction_sweep must not contain duplicates")
        if self.confirmatory_poison_fraction not in self.poison_fraction_sweep:
            raise ValueError(
                "confirmatory_poison_fraction must be included in poison_fraction_sweep"
            )
        return self


class ByzantineReproductionConfig(FrozenConfigModel):
    compromised_counts: tuple[ReproductionRowCount, ...]
    model_replacement: ModelReplacementConfig
    verifier_aware: VerifierAwareConfig


class ByzantineVerifierConfig(FrozenConfigModel):
    compromise_counts: tuple[ReproductionRowCount, ...]
    behaviors: tuple[ByzantineVerifierBehavior, ...]


class SharedLabelErrorConfig(FrozenConfigModel):
    strengths: tuple[AttackStrength, ...]


class SharedSpuriousFeatureConfig(FrozenConfigModel):
    strengths: tuple[AttackStrength, ...]
    value_after_standardization: StandardizedValue


class AttackerInducedCommonContextConfig(FrozenConfigModel):
    strengths: tuple[AttackStrength, ...]


class CapabilityUnderSpecificationConfig(FrozenConfigModel):
    root_cause_hash_modulus: HashModulus
    shift_value_after_standardization: StandardizedValue
    contracts: tuple[CapabilityContractScope, ...]
    mixtures: tuple[RootCauseMixture, ...]


class HeterogeneityConfig(FrozenConfigModel):
    quantity_skew_multipliers: tuple[HeterogeneityMultiplier, ...]
    feature_shift_selected_feature_count: FeatureCount
    feature_shift_magnitudes: tuple[FeatureShiftMagnitude, ...]


class CleanOracleMaterialityConfig(FrozenConfigModel):
    target_f1_decrease: TargetF1
    supported_macro_f1_drop: SupportedMacroF1Drop
    benign_false_alarm_rate_increase: BenignFalseAlarmRateIncrease


class AttacksAndBoundariesConfig(FrozenConfigModel):
    hidden_source_backdoor: HiddenSourceBackdoorConfig
    byzantine_reproduction: ByzantineReproductionConfig
    byzantine_verifier: ByzantineVerifierConfig
    shared_label_error: SharedLabelErrorConfig
    shared_spurious_feature: SharedSpuriousFeatureConfig
    attacker_induced_common_context: AttackerInducedCommonContextConfig
    capability_under_specification: CapabilityUnderSpecificationConfig
    heterogeneity: HeterogeneityConfig
    clean_oracle_materiality: CleanOracleMaterialityConfig


class ReconstructionFilterConfig(FrozenConfigModel):
    reconstruction_local_epochs: LocalEpochCount
    normalization_epsilon: NumericalEpsilon
    calibration_percentile: Percentile


class DensityClusterTrimmedMeanConfig(FrozenConfigModel):
    dbscan_epsilon: DbscanEpsilon
    dbscan_min_samples: ClusterSize
    trim_each_tail_count: TrimCount
    minimum_cluster_size_for_trimming: ClusterSize

    @model_validator(mode="after")
    def _trim_count_fits_cluster(self) -> Self:
        if 2 * self.trim_each_tail_count >= self.minimum_cluster_size_for_trimming:
            raise ValueError(
                "twice trim_each_tail_count must be smaller than minimum_cluster_size_for_trimming"
            )
        return self


class RecoveryAfterSourceAdmissionConfig(FrozenConfigModel):
    backdoor_alarm_percentile: Percentile
    recovery_rounds: FederatedRoundCount


class SourceUpdateSanitizationConfig(FrozenConfigModel):
    coordinate_bound_percentile: Percentile


class ParameterSimilarityConfig(FrozenConfigModel):
    required_committed_rows: CommitteeSize
    cosine_similarity_minimum: CosineSimilarity


class ThreeRowCoordinateMedianConfig(FrozenConfigModel):
    row_count: CommitteeSize
    assumed_byzantine_rows: ReproductionRowCount

    @model_validator(mode="after")
    def _byzantine_within_rows(self) -> Self:
        if self.assumed_byzantine_rows >= self.row_count:
            raise ValueError("assumed_byzantine_rows must be smaller than row_count")
        return self


class BaselinesConfig(FrozenConfigModel):
    local_only_reference_epochs: LocalEpochCount
    centralized_reference_epochs: LocalEpochCount
    fedavg_post_reference_rounds: FederatedRoundCount
    multiple_model_certified_ensemble_group_count: GroupCount
    multiple_model_certified_ensemble_post_reference_rounds: FederatedRoundCount
    reconstruction_filter: ReconstructionFilterConfig
    density_cluster_trimmed_mean: DensityClusterTrimmedMeanConfig
    secure_continual_assessment_post_reference_rounds: FederatedRoundCount
    recovery_after_source_admission: RecoveryAfterSourceAdmissionConfig
    source_update_sanitization: SourceUpdateSanitizationConfig
    parameter_similarity: ParameterSimilarityConfig
    three_row_coordinate_median: ThreeRowCoordinateMedianConfig
    krum_robust_aggregation_post_reference_rounds: FederatedRoundCount


class MetricAggregationConfig(FrozenConfigModel):
    generic_defined_domain_fraction_minimum: DefinedDomainFraction


class MultiplicityConfig(FrozenConfigModel):
    family_wise_alpha: FamilyWiseAlpha


class BootstrapConfig(FrozenConfigModel):
    confidence_level: ConfidenceLevel
    resamples: BootstrapResampleCount


class MaterialityConfig(FrozenConfigModel):
    target_f1_gain_minimum: TargetF1Gain
    target_f1_noninferiority_margin: TargetF1
    supported_macro_f1_noninferiority_margin: SupportedMacroF1Drop
    benign_false_alarm_rate_noninferiority_margin: BenignFalseAlarmRateIncrease
    source_exclusion_asr_reduction_minimum: RateReduction
    malicious_admission_reduction_minimum: RateReduction
    legitimate_admission_noninferiority_margin: RateMargin
    worst_domain_target_f1_gain_minimum: TargetF1Gain
    false_launch_reduction_minimum: RateReduction
    reproduction_attempt_relative_reduction_minimum: RateReduction
    post_evidence_overhead_relative_reduction_minimum: RateReduction
    proposal_malicious_admission_worsening_maximum: RateWorsening


class TechnicalCompletionConfig(FrozenConfigModel):
    minimum_complete_pairs_for_claim_support: MinimumCompletePairCount


class PublicationRoundingConfig(FrozenConfigModel):
    f1_accuracy_rates_decimals: DecimalPlaces
    percentage_decimals: DecimalPlaces
    effect_size_decimals: DecimalPlaces
    p_value_significant_digits: SignificantDigits
    p_value_display_floor: PValueDisplayFloor
    seconds_decimals: DecimalPlaces
    byte_units: ByteUnit
    byte_decimals: DecimalPlaces


class MetricsAndStatisticsConfig(FrozenConfigModel):
    metric_aggregation: MetricAggregationConfig
    multiplicity: MultiplicityConfig
    bootstrap: BootstrapConfig
    materiality: MaterialityConfig
    technical_completion: TechnicalCompletionConfig
    publication_rounding: PublicationRoundingConfig


class RepositoryLayoutConfig(FrozenConfigModel):
    source: RepositoryPath
    tests: RepositoryPath
    raw_data: RepositoryPath
    external_data: RepositoryPath
    execution_workspace: RepositoryPath
    manuscript_results: RepositoryPath


class DataLoaderConfig(FrozenConfigModel):
    workers: WorkerCount
    pin_memory: PinMemoryEnabled
    persistent_workers: PersistentWorkersEnabled

    @model_validator(mode="after")
    def _persistent_workers_require_workers(self) -> Self:
        if self.persistent_workers and self.workers == 0:
            raise ValueError("persistent_workers requires workers > 0")
        return self


class TimeoutsSecondsConfig(FrozenConfigModel):
    dataset_preprocessing: TimeoutSeconds
    scientific_cell_phase: TimeoutSeconds
    experiment_analysis_or_report: TimeoutSeconds
    final_export_verification: TimeoutSeconds


class TimingConfig(FrozenConfigModel):
    warmup_forward_passes: WarmupPassCount


class ReferenceEnvironmentConfig(FrozenConfigModel):
    os_name: EnvironmentText
    os_version_id: EnvironmentText
    python_version: EnvironmentText
    cuda_runtime_version: EnvironmentText
    gpu_name: EnvironmentText
    gpu_vram_gigabytes: GigabyteCount
    minimum_cpu_ram_gigabytes: GigabyteCount
    minimum_free_storage_gigabytes: GigabyteCount
    required_gpu_count: GpuCount
    unrar_version: EnvironmentText
    cublas_workspace_config: EnvironmentText


class RuntimeConfig(FrozenConfigModel):
    repository_layout: RepositoryLayoutConfig
    data_loader: DataLoaderConfig
    timeouts_seconds: TimeoutsSecondsConfig
    automatic_infrastructure_retries_per_cell_phase: RetryCount
    timing: TimingConfig
    same_environment_absolute_metric_tolerance: MetricTolerance
    reference_environment: ReferenceEnvironmentConfig


class ByzantineOperatingRegionConfig(FrozenConfigModel):
    maximum_malicious_admissions_within_bound: AdmissionCount


class SafeDormancyConfig(FrozenConfigModel):
    maximum_permanent_singleton_admissions: AdmissionCount


class CapabilityGranularityBoundaryConfig(FrozenConfigModel):
    false_same_capability_certification_rate_minimum: CapabilityCertificationRate


class HeterogeneityBoundaryConfig(FrozenConfigModel):
    legitimate_admission_change_from_natural_maximum: AdmissionRateChange
    worst_domain_target_f1_change_from_natural_maximum: TargetF1Change


class SecondaryGeneralizationConfig(FrozenConfigModel):
    target_f1_noninferiority_margin: TargetF1
    malicious_admission_worsening_maximum: RateWorsening


class ClaimSupportThresholdsConfig(FrozenConfigModel):
    byzantine_operating_region: ByzantineOperatingRegionConfig
    safe_dormancy: SafeDormancyConfig
    capability_granularity_boundary: CapabilityGranularityBoundaryConfig
    heterogeneity_boundary: HeterogeneityBoundaryConfig
    secondary_generalization: SecondaryGeneralizationConfig


class ValidationTolerancesConfig(FrozenConfigModel):
    random_committee_probability_absolute: ProbabilityTolerance
    delay_component_sum_seconds_absolute: DurationToleranceSeconds


class ScientificConfig(FrozenConfigModel):
    datasets: DatasetsConfig
    capability_claim: CapabilityClaimConfig
    protocol: ProtocolConfig
    model: ModelConfig
    seeds_and_determinism: SeedsAndDeterminismConfig
    attacks_and_boundaries: AttacksAndBoundariesConfig
    baselines: BaselinesConfig
    metrics_and_statistics: MetricsAndStatisticsConfig
    runtime: RuntimeConfig
    claim_support_thresholds: ClaimSupportThresholdsConfig
    validation_tolerances: ValidationTolerancesConfig


class TestFixtureConfig(FrozenConfigModel):
    fixture_format_version: ConfigFormatVersion
    holm_fixture_raw_p_values: tuple[tuple[FixtureCaseName, PValue], ...]
    holm_fixture_adjusted_p_values: tuple[tuple[FixtureCaseName, PValue], ...]
    sign_flip_sample_count: MinimumExampleCount
    sign_flip_expected_p_value: PValue
    smoke_model_input_width: ModelInputWidth
    smoke_model_output_width: ModelOutputWidth
    smoke_batch_row_count: ExampleCount
    smoke_fedavg_client_a_example_count: ExampleCount
    smoke_fedavg_client_b_example_count: ExampleCount
    smoke_fedavg_client_a_weights: tuple[MetricValue, ...]
    smoke_fedavg_client_b_weights: tuple[MetricValue, ...]
    smoke_quantile_values: tuple[MetricValue, ...]
    smoke_quantile_probability: QuantileProbability
    smoke_sample_sd_values: tuple[MetricValue, ...]
    smoke_delay_assignment_seconds: WallClockSeconds
    smoke_delay_reproduce_seconds: WallClockSeconds
    smoke_delay_verify_seconds: WallClockSeconds
    smoke_delay_synthesize_seconds: WallClockSeconds
    smoke_bootstrap_values: tuple[MetricValue, ...]
    smoke_confusion_true_labels: tuple[DatasetClassToken, ...]
    smoke_confusion_predicted_labels: tuple[DatasetClassToken, ...]
    smoke_confusion_class_token: DatasetClassToken
    smoke_confusion_true_positive: ConfusionCount
    smoke_confusion_false_positive: ConfusionCount
    smoke_confusion_false_negative: ConfusionCount
    smoke_confusion_true_negative: ConfusionCount
    smoke_nonzero_production_weight: ProductionWeight


class SmokeConfig(FrozenConfigModel):
    smoke_format_version: ConfigFormatVersion
