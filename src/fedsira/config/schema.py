from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, model_validator

from fedsira.domain.enums import ByteUnit, DatasetId
from fedsira.domain.records import (
    MasterSeed,
    NonEmptyString,
    NonNegativeFloat,
    NonNegativeInt,
    Percentage,
    PositiveFloat,
    PositiveInt,
    Probability,
)

RepositoryPath = NonEmptyString
NonEmptyLabel = NonEmptyString


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


def _validate_role_interval_bounds(value: tuple[float, float]) -> tuple[float, float]:
    start, end = value
    if end <= start:
        raise ValueError("role interval end must be strictly greater than start")
    return value


RoleInterval = Annotated[
    tuple[Probability, Probability], AfterValidator(_validate_role_interval_bounds)
]


class RoleIntervals(FrozenModel):
    supported: dict[NonEmptyLabel, RoleInterval]
    target: dict[NonEmptyLabel, RoleInterval]


class SamplingCapsPerDomain(FrozenModel):
    anchor_train_per_supported_class: PositiveInt
    anchor_validation_per_supported_class: PositiveInt
    source_proposal_target: PositiveInt
    source_proposal_supported_replay_per_supported_class: PositiveInt
    candidate_screen_target: PositiveInt
    reproduction_target: PositiveInt
    reproduction_supported_replay_per_supported_class: PositiveInt
    row_verification_target: PositiveInt
    row_verification_supported_per_supported_class: PositiveInt
    final_gate_target: PositiveInt
    final_gate_supported_per_supported_class: PositiveInt
    report_test_target: PositiveInt
    report_test_benign: PositiveInt
    report_test_other_supported_per_class: PositiveInt


class ScalingConfig(FrozenModel):
    zero_standard_deviation_scale: PositiveFloat
    clip_min: float
    clip_max: float

    @model_validator(mode="after")
    def _clip_bounds_ordered(self) -> ScalingConfig:
        if self.clip_max <= self.clip_min:
            raise ValueError("clip_max must be strictly greater than clip_min")
        return self


class PrimaryDatasetConfig(FrozenModel):
    name: DatasetId
    uci_dataset_id: PositiveInt
    doi: NonEmptyLabel
    target_class: NonEmptyLabel
    minimum_target_holding_domains: PositiveInt
    supported_metric_minimum_report_examples_per_class: PositiveInt
    role_intervals: RoleIntervals
    sampling_caps_per_domain: SamplingCapsPerDomain
    scaling: ScalingConfig


class SecondaryDatasetConfig(FrozenModel):
    name: DatasetId
    target_class: NonEmptyLabel
    pseudo_domain_partition_salt: int


class DatasetsConfig(FrozenModel):
    primary: PrimaryDatasetConfig
    secondary: SecondaryDatasetConfig


class EvidenceMinimaConfig(FrozenModel):
    reproduction_target_examples: PositiveInt
    reproduction_supported_control_examples: PositiveInt
    verification_target_examples: PositiveInt
    verification_supported_control_examples: PositiveInt
    proposal_screen_target_examples: PositiveInt


class CapabilityClaimConfig(FrozenModel):
    target_f1_minimum: Probability
    target_f1_gain_over_anchor_minimum: Probability
    supported_macro_f1_drop_maximum: Probability
    benign_false_alarm_rate_increase_maximum: Probability
    candidate_free_anchor_target_f1_maximum: Probability
    evidence_minima: EvidenceMinimaConfig


class ClaimOpeningConfig(FrozenModel):
    screen_domains: PositiveInt
    required_positive_screen_domains: PositiveInt
    candidate_free_required_adequate_domains: PositiveInt

    @model_validator(mode="after")
    def _required_within_screen_domains(self) -> ClaimOpeningConfig:
        if self.required_positive_screen_domains > self.screen_domains:
            raise ValueError("required_positive_screen_domains cannot exceed screen_domains")
        return self


class ProposalScreenConfig(FrozenModel):
    fold_count: PositiveInt
    differential_minimum_nats_per_example: NonNegativeFloat
    matched_controls_per_target: PositiveInt


class ResourceHorizonConfig(FrozenModel):
    maximum_logical_evidence_cycles: PositiveInt
    measurement_cycle_start: NonNegativeInt
    measurement_cycle_end: NonNegativeInt

    @model_validator(mode="after")
    def _measurement_window_ordered(self) -> ResourceHorizonConfig:
        if self.measurement_cycle_end <= self.measurement_cycle_start:
            raise ValueError(
                "measurement_cycle_end must be strictly greater than measurement_cycle_start"
            )
        return self


class VerificationConfig(FrozenModel):
    panel_size: PositiveInt
    maximum_byzantine_verifiers_per_panel: NonNegativeInt
    required_positive_reports: PositiveInt

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
    committee_size: PositiveInt
    maximum_byzantine_reproduction_rows: NonNegativeInt

    @model_validator(mode="after")
    def _committee_consistency(self) -> SynthesisConfig:
        if self.maximum_byzantine_reproduction_rows >= self.committee_size:
            raise ValueError(
                "maximum_byzantine_reproduction_rows must be smaller than committee_size"
            )
        return self


class FinalGateConfig(FrozenModel):
    minimum_adequate_non_source_domains: PositiveInt
    median_target_f1_minimum: Probability
    minimum_domain_target_f1: Probability
    supported_macro_f1_drop_maximum: Probability
    benign_false_alarm_rate_increase_maximum: Probability


class DiagnosticRandomVerifierProfileConfig(FrozenModel):
    byzantine_domain_count: NonNegativeInt
    panel_size: PositiveInt
    required_positive_reports: PositiveInt
    tolerated_contamination_risk: Probability

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
    anchor_and_standard_fl_learning_rate: PositiveFloat
    post_reference_learning_rate: PositiveFloat
    betas: tuple[Probability, Probability]
    epsilon: PositiveFloat
    weight_decay: NonNegativeFloat


class TrainingConfig(FrozenModel):
    batch_size: PositiveInt
    gradient_global_l2_clip: PositiveFloat


class AnchorFedAvgConfig(FrozenModel):
    rounds: PositiveInt
    local_epochs_per_round: PositiveInt
    client_dropout: Probability
    checkpoint_cadence_rounds: PositiveInt
    evaluation_cadence_rounds: PositiveInt


class PostReferenceConfig(FrozenModel):
    local_epochs: PositiveInt
    stability_kl_temperature: PositiveFloat
    stability_weight: NonNegativeFloat
    delta_l2_weight: NonNegativeFloat


class VerifierAwareBackdoorOverrideConfig(FrozenModel):
    local_epochs: PositiveInt
    triggered_backdoor_loss_weight: NonNegativeFloat


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


class ModelReplacementConfig(FrozenModel):
    poison_fraction: Probability
    delta_scale: PositiveFloat


class VerifierAwareConfig(FrozenModel):
    delta_scale: PositiveFloat


class HiddenSourceBackdoorConfig(FrozenModel):
    trigger_value_after_standardization: float
    confirmatory_poison_fraction: Probability
    poison_fraction_sweep: tuple[Probability, ...]


class ByzantineReproductionConfig(FrozenModel):
    compromised_counts: tuple[NonNegativeInt, ...]
    model_replacement: ModelReplacementConfig
    verifier_aware: VerifierAwareConfig


class ByzantineVerifierConfig(FrozenModel):
    compromise_counts: tuple[NonNegativeInt, ...]
    behaviors: tuple[NonEmptyLabel, ...]


class SharedLabelErrorConfig(FrozenModel):
    strengths: tuple[Probability, ...]


class SharedSpuriousFeatureConfig(FrozenModel):
    strengths: tuple[Probability, ...]
    value_after_standardization: float


class AttackerInducedCommonContextConfig(FrozenModel):
    strengths: tuple[Probability, ...]


class CapabilityUnderSpecificationConfig(FrozenModel):
    root_cause_hash_modulus: PositiveInt
    shift_value_after_standardization: float
    contracts: tuple[NonEmptyLabel, ...]
    mixtures: tuple[NonEmptyLabel, ...]


class HeterogeneityConfig(FrozenModel):
    quantity_skew_multipliers: tuple[Probability, ...]
    feature_shift_selected_feature_count: PositiveInt
    feature_shift_magnitudes: tuple[PositiveFloat, ...]


class CleanOracleMaterialityConfig(FrozenModel):
    target_f1_decrease: Probability
    supported_macro_f1_drop: Probability
    benign_false_alarm_rate_increase: Probability


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
    reconstruction_local_epochs: PositiveInt
    normalization_epsilon: PositiveFloat
    calibration_percentile: Percentage


class DensityClusterTrimmedMeanConfig(FrozenModel):
    dbscan_epsilon: PositiveFloat
    dbscan_min_samples: PositiveInt
    trim_each_tail_count: NonNegativeInt
    minimum_cluster_size_for_trimming: PositiveInt


class RecoveryAfterSourceAdmissionConfig(FrozenModel):
    backdoor_alarm_percentile: Percentage
    recovery_rounds: PositiveInt


class SourceUpdateSanitizationConfig(FrozenModel):
    coordinate_bound_percentile: Percentage


class ParameterSimilarityConfig(FrozenModel):
    required_committed_rows: PositiveInt
    cosine_similarity_minimum: Probability


class ThreeRowCoordinateMedianConfig(FrozenModel):
    row_count: PositiveInt
    assumed_byzantine_rows: NonNegativeInt

    @model_validator(mode="after")
    def _byzantine_within_rows(self) -> ThreeRowCoordinateMedianConfig:
        if self.assumed_byzantine_rows >= self.row_count:
            raise ValueError("assumed_byzantine_rows must be smaller than row_count")
        return self


class BaselinesConfig(FrozenModel):
    local_only_reference_epochs: PositiveInt
    centralized_reference_epochs: PositiveInt
    fedavg_post_reference_rounds: PositiveInt
    multiple_model_certified_ensemble_group_count: PositiveInt
    multiple_model_certified_ensemble_post_reference_rounds: PositiveInt
    reconstruction_filter: ReconstructionFilterConfig
    density_cluster_trimmed_mean: DensityClusterTrimmedMeanConfig
    secure_continual_assessment_post_reference_rounds: PositiveInt
    recovery_after_source_admission: RecoveryAfterSourceAdmissionConfig
    source_update_sanitization: SourceUpdateSanitizationConfig
    parameter_similarity: ParameterSimilarityConfig
    three_row_coordinate_median: ThreeRowCoordinateMedianConfig
    krum_robust_aggregation_post_reference_rounds: PositiveInt


class MetricAggregationConfig(FrozenModel):
    generic_defined_domain_fraction_minimum: Probability


class MultiplicityConfig(FrozenModel):
    family_wise_alpha: Probability


class BootstrapConfig(FrozenModel):
    confidence_level: Probability
    resamples: PositiveInt


class MaterialityConfig(FrozenModel):
    target_f1_gain_minimum: Probability
    supported_macro_f1_noninferiority_margin: Probability
    benign_false_alarm_rate_noninferiority_margin: Probability
    source_exclusion_asr_reduction_minimum: Probability
    malicious_admission_reduction_minimum: Probability
    legitimate_admission_noninferiority_margin: Probability
    worst_domain_target_f1_gain_minimum: Probability
    false_launch_reduction_minimum: Probability
    reproduction_attempt_relative_reduction_minimum: Probability
    post_evidence_overhead_relative_reduction_minimum: Probability
    proposal_malicious_admission_worsening_maximum: Probability


class TechnicalCompletionConfig(FrozenModel):
    minimum_complete_pairs_for_claim_support: PositiveInt


class PublicationRoundingConfig(FrozenModel):
    f1_accuracy_rates_decimals: NonNegativeInt
    percentage_decimals: NonNegativeInt
    effect_size_decimals: NonNegativeInt
    p_value_significant_digits: PositiveInt
    p_value_display_floor: PositiveFloat
    seconds_decimals: NonNegativeInt
    byte_units: ByteUnit
    byte_decimals: NonNegativeInt


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
    workers: NonNegativeInt
    pin_memory: bool
    persistent_workers: bool


class TimeoutsSecondsConfig(FrozenModel):
    dataset_preprocessing: PositiveInt
    scientific_cell_phase: PositiveInt
    experiment_analysis_or_report: PositiveInt
    final_export_verification: PositiveInt


class TimingConfig(FrozenModel):
    warmup_forward_passes: NonNegativeInt


class RuntimeConfig(FrozenModel):
    repository_layout: RepositoryLayoutConfig
    data_loader: DataLoaderConfig
    timeouts_seconds: TimeoutsSecondsConfig
    automatic_infrastructure_retries_per_cell_phase: NonNegativeInt
    timing: TimingConfig
    same_environment_absolute_metric_tolerance: PositiveFloat


class ByzantineOperatingRegionConfig(FrozenModel):
    maximum_malicious_admissions_within_bound: NonNegativeInt


class SafeDormancyConfig(FrozenModel):
    maximum_permanent_singleton_admissions: NonNegativeInt


class CapabilityGranularityBoundaryConfig(FrozenModel):
    false_same_capability_certification_rate_minimum: Probability


class HeterogeneityBoundaryConfig(FrozenModel):
    legitimate_admission_change_from_natural_maximum: Probability
    worst_domain_target_f1_change_from_natural_maximum: Probability


class SecondaryGeneralizationConfig(FrozenModel):
    target_f1_noninferiority_margin: Probability
    malicious_admission_worsening_maximum: Probability


class ClaimSupportThresholdsConfig(FrozenModel):
    byzantine_operating_region: ByzantineOperatingRegionConfig
    safe_dormancy: SafeDormancyConfig
    capability_granularity_boundary: CapabilityGranularityBoundaryConfig
    heterogeneity_boundary: HeterogeneityBoundaryConfig
    secondary_generalization: SecondaryGeneralizationConfig


class ValidationTolerancesConfig(FrozenModel):
    random_committee_probability_absolute: PositiveFloat
    delay_component_sum_seconds_absolute: PositiveFloat


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
    fixture_format_version: PositiveInt


class SmokeConfig(FrozenModel):
    smoke_format_version: PositiveInt
