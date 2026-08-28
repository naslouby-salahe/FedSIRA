from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, model_validator

from fedsira.domain.enums import (
    ByteUnit,
    ByzantineVerifierBehavior,
    CapabilityContractScope,
    DatasetId,
    RootCauseMixture,
)
from fedsira.domain.records import (
    AdmissionCount,
    BatchSize,
    BenignFalseAlarmRateIncrease,
    BootstrapResampleCount,
    CadenceRounds,
    CanonicalToken,
    ClientDropout,
    ClusterSize,
    CommitteeSize,
    ConfidenceLevel,
    ConfigFormatVersion,
    ContaminationRisk,
    DbscanEpsilon,
    DecimalPlaces,
    DeltaScale,
    DifferentialNatsPerExample,
    Doi,
    DomainCount,
    EvidenceCycleIndex,
    FamilyWiseAlpha,
    FeatureCount,
    FederatedRoundCount,
    FoldCount,
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
    MinimumCompletePairCount,
    MinimumExampleCount,
    NonNegativeInt,
    NumericalEpsilon,
    OptimizerEpsilon,
    PValueDisplayFloor,
    PartitionSalt,
    Percentage,
    PersistentWorkersEnabled,
    PinMemoryEnabled,
    PoisonFraction,
    PositiveFloat,
    Probability,
    RegularizationWeight,
    RepositoryPath,
    ReproductionRowCount,
    RetryCount,
    ScaleFactor,
    ScreenDomainCount,
    SeedCount,
    SignificantDigits,
    StandardizedValue,
    SupportedMacroF1Drop,
    TargetF1,
    TargetF1Gain,
    Temperature,
    TimeoutSeconds,
    TrimCount,
    UciDatasetId,
    VerifierCount,
    WarmupPassCount,
    WeightDecay,
    WorkerCount,
    DatasetClassToken,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


def _validate_role_interval_bounds(
    value: tuple[Probability, Probability],
) -> tuple[Probability, Probability]:
    start, end = value
    if end <= start:
        raise ValueError("role interval end must be strictly greater than start")
    return value


RoleInterval = Annotated[
    tuple[Probability, Probability], AfterValidator(_validate_role_interval_bounds)
]


class RoleIntervals(FrozenModel):
    supported: dict[CanonicalToken, RoleInterval]
    target: dict[CanonicalToken, RoleInterval]


class SamplingCapsPerDomain(FrozenModel):
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


class ScalingConfig(FrozenModel):
    zero_standard_deviation_scale: ScaleFactor
    clip_min: StandardizedValue
    clip_max: StandardizedValue

    @model_validator(mode="after")
    def _clip_bounds_ordered(self) -> ScalingConfig:
        if self.clip_max <= self.clip_min:
            raise ValueError("clip_max must be strictly greater than clip_min")
        return self


class PrimaryDatasetConfig(FrozenModel):
    name: DatasetId
    uci_dataset_id: UciDatasetId
    doi: Doi
    target_class: DatasetClassToken
    minimum_target_holding_domains: DomainCount
    supported_metric_minimum_report_examples_per_class: MinimumExampleCount
    role_intervals: RoleIntervals
    sampling_caps_per_domain: SamplingCapsPerDomain
    scaling: ScalingConfig


class SecondaryDatasetConfig(FrozenModel):
    name: DatasetId
    target_class: DatasetClassToken
    pseudo_domain_partition_salt: PartitionSalt


class DatasetsConfig(FrozenModel):
    primary: PrimaryDatasetConfig
    secondary: SecondaryDatasetConfig


class EvidenceMinimaConfig(FrozenModel):
    reproduction_target_examples: MinimumExampleCount
    reproduction_supported_control_examples: MinimumExampleCount
    verification_target_examples: MinimumExampleCount
    verification_supported_control_examples: MinimumExampleCount
    proposal_screen_target_examples: MinimumExampleCount


class CapabilityClaimConfig(FrozenModel):
    target_f1_minimum: TargetF1
    target_f1_gain_over_anchor_minimum: TargetF1Gain
    supported_macro_f1_drop_maximum: SupportedMacroF1Drop
    benign_false_alarm_rate_increase_maximum: BenignFalseAlarmRateIncrease
    candidate_free_anchor_target_f1_maximum: TargetF1
    evidence_minima: EvidenceMinimaConfig


class ClaimOpeningConfig(FrozenModel):
    screen_domains: ScreenDomainCount
    required_positive_screen_domains: ScreenDomainCount
    candidate_free_required_adequate_domains: DomainCount

    @model_validator(mode="after")
    def _required_within_screen_domains(self) -> ClaimOpeningConfig:
        if self.required_positive_screen_domains > self.screen_domains:
            raise ValueError("required_positive_screen_domains cannot exceed screen_domains")
        return self


class ProposalScreenConfig(FrozenModel):
    fold_count: FoldCount
    differential_minimum_nats_per_example: DifferentialNatsPerExample
    matched_controls_per_target: MatchedControlCount


class ResourceHorizonConfig(FrozenModel):
    maximum_logical_evidence_cycles: LogicalEvidenceCycleCount
    measurement_cycle_start: EvidenceCycleIndex
    measurement_cycle_end: EvidenceCycleIndex

    @model_validator(mode="after")
    def _measurement_window_ordered(self) -> ResourceHorizonConfig:
        if self.measurement_cycle_end <= self.measurement_cycle_start:
            raise ValueError(
                "measurement_cycle_end must be strictly greater than measurement_cycle_start"
            )
        return self


class VerificationConfig(FrozenModel):
    panel_size: VerifierCount
    maximum_byzantine_verifiers_per_panel: ReproductionRowCount
    required_positive_reports: VerifierCount

    @model_validator(mode="after")
    def _panel_consistency(self) -> VerificationConfig:
        if self.required_positive_reports > self.panel_size:
            raise ValueError("required_positive_reports cannot exceed panel_size")
        if self.maximum_byzantine_verifiers_per_panel >= self.panel_size:
            raise ValueError(
                "maximum_byzantine_verifiers_per_panel must be smaller than panel_size"
            )
        return self


class SynthesisConfig(FrozenModel):
    committee_size: CommitteeSize
    maximum_byzantine_reproduction_rows: ReproductionRowCount

    @model_validator(mode="after")
    def _committee_consistency(self) -> SynthesisConfig:
        if self.maximum_byzantine_reproduction_rows >= self.committee_size:
            raise ValueError(
                "maximum_byzantine_reproduction_rows must be smaller than committee_size"
            )
        return self


class FinalGateConfig(FrozenModel):
    minimum_adequate_non_source_domains: DomainCount
    median_target_f1_minimum: TargetF1
    minimum_domain_target_f1: TargetF1
    supported_macro_f1_drop_maximum: SupportedMacroF1Drop
    benign_false_alarm_rate_increase_maximum: BenignFalseAlarmRateIncrease


class DiagnosticRandomVerifierProfileConfig(FrozenModel):
    byzantine_domain_count: ReproductionRowCount
    panel_size: VerifierCount
    required_positive_reports: VerifierCount
    tolerated_contamination_risk: ContaminationRisk

    @model_validator(mode="after")
    def _required_within_panel(self) -> DiagnosticRandomVerifierProfileConfig:
        if self.required_positive_reports > self.panel_size:
            raise ValueError("required_positive_reports cannot exceed panel_size")
        return self


class ProtocolConfig(FrozenModel):
    claim_opening: ClaimOpeningConfig
    proposal_screen: ProposalScreenConfig
    resource_horizon: ResourceHorizonConfig
    verification: VerificationConfig
    synthesis: SynthesisConfig
    final_gate: FinalGateConfig
    diagnostic_random_verifier_profile: DiagnosticRandomVerifierProfileConfig


class OptimizerConfig(FrozenModel):
    anchor_and_standard_fl_learning_rate: LearningRate
    post_reference_learning_rate: LearningRate
    betas: tuple[Probability, Probability]
    epsilon: OptimizerEpsilon
    weight_decay: WeightDecay


class TrainingConfig(FrozenModel):
    batch_size: BatchSize
    gradient_global_l2_clip: GradientL2Clip


class AnchorFedAvgConfig(FrozenModel):
    rounds: FederatedRoundCount
    local_epochs_per_round: LocalEpochCount
    client_dropout: ClientDropout
    checkpoint_cadence_rounds: CadenceRounds
    evaluation_cadence_rounds: CadenceRounds


class PostReferenceConfig(FrozenModel):
    local_epochs: LocalEpochCount
    stability_kl_temperature: Temperature
    stability_weight: LossWeight
    delta_l2_weight: RegularizationWeight


class VerifierAwareBackdoorOverrideConfig(FrozenModel):
    local_epochs: LocalEpochCount
    triggered_backdoor_loss_weight: LossWeight


class ModelConfig(FrozenModel):
    optimizer: OptimizerConfig
    training: TrainingConfig
    anchor_fedavg: AnchorFedAvgConfig
    post_reference: PostReferenceConfig
    verifier_aware_backdoor_override: VerifierAwareBackdoorOverrideConfig


class SeedsAndDeterminismConfig(FrozenModel):
    master_seeds: tuple[MasterSeed, ...]
    analysis_seed: MasterSeed
    smoke_seed: MasterSeed

    @model_validator(mode="after")
    def _master_seeds_are_distinct(self) -> SeedsAndDeterminismConfig:
        if len(set(self.master_seeds)) != len(self.master_seeds):
            raise ValueError("master_seeds must not contain duplicates")
        if len(self.master_seeds) == 0:
            raise ValueError("master_seeds must not be empty")
        return self

    @property
    def confirmatory_seed_count(self) -> SeedCount:
        return len(self.master_seeds)


class ModelReplacementConfig(FrozenModel):
    poison_fraction: PoisonFraction
    delta_scale: DeltaScale


class VerifierAwareConfig(FrozenModel):
    delta_scale: DeltaScale


class HiddenSourceBackdoorConfig(FrozenModel):
    trigger_value_after_standardization: StandardizedValue
    confirmatory_poison_fraction: PoisonFraction
    poison_fraction_sweep: tuple[PoisonFraction, ...]


class ByzantineReproductionConfig(FrozenModel):
    compromised_counts: tuple[ReproductionRowCount, ...]
    model_replacement: ModelReplacementConfig
    verifier_aware: VerifierAwareConfig


class ByzantineVerifierConfig(FrozenModel):
    compromise_counts: tuple[ReproductionRowCount, ...]
    behaviors: tuple[ByzantineVerifierBehavior, ...]


class SharedLabelErrorConfig(FrozenModel):
    strengths: tuple[Probability, ...]


class SharedSpuriousFeatureConfig(FrozenModel):
    strengths: tuple[Probability, ...]
    value_after_standardization: StandardizedValue


class AttackerInducedCommonContextConfig(FrozenModel):
    strengths: tuple[Probability, ...]


class CapabilityUnderSpecificationConfig(FrozenModel):
    root_cause_hash_modulus: HashModulus
    shift_value_after_standardization: StandardizedValue
    contracts: tuple[CapabilityContractScope, ...]
    mixtures: tuple[RootCauseMixture, ...]


class HeterogeneityConfig(FrozenModel):
    quantity_skew_multipliers: tuple[HeterogeneityMultiplier, ...]
    feature_shift_selected_feature_count: FeatureCount
    feature_shift_magnitudes: tuple[PositiveFloat, ...]


class CleanOracleMaterialityConfig(FrozenModel):
    target_f1_decrease: TargetF1
    supported_macro_f1_drop: SupportedMacroF1Drop
    benign_false_alarm_rate_increase: BenignFalseAlarmRateIncrease


class AttacksAndBoundariesConfig(FrozenModel):
    hidden_source_backdoor: HiddenSourceBackdoorConfig
    byzantine_reproduction: ByzantineReproductionConfig
    byzantine_verifier: ByzantineVerifierConfig
    shared_label_error: SharedLabelErrorConfig
    shared_spurious_feature: SharedSpuriousFeatureConfig
    attacker_induced_common_context: AttackerInducedCommonContextConfig
    capability_under_specification: CapabilityUnderSpecificationConfig
    heterogeneity: HeterogeneityConfig
    clean_oracle_materiality: CleanOracleMaterialityConfig


class ReconstructionFilterConfig(FrozenModel):
    reconstruction_local_epochs: LocalEpochCount
    normalization_epsilon: NumericalEpsilon
    calibration_percentile: Percentage


class DensityClusterTrimmedMeanConfig(FrozenModel):
    dbscan_epsilon: DbscanEpsilon
    dbscan_min_samples: ClusterSize
    trim_each_tail_count: TrimCount
    minimum_cluster_size_for_trimming: ClusterSize


class RecoveryAfterSourceAdmissionConfig(FrozenModel):
    backdoor_alarm_percentile: Percentage
    recovery_rounds: FederatedRoundCount


class SourceUpdateSanitizationConfig(FrozenModel):
    coordinate_bound_percentile: Percentage


class ParameterSimilarityConfig(FrozenModel):
    required_committed_rows: CommitteeSize
    cosine_similarity_minimum: Probability


class ThreeRowCoordinateMedianConfig(FrozenModel):
    row_count: CommitteeSize
    assumed_byzantine_rows: ReproductionRowCount

    @model_validator(mode="after")
    def _byzantine_within_rows(self) -> ThreeRowCoordinateMedianConfig:
        if self.assumed_byzantine_rows >= self.row_count:
            raise ValueError("assumed_byzantine_rows must be smaller than row_count")
        return self


class BaselinesConfig(FrozenModel):
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


class MetricAggregationConfig(FrozenModel):
    generic_defined_domain_fraction_minimum: Probability


class MultiplicityConfig(FrozenModel):
    family_wise_alpha: FamilyWiseAlpha


class BootstrapConfig(FrozenModel):
    confidence_level: ConfidenceLevel
    resamples: BootstrapResampleCount


class MaterialityConfig(FrozenModel):
    target_f1_gain_minimum: TargetF1Gain
    supported_macro_f1_noninferiority_margin: SupportedMacroF1Drop
    benign_false_alarm_rate_noninferiority_margin: BenignFalseAlarmRateIncrease
    source_exclusion_asr_reduction_minimum: Probability
    malicious_admission_reduction_minimum: Probability
    legitimate_admission_noninferiority_margin: Probability
    worst_domain_target_f1_gain_minimum: TargetF1Gain
    false_launch_reduction_minimum: Probability
    reproduction_attempt_relative_reduction_minimum: Probability
    post_evidence_overhead_relative_reduction_minimum: Probability
    proposal_malicious_admission_worsening_maximum: Probability


class TechnicalCompletionConfig(FrozenModel):
    minimum_complete_pairs_for_claim_support: MinimumCompletePairCount


class PublicationRoundingConfig(FrozenModel):
    f1_accuracy_rates_decimals: DecimalPlaces
    percentage_decimals: DecimalPlaces
    effect_size_decimals: DecimalPlaces
    p_value_significant_digits: SignificantDigits
    p_value_display_floor: PValueDisplayFloor
    seconds_decimals: DecimalPlaces
    byte_units: ByteUnit
    byte_decimals: DecimalPlaces


class MetricsAndStatisticsConfig(FrozenModel):
    metric_aggregation: MetricAggregationConfig
    multiplicity: MultiplicityConfig
    bootstrap: BootstrapConfig
    materiality: MaterialityConfig
    technical_completion: TechnicalCompletionConfig
    publication_rounding: PublicationRoundingConfig


class RepositoryLayoutConfig(FrozenModel):
    source: RepositoryPath
    tests: RepositoryPath
    raw_data: RepositoryPath
    external_data: RepositoryPath
    execution_workspace: RepositoryPath
    manuscript_results: RepositoryPath


class DataLoaderConfig(FrozenModel):
    workers: WorkerCount
    pin_memory: PinMemoryEnabled
    persistent_workers: PersistentWorkersEnabled


class TimeoutsSecondsConfig(FrozenModel):
    dataset_preprocessing: TimeoutSeconds
    scientific_cell_phase: TimeoutSeconds
    experiment_analysis_or_report: TimeoutSeconds
    final_export_verification: TimeoutSeconds


class TimingConfig(FrozenModel):
    warmup_forward_passes: WarmupPassCount


class RuntimeConfig(FrozenModel):
    repository_layout: RepositoryLayoutConfig
    data_loader: DataLoaderConfig
    timeouts_seconds: TimeoutsSecondsConfig
    automatic_infrastructure_retries_per_cell_phase: RetryCount
    timing: TimingConfig
    same_environment_absolute_metric_tolerance: MetricTolerance


class ByzantineOperatingRegionConfig(FrozenModel):
    maximum_malicious_admissions_within_bound: AdmissionCount


class SafeDormancyConfig(FrozenModel):
    maximum_permanent_singleton_admissions: AdmissionCount


class CapabilityGranularityBoundaryConfig(FrozenModel):
    false_same_capability_certification_rate_minimum: Probability


class HeterogeneityBoundaryConfig(FrozenModel):
    legitimate_admission_change_from_natural_maximum: Probability
    worst_domain_target_f1_change_from_natural_maximum: Probability


class SecondaryGeneralizationConfig(FrozenModel):
    target_f1_noninferiority_margin: TargetF1
    malicious_admission_worsening_maximum: Probability


class ClaimSupportThresholdsConfig(FrozenModel):
    byzantine_operating_region: ByzantineOperatingRegionConfig
    safe_dormancy: SafeDormancyConfig
    capability_granularity_boundary: CapabilityGranularityBoundaryConfig
    heterogeneity_boundary: HeterogeneityBoundaryConfig
    secondary_generalization: SecondaryGeneralizationConfig


class ValidationTolerancesConfig(FrozenModel):
    random_committee_probability_absolute: MetricTolerance
    delay_component_sum_seconds_absolute: MetricTolerance


class ScientificConfig(FrozenModel):
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


class TestFixtureConfig(FrozenModel):
    fixture_format_version: ConfigFormatVersion
    holm_fixture_raw_p_values: tuple[tuple[CanonicalToken, Probability], ...]
    holm_fixture_adjusted_p_values: tuple[tuple[CanonicalToken, Probability], ...]
    sign_flip_sample_count: MinimumExampleCount
    sign_flip_expected_p_value: Probability


class SmokeConfig(FrozenModel):
    smoke_format_version: ConfigFormatVersion
