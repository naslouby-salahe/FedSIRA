from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from enum import StrEnum

from fedsira.analysis.statistics import (
    exact_sign_flip_non_inferiority_p_value,
    exact_sign_flip_two_sided_p_value,
    holm_adjusted_p_values,
)
from fedsira.baselines.registry import BaselineIdentity
from fedsira.config.schema import BootstrapConfig, MaterialityConfig, MultiplicityConfig
from fedsira.domain.enums import CapabilityContractScope, DatasetId
from fedsira.domain.records import (
    CapabilityCertificationRate,
    ComparisonMargin,
    ComparisonName,
    CompleteSeedCount,
    ConfidenceIntervalBound,
    EffectSize,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MaterialThreshold,
    MaterialityDecision,
    MethodName,
    MetricDifference,
    PValue,
    PairedDifference,
    ScenarioName,
)
from fedsira.evaluation.aggregation import bootstrap_percentile_confidence_interval
from fedsira.experiments.registry import (
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    MECHANISM_ABLATION_NAME,
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    AblationVariant,
    ClaimFamily,
    ExperimentClass,
    ExternalVerificationCondition,
    HeterogeneityRegime,
    OpeningMode,
    PluralityCondition,
    PrimaryScenario,
    ProposalEpisode,
    ReproducerCondition,
    RootCauseMixture,
    SecondaryScenario,
    SourceExclusionMethod,
    VerifierCondition,
)


class ComparisonTestKind(StrEnum):
    SUPERIORITY = "superiority"
    NON_INFERIORITY = "non-inferiority"


class ComparisonOrientation(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class ComparisonState(StrEnum):
    UNDEFINED = "Undefined"
    PENDING = "Pending"
    PASSED = "Passed"
    FAILED = "Failed"
    INCONCLUSIVE_TECHNICAL = "Inconclusive Technical"


class ComparisonMetric(StrEnum):
    FALSE_LAUNCH = "false-launch"
    REPRODUCTION_ATTEMPTS = "reproduction-attempts"
    POST_EVIDENCE_OVERHEAD = "post-evidence-overhead"
    LEGITIMATE_ADMISSION = "legitimate-admission"
    MALICIOUS_ADMISSION = "malicious-admission"
    WORST_DOMAIN_TARGET_F1 = "worst-domain-target-f1"
    ATTACK_SUCCESS_RATE = "asr"
    TARGET_F1 = "target-f1"
    SUPPORTED_MACRO_F1_HARM = "supported-macro-f1-harm"
    BENIGN_FALSE_ALARM_RATE_INCREASE = "benign-far-increase"
    FALSE_SAME_CAPABILITY_CERTIFICATION_RATE = "false-same-capability-certification-rate"


class CoreMethodIdentity(StrEnum):
    RESOLVED_FEDSIRA_CORE = "Resolved FedSIRA Core"
    FULL_PLURALITY_PATH = "Full Plurality Path"
    ZERO_REFERENCE = "zero"


class PairingKey(FrozenDomainModel):
    dataset: DatasetId
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    master_seed: MasterSeed

    @property
    def canonical(self) -> ComparisonName:
        return "|".join(
            (
                self.dataset.value,
                self.experiment,
                self.scientific_scenario,
                str(self.master_seed),
            )
        )


class ComparisonDefinition(FrozenDomainModel):
    canonical_name: ComparisonName
    family: ClaimFamily
    method: MethodName
    reference: MethodName
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    metric: ComparisonMetric
    orientation: ComparisonOrientation
    test_kind: ComparisonTestKind
    margin: ComparisonMargin | None = None
    material_threshold: MaterialThreshold | None = None


class ComparisonResult(FrozenDomainModel):
    definition: ComparisonDefinition
    paired_differences: tuple[PairedDifference, ...]
    complete_seed_count: CompleteSeedCount
    mean_paired_difference: MetricDifference | None
    median_paired_difference: MetricDifference | None
    paired_standardized_effect: EffectSize | None
    raw_p_value: PValue | None
    adjusted_p_value: PValue | None
    confidence_interval: tuple[ConfidenceIntervalBound, ConfidenceIntervalBound] | None
    materiality_passes: MaterialityDecision | None
    comparison_state: ComparisonState


class ComparisonFamilyResult(FrozenDomainModel):
    family: ClaimFamily
    comparisons: tuple[ComparisonResult, ...]


def complete_paired_seeds(
    seed_metrics: Mapping[MasterSeed, Mapping[MethodName, MetricDifference | None]],
    method: MethodName,
    reference: MethodName,
    metric: ComparisonMetric,
) -> tuple[MasterSeed, ...]:
    del metric
    return tuple(
        master_seed
        for master_seed, values in sorted(seed_metrics.items())
        if values.get(method) is not None and values.get(reference) is not None
    )


def _signed_standard_deviation(
    values: Sequence[PairedDifference],
) -> MetricDifference | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def _effect_size(differences: Sequence[PairedDifference]) -> EffectSize | None:
    if not differences:
        return None
    mean = sum(differences) / len(differences)
    standard_deviation = _signed_standard_deviation(differences)
    if standard_deviation is None or standard_deviation == 0.0:
        if mean > 0:
            return math.inf
        if mean < 0:
            return -math.inf
        return 0.0
    return mean / standard_deviation


def evaluate_comparison(
    definition: ComparisonDefinition,
    paired_differences: Sequence[PairedDifference],
    multiplicity_config: MultiplicityConfig,
    bootstrap_config: BootstrapConfig,
    analysis_seed: MasterSeed,
) -> ComparisonResult:
    del multiplicity_config
    difference_vector = tuple(paired_differences)
    complete_seed_count = len(difference_vector)
    if complete_seed_count == 0:
        return ComparisonResult(
            definition=definition,
            paired_differences=difference_vector,
            complete_seed_count=0,
            mean_paired_difference=None,
            median_paired_difference=None,
            paired_standardized_effect=None,
            raw_p_value=None,
            adjusted_p_value=None,
            confidence_interval=None,
            materiality_passes=None,
            comparison_state=ComparisonState.UNDEFINED,
        )
    mean_difference = sum(difference_vector) / complete_seed_count
    sorted_differences = sorted(difference_vector)
    if complete_seed_count % 2 == 1:
        median_difference = sorted_differences[complete_seed_count // 2]
    else:
        median_difference = (
            sorted_differences[complete_seed_count // 2 - 1]
            + sorted_differences[complete_seed_count // 2]
        ) / 2
    standardized_effect = _effect_size(difference_vector)
    confidence_interval = bootstrap_percentile_confidence_interval(
        difference_vector, bootstrap_config, analysis_seed
    )
    if definition.test_kind is ComparisonTestKind.SUPERIORITY:
        raw_p_value = exact_sign_flip_two_sided_p_value(difference_vector)
    else:
        if definition.margin is None:
            raise ValueError(
                f"non-inferiority comparison {definition.canonical_name} requires a margin"
            )
        raw_p_value = exact_sign_flip_non_inferiority_p_value(difference_vector, definition.margin)
    return ComparisonResult(
        definition=definition,
        paired_differences=difference_vector,
        complete_seed_count=complete_seed_count,
        mean_paired_difference=mean_difference,
        median_paired_difference=median_difference,
        paired_standardized_effect=standardized_effect,
        raw_p_value=raw_p_value,
        adjusted_p_value=raw_p_value,
        confidence_interval=confidence_interval,
        materiality_passes=None,
        comparison_state=ComparisonState.PENDING,
    )


def apply_holm_adjustment(
    family_result: ComparisonFamilyResult,
    multiplicity_config: MultiplicityConfig,
) -> ComparisonFamilyResult:
    raw_values = tuple(
        (result.definition.canonical_name, result.raw_p_value)
        for result in family_result.comparisons
        if result.raw_p_value is not None
    )
    adjusted_by_name = dict(holm_adjusted_p_values(raw_values))
    updated_comparisons: list[ComparisonResult] = []
    for result in family_result.comparisons:
        adjusted_p_value = adjusted_by_name.get(result.definition.canonical_name)
        if adjusted_p_value is None:
            updated_comparisons.append(result)
            continue
        if result.definition.material_threshold is None or result.mean_paired_difference is None:
            materiality_passes = None
        else:
            materiality_passes = (
                abs(result.mean_paired_difference) >= result.definition.material_threshold
            )
        statistical_pass = adjusted_p_value < multiplicity_config.family_wise_alpha
        materiality_pass = materiality_passes is not False
        comparison_state = (
            ComparisonState.PASSED
            if statistical_pass and materiality_pass
            else ComparisonState.FAILED
        )
        updated_comparisons.append(
            result.model_copy(
                update={
                    "adjusted_p_value": adjusted_p_value,
                    "materiality_passes": materiality_passes,
                    "comparison_state": comparison_state,
                }
            )
        )
    return ComparisonFamilyResult(
        family=family_result.family,
        comparisons=tuple(updated_comparisons),
    )


def comparison_canonical_name(
    family: ClaimFamily,
    experiment: ExperimentName,
    scientific_scenario: ScenarioName,
    method: MethodName,
    reference: MethodName,
    metric: ComparisonMetric,
    test_kind: ComparisonTestKind,
) -> ComparisonName:
    return (
        f"{family.value}|{experiment}|{scientific_scenario}|"
        f"{method}__vs__{reference}|{metric.value}|{test_kind.value}"
    )


def _definition(
    family: ClaimFamily,
    experiment: ExperimentName,
    scientific_scenario: ScenarioName,
    method: MethodName,
    reference: MethodName,
    metric: ComparisonMetric,
    orientation: ComparisonOrientation,
    test_kind: ComparisonTestKind,
    margin: ComparisonMargin | None = None,
    material_threshold: MaterialThreshold | None = None,
) -> ComparisonDefinition:
    return ComparisonDefinition(
        canonical_name=comparison_canonical_name(
            family,
            experiment,
            scientific_scenario,
            method,
            reference,
            metric,
            test_kind,
        ),
        family=family,
        method=method,
        reference=reference,
        experiment=experiment,
        scientific_scenario=scientific_scenario,
        metric=metric,
        orientation=orientation,
        test_kind=test_kind,
        margin=margin,
        material_threshold=material_threshold,
    )


PRIMARY_SCENARIOS: tuple[ScenarioName, ...] = (
    PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
    PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
    PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT.value,
)


def _proposal_screen_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.PROPOSAL_SCREEN_NECESSITY
    experiment = PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME
    method = OpeningMode.PROPOSAL_ASSISTED.value
    reference = OpeningMode.CANDIDATE_FREE.value
    return (
        _definition(
            family,
            experiment,
            ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value,
            method,
            reference,
            ComparisonMetric.FALSE_LAUNCH,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.false_launch_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.IRRELEVANT_SOURCE_IMPROVEMENT.value,
            method,
            reference,
            ComparisonMetric.FALSE_LAUNCH,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.false_launch_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,
            method,
            reference,
            ComparisonMetric.REPRODUCTION_ATTEMPTS,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.reproduction_attempt_relative_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value,
            method,
            reference,
            ComparisonMetric.REPRODUCTION_ATTEMPTS,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.reproduction_attempt_relative_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.IRRELEVANT_SOURCE_IMPROVEMENT.value,
            method,
            reference,
            ComparisonMetric.REPRODUCTION_ATTEMPTS,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.reproduction_attempt_relative_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
            method,
            reference,
            ComparisonMetric.REPRODUCTION_ATTEMPTS,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.reproduction_attempt_relative_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,
            method,
            reference,
            ComparisonMetric.POST_EVIDENCE_OVERHEAD,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.post_evidence_overhead_relative_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value,
            method,
            reference,
            ComparisonMetric.POST_EVIDENCE_OVERHEAD,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.post_evidence_overhead_relative_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.IRRELEVANT_SOURCE_IMPROVEMENT.value,
            method,
            reference,
            ComparisonMetric.POST_EVIDENCE_OVERHEAD,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.post_evidence_overhead_relative_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
            method,
            reference,
            ComparisonMetric.POST_EVIDENCE_OVERHEAD,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.post_evidence_overhead_relative_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,
            method,
            reference,
            ComparisonMetric.LEGITIMATE_ADMISSION,
            ComparisonOrientation.HIGHER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.legitimate_admission_noninferiority_margin,
        ),
        _definition(
            family,
            experiment,
            ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
            method,
            reference,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.supported_macro_f1_noninferiority_margin,
        ),
    )


def _plurality_comparisons(materiality: MaterialityConfig) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.PLURALITY_NECESSITY
    experiment = SINGLE_REPRODUCTION_NECESSITY_NAME
    method = CoreMethodIdentity.FULL_PLURALITY_PATH.value
    reference = BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value
    conditions = (
        PluralityCondition.HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0.value,
        PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
    )
    return tuple(
        _definition(
            family,
            experiment,
            condition,
            method,
            reference,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.malicious_admission_reduction_minimum,
        )
        for condition in conditions
    ) + tuple(
        _definition(
            family,
            experiment,
            condition,
            method,
            reference,
            ComparisonMetric.WORST_DOMAIN_TARGET_F1,
            ComparisonOrientation.HIGHER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.worst_domain_target_f1_gain_minimum,
        )
        for condition in conditions
    )


def _source_exclusion_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM
    experiment = SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME
    scenario = PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value
    method = SourceExclusionMethod.FULL_FEDSIRA.value
    reference = BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value
    return (
        _definition(
            family,
            experiment,
            scenario,
            method,
            reference,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.source_exclusion_asr_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            scenario,
            method,
            reference,
            ComparisonMetric.TARGET_F1,
            ComparisonOrientation.HIGHER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.supported_macro_f1_noninferiority_margin,
        ),
        _definition(
            family,
            experiment,
            scenario,
            method,
            reference,
            ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.supported_macro_f1_noninferiority_margin,
        ),
        _definition(
            family,
            experiment,
            scenario,
            method,
            reference,
            ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.benign_false_alarm_rate_noninferiority_margin,
        ),
    )


def _external_verification_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY
    experiment = EXTERNAL_VERIFICATION_NECESSITY_NAME
    method = SourceExclusionMethod.FULL_FEDSIRA.value
    reference = BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value
    conditions = (
        PluralityCondition.HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0.value,
        PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
        ExternalVerificationCondition.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER.value,
    )
    return tuple(
        _definition(
            family,
            experiment,
            condition,
            method,
            reference,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.malicious_admission_reduction_minimum,
        )
        for condition in conditions
    ) + tuple(
        _definition(
            family,
            experiment,
            condition,
            method,
            reference,
            ComparisonMetric.WORST_DOMAIN_TARGET_F1,
            ComparisonOrientation.HIGHER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.worst_domain_target_f1_gain_minimum,
        )
        for condition in conditions
    )


def _primary_baseline_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.PRIMARY_BASELINE_SUPERIORITY
    experiment = PRIMARY_CONFIRMATORY_EVALUATION_NAME
    method = CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value
    comparators = (
        BaselineIdentity.FEDAVG_REFERENCE.value,
        BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value,
        BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN.value,
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
        BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE.value,
        BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION.value,
        BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER.value,
        BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN.value,
        BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE.value,
        BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION.value,
        BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value,
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value,
    )
    definitions: list[ComparisonDefinition] = []
    for comparator in comparators:
        for scenario in PRIMARY_SCENARIOS:
            definitions.extend(
                (
                    _definition(
                        family,
                        experiment,
                        scenario,
                        method,
                        comparator,
                        ComparisonMetric.TARGET_F1,
                        ComparisonOrientation.HIGHER_IS_BETTER,
                        ComparisonTestKind.SUPERIORITY,
                        material_threshold=materiality.target_f1_gain_minimum,
                    ),
                    _definition(
                        family,
                        experiment,
                        scenario,
                        method,
                        comparator,
                        ComparisonMetric.LEGITIMATE_ADMISSION,
                        ComparisonOrientation.HIGHER_IS_BETTER,
                        ComparisonTestKind.NON_INFERIORITY,
                        margin=materiality.legitimate_admission_noninferiority_margin,
                    ),
                    _definition(
                        family,
                        experiment,
                        scenario,
                        method,
                        comparator,
                        ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        ComparisonTestKind.NON_INFERIORITY,
                        margin=materiality.supported_macro_f1_noninferiority_margin,
                    ),
                    _definition(
                        family,
                        experiment,
                        scenario,
                        method,
                        comparator,
                        ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        ComparisonTestKind.NON_INFERIORITY,
                        margin=materiality.benign_false_alarm_rate_noninferiority_margin,
                    ),
                    _definition(
                        family,
                        experiment,
                        scenario,
                        method,
                        comparator,
                        ComparisonMetric.MALICIOUS_ADMISSION,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        ComparisonTestKind.SUPERIORITY,
                        material_threshold=materiality.malicious_admission_reduction_minimum,
                    ),
                    _definition(
                        family,
                        experiment,
                        scenario,
                        method,
                        comparator,
                        ComparisonMetric.ATTACK_SUCCESS_RATE,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        ComparisonTestKind.SUPERIORITY,
                        material_threshold=materiality.source_exclusion_asr_reduction_minimum,
                    ),
                )
            )
    return tuple(definitions)


def _reproducer_robustness_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.REPRODUCER_ROBUSTNESS
    experiment = COMPROMISED_REPRODUCER_ROBUSTNESS_NAME
    method = CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value
    comparators = (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value,
    )
    conditions = (
        ReproducerCondition.ONE_SOURCE_COPY.value,
        ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR.value,
        ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR.value,
        ReproducerCondition.TWO_SOURCE_COPIES.value,
        ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS.value,
        ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS.value,
    )
    definitions: list[ComparisonDefinition] = []
    for comparator in comparators:
        for condition in conditions:
            definitions.extend(
                (
                    _definition(
                        family,
                        experiment,
                        condition,
                        method,
                        comparator,
                        ComparisonMetric.MALICIOUS_ADMISSION,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        ComparisonTestKind.SUPERIORITY,
                        material_threshold=materiality.malicious_admission_reduction_minimum,
                    ),
                    _definition(
                        family,
                        experiment,
                        condition,
                        method,
                        comparator,
                        ComparisonMetric.TARGET_F1,
                        ComparisonOrientation.HIGHER_IS_BETTER,
                        ComparisonTestKind.SUPERIORITY,
                        material_threshold=materiality.target_f1_gain_minimum,
                    ),
                    _definition(
                        family,
                        experiment,
                        condition,
                        method,
                        comparator,
                        ComparisonMetric.ATTACK_SUCCESS_RATE,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        ComparisonTestKind.SUPERIORITY,
                        material_threshold=materiality.source_exclusion_asr_reduction_minimum,
                    ),
                )
            )
    for comparator in comparators:
        definitions.extend(
            (
                _definition(
                    family,
                    experiment,
                    ReproducerCondition.CLEAN.value,
                    method,
                    comparator,
                    ComparisonMetric.LEGITIMATE_ADMISSION,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    ComparisonTestKind.NON_INFERIORITY,
                    margin=materiality.legitimate_admission_noninferiority_margin,
                ),
                _definition(
                    family,
                    experiment,
                    ReproducerCondition.CLEAN.value,
                    method,
                    comparator,
                    ComparisonMetric.TARGET_F1,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    ComparisonTestKind.NON_INFERIORITY,
                    margin=materiality.supported_macro_f1_noninferiority_margin,
                ),
            )
        )
    return tuple(definitions)


def _verifier_robustness_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.VERIFIER_ROBUSTNESS
    experiment = COMPROMISED_VERIFIER_ROBUSTNESS_NAME
    return (
        _definition(
            family,
            experiment,
            VerifierCondition.ONE_FALSE_POSITIVE.value,
            VerifierCondition.ONE_FALSE_POSITIVE.value,
            VerifierCondition.ALL_HONEST.value,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.malicious_admission_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            VerifierCondition.TWO_FALSE_POSITIVES.value,
            VerifierCondition.TWO_FALSE_POSITIVES.value,
            VerifierCondition.ALL_HONEST.value,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=materiality.malicious_admission_reduction_minimum,
        ),
        _definition(
            family,
            experiment,
            VerifierCondition.ONE_FALSE_NEGATIVE.value,
            VerifierCondition.ONE_FALSE_NEGATIVE.value,
            VerifierCondition.ALL_HONEST.value,
            ComparisonMetric.LEGITIMATE_ADMISSION,
            ComparisonOrientation.HIGHER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.legitimate_admission_noninferiority_margin,
        ),
        _definition(
            family,
            experiment,
            VerifierCondition.TWO_FALSE_NEGATIVES.value,
            VerifierCondition.TWO_FALSE_NEGATIVES.value,
            VerifierCondition.ALL_HONEST.value,
            ComparisonMetric.LEGITIMATE_ADMISSION,
            ComparisonOrientation.HIGHER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.legitimate_admission_noninferiority_margin,
        ),
    )


def _ablation_comparisons(
    materiality: MaterialityConfig,
    capability_granularity_minimum: CapabilityCertificationRate,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.MECHANISM_ABLATION
    experiment = MECHANISM_ABLATION_NAME
    scenario = ExperimentClass.ABLATION.value
    variants = (
        (
            AblationVariant.NO_PROPOSAL_SCREEN.value,
            ComparisonMetric.REPRODUCTION_ATTEMPTS,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.RAW_TARGET_F1_SCREEN_ONLY.value,
            ComparisonMetric.FALSE_LAUNCH,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.NO_MATCHED_CONTROL.value,
            ComparisonMetric.FALSE_LAUNCH,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW.value,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK.value,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.ONE_INDEPENDENT_REPRODUCTION.value,
            ComparisonMetric.WORST_DOMAIN_TARGET_F1,
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
        (
            AblationVariant.MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION.value,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.SAME_CONTEXT_VERIFICATION_ONLY.value,
            ComparisonMetric.LEGITIMATE_ADMISSION,
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
        (
            AblationVariant.NO_ORIGIN_EXCLUSION.value,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION.value,
            ComparisonMetric.LEGITIMATE_ADMISSION,
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
        (
            AblationVariant.CANDIDATE_FREE_REPRODUCTION.value,
            ComparisonMetric.POST_EVIDENCE_OVERHEAD,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.DIRECT_KRUM_OF_RETRAINS.value,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.GENERIC_THREE_ROW_THRESHOLD.value,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.RANDOM_COMMITTEE_PROFILE.value,
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.NO_FINAL_SYNTHESIS_GATE.value,
            ComparisonMetric.WORST_DOMAIN_TARGET_F1,
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
        (
            AblationVariant.BYZANTINE_REPRODUCER_COPIES_SOURCE.value,
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.CAPABILITY_CONTRACT_GRANULARITY.value,
            ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
    )

    def ablation_threshold(metric: ComparisonMetric) -> MaterialThreshold:
        thresholds = {
            ComparisonMetric.ATTACK_SUCCESS_RATE: materiality.source_exclusion_asr_reduction_minimum,
            ComparisonMetric.MALICIOUS_ADMISSION: materiality.malicious_admission_reduction_minimum,
            ComparisonMetric.WORST_DOMAIN_TARGET_F1: materiality.worst_domain_target_f1_gain_minimum,
            ComparisonMetric.FALSE_LAUNCH: materiality.false_launch_reduction_minimum,
            ComparisonMetric.REPRODUCTION_ATTEMPTS: materiality.reproduction_attempt_relative_reduction_minimum,
            ComparisonMetric.POST_EVIDENCE_OVERHEAD: materiality.post_evidence_overhead_relative_reduction_minimum,
            ComparisonMetric.LEGITIMATE_ADMISSION: materiality.legitimate_admission_noninferiority_margin,
            ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE: capability_granularity_minimum,
        }
        return thresholds.get(metric, materiality.target_f1_gain_minimum)

    return tuple(
        _definition(
            family,
            experiment,
            scenario,
            variant,
            SourceExclusionMethod.FULL_FEDSIRA.value,
            metric,
            orientation,
            ComparisonTestKind.SUPERIORITY,
            material_threshold=ablation_threshold(metric),
        )
        for variant, metric, orientation in variants
    )


def _heterogeneity_boundary_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY
    definitions: list[ComparisonDefinition] = []
    for regime in (
        HeterogeneityRegime.QUANTITY_SKEW.value,
        HeterogeneityRegime.FEATURE_SHIFT_0_5.value,
        HeterogeneityRegime.FEATURE_SHIFT_1_0.value,
    ):
        definitions.extend(
            (
                _definition(
                    family,
                    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
                    regime,
                    regime,
                    HeterogeneityRegime.NATURAL.value,
                    ComparisonMetric.LEGITIMATE_ADMISSION,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    ComparisonTestKind.SUPERIORITY,
                ),
                _definition(
                    family,
                    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
                    regime,
                    regime,
                    HeterogeneityRegime.NATURAL.value,
                    ComparisonMetric.WORST_DOMAIN_TARGET_F1,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    ComparisonTestKind.SUPERIORITY,
                ),
            )
        )
    for mixture in (
        RootCauseMixture.BALANCED_50_50.value,
        RootCauseMixture.A_DOMINANT_80_20.value,
    ):
        definitions.append(
            _definition(
                family,
                CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
                mixture,
                CapabilityContractScope.BROAD_TARGET_ONLY.value,
                CoreMethodIdentity.ZERO_REFERENCE.value,
                ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
                ComparisonOrientation.HIGHER_IS_BETTER,
                ComparisonTestKind.SUPERIORITY,
                material_threshold=materiality.malicious_admission_reduction_minimum,
            )
        )
    return tuple(definitions)


def _secondary_generalization_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.SECONDARY_GENERALIZATION
    experiment = SECONDARY_DATASET_GENERALIZATION_NAME
    method = CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value
    comparators = (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
    )
    scenarios = (
        SecondaryScenario.LEGITIMATE_BACKDOOR_MALWARE_CAPABILITY.value,
        SecondaryScenario.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
    )
    definitions: list[ComparisonDefinition] = []
    for comparator in comparators:
        for scenario in scenarios:
            definitions.extend(
                (
                    _definition(
                        family,
                        experiment,
                        scenario,
                        method,
                        comparator,
                        ComparisonMetric.TARGET_F1,
                        ComparisonOrientation.HIGHER_IS_BETTER,
                        ComparisonTestKind.NON_INFERIORITY,
                        margin=materiality.supported_macro_f1_noninferiority_margin,
                    ),
                    _definition(
                        family,
                        experiment,
                        scenario,
                        method,
                        comparator,
                        ComparisonMetric.MALICIOUS_ADMISSION,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        ComparisonTestKind.NON_INFERIORITY,
                        margin=materiality.legitimate_admission_noninferiority_margin,
                    ),
                )
            )
    return tuple(definitions)


def build_comparison_registry(
    materiality: MaterialityConfig,
    capability_granularity_minimum: CapabilityCertificationRate,
) -> tuple[ComparisonDefinition, ...]:
    return (
        *_proposal_screen_comparisons(materiality),
        *_plurality_comparisons(materiality),
        *_source_exclusion_comparisons(materiality),
        *_external_verification_comparisons(materiality),
        *_primary_baseline_comparisons(materiality),
        *_reproducer_robustness_comparisons(materiality),
        *_verifier_robustness_comparisons(materiality),
        *_ablation_comparisons(materiality, capability_granularity_minimum),
        *_heterogeneity_boundary_comparisons(materiality),
        *_secondary_generalization_comparisons(materiality),
    )
