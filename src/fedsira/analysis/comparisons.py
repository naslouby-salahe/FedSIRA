from __future__ import annotations

import math
from enum import StrEnum

from fedsira.analysis.statistics import (
    exact_sign_flip_non_inferiority_p_value,
    exact_sign_flip_two_sided_p_value,
    holm_adjusted_p_values,
)
from fedsira.baselines.registry import BaselineIdentity
from fedsira.config.schema import BootstrapConfig, MultiplicityConfig, ScientificConfig
from fedsira.domain.enums import CoreMethodIdentity, DatasetId, RootCauseMixture
from fedsira.domain.records import (
    ComparisonMargin,
    ComparisonName,
    CompleteSeedCount,
    ConfidenceIntervalBound,
    EffectSize,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MaterialityDecision,
    MaterialThreshold,
    MethodName,
    MetricDifference,
    PairedDifference,
    PValue,
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
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    AblationVariant,
    CapabilityContractGranularity,
    ClaimFamily,
    EpistemicFailureType,
    ExternalVerificationCondition,
    HeterogeneityRegime,
    OpeningMode,
    PluralityCondition,
    PrimaryScenario,
    ProposalEpisode,
    ReproducerCondition,
    SecondaryScenario,
    SourceExclusionMethod,
    VerifierCondition,
    VerifierProfile,
    ablation_scenario_for_variant,
    epistemic_strength_tokens,
)


class ComparisonTestKind(StrEnum):
    SUPERIORITY = "superiority"
    NON_INFERIORITY = "non-inferiority"


class ComparisonOrientation(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class ComparisonEffectScale(StrEnum):
    ABSOLUTE = "absolute"
    RELATIVE_REFERENCE_REDUCTION = "relative-reference-reduction"


class ComparisonReferenceKind(StrEnum):
    SCIENTIFIC_CELL = "scientific-cell"
    ZERO = "zero"


class MaterialityDirection(StrEnum):
    BENEFIT_AT_LEAST = "benefit-at-least"
    DETERIORATION_AT_LEAST = "deterioration-at-least"


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


class PairingKey(FrozenDomainModel):
    dataset: DatasetId
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    master_seed: MasterSeed

    @property
    def pairing_identity(self) -> ComparisonName:
        return "|".join(
            (
                self.dataset.value,
                self.experiment,
                self.scientific_scenario,
                str(self.master_seed),
            )
        )


class ComparisonDefinition(FrozenDomainModel):
    comparison_name: ComparisonName
    family: ClaimFamily
    experiment: ExperimentName
    scientific_scenario: ScenarioName
    method: MethodName
    reference_experiment: ExperimentName
    reference_scenario: ScenarioName
    reference_method: MethodName
    reference_kind: ComparisonReferenceKind
    metric: ComparisonMetric
    orientation: ComparisonOrientation
    test_kind: ComparisonTestKind
    effect_scale: ComparisonEffectScale = ComparisonEffectScale.ABSOLUTE
    materiality_direction: MaterialityDirection = MaterialityDirection.BENEFIT_AT_LEAST
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


class ComparisonTemplate(FrozenDomainModel):
    metric: ComparisonMetric
    orientation: ComparisonOrientation
    test_kind: ComparisonTestKind
    effect_scale: ComparisonEffectScale = ComparisonEffectScale.ABSOLUTE
    materiality_direction: MaterialityDirection = MaterialityDirection.BENEFIT_AT_LEAST
    margin: ComparisonMargin | None = None
    material_threshold: MaterialThreshold | None = None


def _effect_size(values: tuple[PairedDifference, ...]) -> EffectSize | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    deviation = math.sqrt(variance)
    if deviation == 0.0:
        if mean > 0:
            return math.inf
        if mean < 0:
            return -math.inf
        return 0.0
    return mean / deviation


def evaluate_comparison(
    definition: ComparisonDefinition,
    paired_differences: tuple[PairedDifference, ...],
    bootstrap_config: BootstrapConfig,
    analysis_seed: MasterSeed,
) -> ComparisonResult:
    count = len(paired_differences)
    if count == 0:
        return ComparisonResult(
            definition=definition,
            paired_differences=(),
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
    mean = sum(paired_differences) / count
    ordered = sorted(paired_differences)
    middle = count // 2
    median = ordered[middle] if count % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    interval = bootstrap_percentile_confidence_interval(
        paired_differences,
        bootstrap_config,
        analysis_seed,
    )
    if definition.test_kind is ComparisonTestKind.SUPERIORITY:
        raw_p_value = exact_sign_flip_two_sided_p_value(paired_differences)
    else:
        if definition.margin is None:
            raise ValueError(
                f"non-inferiority comparison {definition.comparison_name} requires a margin"
            )
        raw_p_value = exact_sign_flip_non_inferiority_p_value(
            paired_differences,
            definition.margin,
        )
    return ComparisonResult(
        definition=definition,
        paired_differences=paired_differences,
        complete_seed_count=count,
        mean_paired_difference=mean,
        median_paired_difference=median,
        paired_standardized_effect=_effect_size(paired_differences),
        raw_p_value=raw_p_value,
        adjusted_p_value=raw_p_value,
        confidence_interval=interval,
        materiality_passes=None,
        comparison_state=ComparisonState.PENDING,
    )


def _materiality_passes(
    definition: ComparisonDefinition,
    effect: MetricDifference | None,
) -> MaterialityDecision | None:
    threshold = definition.material_threshold
    if threshold is None:
        return None
    if effect is None:
        return False
    if definition.materiality_direction is MaterialityDirection.DETERIORATION_AT_LEAST:
        return effect <= -threshold
    return effect >= threshold


def _adjusted_p_value(
    comparison_name: ComparisonName,
    adjusted_values: tuple[tuple[ComparisonName, PValue], ...],
) -> PValue:
    for name, adjusted_value in adjusted_values:
        if name == comparison_name:
            return adjusted_value
    raise KeyError(f"missing Holm-adjusted p-value for {comparison_name}")


def _adjusted_result(
    result: ComparisonResult,
    adjusted_p_value: PValue,
    multiplicity_config: MultiplicityConfig,
) -> ComparisonResult:
    if result.raw_p_value is None:
        return ComparisonResult(
            definition=result.definition,
            paired_differences=result.paired_differences,
            complete_seed_count=result.complete_seed_count,
            mean_paired_difference=result.mean_paired_difference,
            median_paired_difference=result.median_paired_difference,
            paired_standardized_effect=result.paired_standardized_effect,
            raw_p_value=None,
            adjusted_p_value=adjusted_p_value,
            confidence_interval=result.confidence_interval,
            materiality_passes=result.materiality_passes,
            comparison_state=result.comparison_state,
        )
    materiality_passes = _materiality_passes(
        result.definition,
        result.mean_paired_difference,
    )
    passes = (
        adjusted_p_value < multiplicity_config.family_wise_alpha and materiality_passes is not False
    )
    return ComparisonResult(
        definition=result.definition,
        paired_differences=result.paired_differences,
        complete_seed_count=result.complete_seed_count,
        mean_paired_difference=result.mean_paired_difference,
        median_paired_difference=result.median_paired_difference,
        paired_standardized_effect=result.paired_standardized_effect,
        raw_p_value=result.raw_p_value,
        adjusted_p_value=adjusted_p_value,
        confidence_interval=result.confidence_interval,
        materiality_passes=materiality_passes,
        comparison_state=(ComparisonState.PASSED if passes else ComparisonState.FAILED),
    )


def apply_holm_adjustment(
    family_result: ComparisonFamilyResult,
    multiplicity_config: MultiplicityConfig,
) -> ComparisonFamilyResult:
    raw_values = tuple(
        (
            result.definition.comparison_name,
            result.raw_p_value if result.raw_p_value is not None else 1.0,
        )
        for result in family_result.comparisons
    )
    adjusted_values = holm_adjusted_p_values(raw_values)
    return ComparisonFamilyResult(
        family=family_result.family,
        comparisons=tuple(
            _adjusted_result(
                result,
                _adjusted_p_value(result.definition.comparison_name, adjusted_values),
                multiplicity_config,
            )
            for result in family_result.comparisons
        ),
    )


def build_comparison_name(
    family: ClaimFamily,
    experiment: ExperimentName,
    scenario: ScenarioName,
    method: MethodName,
    reference: MethodName,
    metric: ComparisonMetric,
    test_kind: ComparisonTestKind,
) -> ComparisonName:
    return (
        f"{family.value}|{experiment}|{scenario}|{method}__vs__{reference}|"
        f"{metric.value}|{test_kind.value}"
    )


def _reference_label(
    method: MethodName,
    reference_method: MethodName,
    reference_scenario: ScenarioName,
    reference_kind: ComparisonReferenceKind,
) -> MethodName:
    if reference_kind is ComparisonReferenceKind.ZERO:
        return CoreMethodIdentity.ZERO_REFERENCE.value
    if method == reference_method:
        return reference_scenario
    return reference_method


def _definition(
    family: ClaimFamily,
    experiment: ExperimentName,
    scenario: ScenarioName,
    method: MethodName,
    reference_method: MethodName,
    template: ComparisonTemplate,
    *,
    reference_experiment: ExperimentName | None = None,
    reference_scenario: ScenarioName | None = None,
    reference_kind: ComparisonReferenceKind = ComparisonReferenceKind.SCIENTIFIC_CELL,
) -> ComparisonDefinition:
    resolved_reference_experiment = reference_experiment or experiment
    resolved_reference_scenario = reference_scenario or scenario
    reference_label = _reference_label(
        method,
        reference_method,
        resolved_reference_scenario,
        reference_kind,
    )
    return ComparisonDefinition(
        comparison_name=build_comparison_name(
            family,
            experiment,
            scenario,
            method,
            reference_label,
            template.metric,
            template.test_kind,
        ),
        family=family,
        experiment=experiment,
        scientific_scenario=scenario,
        method=method,
        reference_experiment=resolved_reference_experiment,
        reference_scenario=resolved_reference_scenario,
        reference_method=reference_method,
        reference_kind=reference_kind,
        metric=template.metric,
        orientation=template.orientation,
        test_kind=template.test_kind,
        effect_scale=template.effect_scale,
        materiality_direction=template.materiality_direction,
        margin=template.margin,
        material_threshold=template.material_threshold,
    )


def _superiority(
    metric: ComparisonMetric,
    orientation: ComparisonOrientation,
    threshold: MaterialThreshold | None = None,
    *,
    effect_scale: ComparisonEffectScale = ComparisonEffectScale.ABSOLUTE,
    materiality_direction: MaterialityDirection = MaterialityDirection.BENEFIT_AT_LEAST,
) -> ComparisonTemplate:
    return ComparisonTemplate(
        metric=metric,
        orientation=orientation,
        test_kind=ComparisonTestKind.SUPERIORITY,
        effect_scale=effect_scale,
        materiality_direction=materiality_direction,
        material_threshold=threshold,
    )


def _non_inferiority(
    metric: ComparisonMetric,
    orientation: ComparisonOrientation,
    margin: ComparisonMargin,
) -> ComparisonTemplate:
    return ComparisonTemplate(
        metric=metric,
        orientation=orientation,
        test_kind=ComparisonTestKind.NON_INFERIORITY,
        margin=margin,
    )


def _matrix(
    family: ClaimFamily,
    experiment: ExperimentName,
    scenarios: tuple[ScenarioName, ...],
    method: MethodName,
    references: tuple[MethodName, ...],
    templates: tuple[ComparisonTemplate, ...],
) -> tuple[ComparisonDefinition, ...]:
    return tuple(
        _definition(
            family,
            experiment,
            scenario,
            method,
            reference,
            template,
        )
        for reference in references
        for scenario in scenarios
        for template in templates
    )


PRIMARY_COMPARATORS: tuple[MethodName, ...] = tuple(
    baseline.value
    for baseline in (
        BaselineIdentity.FEDAVG_REFERENCE,
        BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION,
        BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN,
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
        BaselineIdentity.MULTIPLE_MODEL_CERTIFIED_ENSEMBLE,
        BaselineIdentity.INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION,
        BaselineIdentity.UPDATE_RECONSTRUCTION_FILTER,
        BaselineIdentity.DENSITY_CLUSTER_TRIMMED_MEAN,
        BaselineIdentity.SECURE_CONTINUAL_ASSESSMENT_REFERENCE,
        BaselineIdentity.RECOVERY_AFTER_SOURCE_ADMISSION,
        BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE,
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
    )
)

REPRODUCER_COMPARATORS: tuple[MethodName, ...] = tuple(
    baseline.value
    for baseline in (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
    )
)


def _proposal_screen_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    materiality = config.metrics_and_statistics.materiality
    family = ClaimFamily.PROPOSAL_SCREEN_NECESSITY
    experiment = PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME
    method = OpeningMode.PROPOSAL_ASSISTED.value
    reference = OpeningMode.CANDIDATE_FREE.value
    definitions: list[ComparisonDefinition] = []
    for scenario in (
        ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value,
        ProposalEpisode.IRRELEVANT_SOURCE_IMPROVEMENT.value,
    ):
        definitions.append(
            _definition(
                family,
                experiment,
                scenario,
                method,
                reference,
                _superiority(
                    ComparisonMetric.FALSE_LAUNCH,
                    ComparisonOrientation.LOWER_IS_BETTER,
                    materiality.false_launch_reduction_minimum,
                ),
            )
        )
    for scenario in ProposalEpisode:
        definitions.extend(
            (
                _definition(
                    family,
                    experiment,
                    scenario.value,
                    method,
                    reference,
                    _superiority(
                        ComparisonMetric.REPRODUCTION_ATTEMPTS,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        materiality.reproduction_attempt_relative_reduction_minimum,
                        effect_scale=ComparisonEffectScale.RELATIVE_REFERENCE_REDUCTION,
                    ),
                ),
                _definition(
                    family,
                    experiment,
                    scenario.value,
                    method,
                    reference,
                    _superiority(
                        ComparisonMetric.POST_EVIDENCE_OVERHEAD,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        materiality.post_evidence_overhead_relative_reduction_minimum,
                        effect_scale=ComparisonEffectScale.RELATIVE_REFERENCE_REDUCTION,
                    ),
                ),
            )
        )
    definitions.extend(
        (
            _definition(
                family,
                experiment,
                ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,
                method,
                reference,
                _non_inferiority(
                    ComparisonMetric.LEGITIMATE_ADMISSION,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    materiality.legitimate_admission_noninferiority_margin,
                ),
            ),
            _definition(
                family,
                experiment,
                ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
                method,
                reference,
                _non_inferiority(
                    ComparisonMetric.MALICIOUS_ADMISSION,
                    ComparisonOrientation.LOWER_IS_BETTER,
                    materiality.proposal_malicious_admission_worsening_maximum,
                ),
            ),
        )
    )
    return tuple(definitions)


def _plurality_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    materiality = config.metrics_and_statistics.materiality
    return _matrix(
        ClaimFamily.PLURALITY_NECESSITY,
        SINGLE_REPRODUCTION_NECESSITY_NAME,
        (
            PluralityCondition.HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0.value,
            PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
        ),
        CoreMethodIdentity.FULL_PLURALITY_PATH.value,
        (BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,),
        (
            _superiority(
                ComparisonMetric.MALICIOUS_ADMISSION,
                ComparisonOrientation.LOWER_IS_BETTER,
                materiality.malicious_admission_reduction_minimum,
            ),
            _superiority(
                ComparisonMetric.WORST_DOMAIN_TARGET_F1,
                ComparisonOrientation.HIGHER_IS_BETTER,
                materiality.worst_domain_target_f1_gain_minimum,
            ),
        ),
    )


def _source_exclusion_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    materiality = config.metrics_and_statistics.materiality
    return (
        _definition(
            ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM,
            SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
            SourceExclusionMethod.FULL_FEDSIRA.value,
            BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value,
            _superiority(
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                ComparisonOrientation.LOWER_IS_BETTER,
                materiality.source_exclusion_asr_reduction_minimum,
            ),
        ),
    )


def _external_verification_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    materiality = config.metrics_and_statistics.materiality
    return _matrix(
        ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY,
        EXTERNAL_VERIFICATION_NECESSITY_NAME,
        (
            ExternalVerificationCondition.HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0.value,
            ExternalVerificationCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
            ExternalVerificationCondition.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER.value,
        ),
        SourceExclusionMethod.FULL_FEDSIRA.value,
        (BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,),
        (
            _superiority(
                ComparisonMetric.MALICIOUS_ADMISSION,
                ComparisonOrientation.LOWER_IS_BETTER,
                materiality.malicious_admission_reduction_minimum,
            ),
            _superiority(
                ComparisonMetric.WORST_DOMAIN_TARGET_F1,
                ComparisonOrientation.HIGHER_IS_BETTER,
                materiality.worst_domain_target_f1_gain_minimum,
            ),
        ),
    )


def _primary_templates(
    config: ScientificConfig,
    scenario: PrimaryScenario,
) -> tuple[ComparisonTemplate, ...]:
    materiality = config.metrics_and_statistics.materiality
    templates: list[ComparisonTemplate] = [
        _superiority(
            ComparisonMetric.TARGET_F1,
            ComparisonOrientation.HIGHER_IS_BETTER,
            materiality.target_f1_gain_minimum,
        ),
        _non_inferiority(
            ComparisonMetric.LEGITIMATE_ADMISSION,
            ComparisonOrientation.HIGHER_IS_BETTER,
            materiality.legitimate_admission_noninferiority_margin,
        ),
        _non_inferiority(
            ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
            ComparisonOrientation.LOWER_IS_BETTER,
            materiality.supported_macro_f1_noninferiority_margin,
        ),
        _non_inferiority(
            ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
            ComparisonOrientation.LOWER_IS_BETTER,
            materiality.benign_false_alarm_rate_noninferiority_margin,
        ),
    ]
    if scenario is not PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY:
        templates.extend(
            (
                _superiority(
                    ComparisonMetric.MALICIOUS_ADMISSION,
                    ComparisonOrientation.LOWER_IS_BETTER,
                    materiality.malicious_admission_reduction_minimum,
                ),
                _superiority(
                    ComparisonMetric.ATTACK_SUCCESS_RATE,
                    ComparisonOrientation.LOWER_IS_BETTER,
                    materiality.source_exclusion_asr_reduction_minimum,
                ),
            )
        )
    return tuple(templates)


def _primary_baseline_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    return tuple(
        _definition(
            ClaimFamily.PRIMARY_BASELINE_SUPERIORITY,
            PRIMARY_CONFIRMATORY_EVALUATION_NAME,
            scenario.value,
            CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
            comparator,
            template,
        )
        for comparator in PRIMARY_COMPARATORS
        for scenario in PrimaryScenario
        for template in _primary_templates(config, scenario)
    )


def _reproducer_attack_templates(
    config: ScientificConfig,
) -> tuple[ComparisonTemplate, ...]:
    materiality = config.metrics_and_statistics.materiality
    return (
        _superiority(
            ComparisonMetric.MALICIOUS_ADMISSION,
            ComparisonOrientation.LOWER_IS_BETTER,
            materiality.malicious_admission_reduction_minimum,
        ),
        _superiority(
            ComparisonMetric.TARGET_F1,
            ComparisonOrientation.HIGHER_IS_BETTER,
            materiality.target_f1_gain_minimum,
        ),
        _superiority(
            ComparisonMetric.ATTACK_SUCCESS_RATE,
            ComparisonOrientation.LOWER_IS_BETTER,
            materiality.source_exclusion_asr_reduction_minimum,
        ),
    )


def _reproducer_robustness_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    materiality = config.metrics_and_statistics.materiality
    definitions: list[ComparisonDefinition] = []
    for condition in ReproducerCondition:
        if condition is ReproducerCondition.CLEAN:
            templates = (
                _non_inferiority(
                    ComparisonMetric.LEGITIMATE_ADMISSION,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    materiality.legitimate_admission_noninferiority_margin,
                ),
                _non_inferiority(
                    ComparisonMetric.TARGET_F1,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    materiality.target_f1_noninferiority_margin,
                ),
            )
        else:
            templates = _reproducer_attack_templates(config)
        definitions.extend(
            _matrix(
                ClaimFamily.REPRODUCER_ROBUSTNESS,
                COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
                (condition.value,),
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                REPRODUCER_COMPARATORS,
                templates,
            )
        )
    return tuple(definitions)


def _verifier_robustness_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    materiality = config.metrics_and_statistics.materiality
    definitions: list[ComparisonDefinition] = []
    for profile in VerifierProfile:
        for condition in (
            VerifierCondition.ONE_FALSE_POSITIVE,
            VerifierCondition.TWO_FALSE_POSITIVES,
        ):
            definitions.append(
                _definition(
                    ClaimFamily.VERIFIER_ROBUSTNESS,
                    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
                    condition.value,
                    profile.value,
                    profile.value,
                    _superiority(
                        ComparisonMetric.MALICIOUS_ADMISSION,
                        ComparisonOrientation.LOWER_IS_BETTER,
                        materiality.malicious_admission_reduction_minimum,
                        materiality_direction=MaterialityDirection.DETERIORATION_AT_LEAST,
                    ),
                    reference_scenario=VerifierCondition.ALL_HONEST.value,
                )
            )
        for condition in (
            VerifierCondition.ONE_FALSE_NEGATIVE,
            VerifierCondition.TWO_FALSE_NEGATIVES,
        ):
            definitions.append(
                _definition(
                    ClaimFamily.VERIFIER_ROBUSTNESS,
                    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
                    condition.value,
                    profile.value,
                    profile.value,
                    _non_inferiority(
                        ComparisonMetric.LEGITIMATE_ADMISSION,
                        ComparisonOrientation.HIGHER_IS_BETTER,
                        materiality.legitimate_admission_noninferiority_margin,
                    ),
                    reference_scenario=VerifierCondition.ALL_HONEST.value,
                )
            )
    return tuple(definitions)


def _ablation_metric(
    variant: AblationVariant,
) -> tuple[ComparisonMetric, ComparisonOrientation]:
    if variant is AblationVariant.NO_PROPOSAL_SCREEN:
        return ComparisonMetric.REPRODUCTION_ATTEMPTS, ComparisonOrientation.LOWER_IS_BETTER
    if variant in (
        AblationVariant.RAW_TARGET_F1_SCREEN_ONLY,
        AblationVariant.NO_MATCHED_CONTROL,
    ):
        return ComparisonMetric.FALSE_LAUNCH, ComparisonOrientation.LOWER_IS_BETTER
    if variant in (
        AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW,
        AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK,
        AblationVariant.NO_ORIGIN_EXCLUSION,
        AblationVariant.BYZANTINE_REPRODUCER_COPIES_SOURCE,
    ):
        return ComparisonMetric.ATTACK_SUCCESS_RATE, ComparisonOrientation.LOWER_IS_BETTER
    if variant in (
        AblationVariant.ONE_INDEPENDENT_REPRODUCTION,
        AblationVariant.NO_FINAL_SYNTHESIS_GATE,
    ):
        return ComparisonMetric.WORST_DOMAIN_TARGET_F1, ComparisonOrientation.HIGHER_IS_BETTER
    if variant in (
        AblationVariant.MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION,
        AblationVariant.DIRECT_KRUM_OF_RETRAINS,
        AblationVariant.GENERIC_THREE_ROW_THRESHOLD,
        AblationVariant.RANDOM_COMMITTEE_PROFILE,
    ):
        return ComparisonMetric.MALICIOUS_ADMISSION, ComparisonOrientation.LOWER_IS_BETTER
    if variant in (
        AblationVariant.SAME_CONTEXT_VERIFICATION_ONLY,
        AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION,
    ):
        return ComparisonMetric.LEGITIMATE_ADMISSION, ComparisonOrientation.HIGHER_IS_BETTER
    if variant is AblationVariant.CANDIDATE_FREE_REPRODUCTION:
        return ComparisonMetric.POST_EVIDENCE_OVERHEAD, ComparisonOrientation.LOWER_IS_BETTER
    if variant is AblationVariant.CAPABILITY_CONTRACT_GRANULARITY:
        return (
            ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
            ComparisonOrientation.LOWER_IS_BETTER,
        )
    raise ValueError(f"ablation variant {variant} has no claim-bearing metric")


def _ablation_threshold(
    config: ScientificConfig,
    variant: AblationVariant,
    metric: ComparisonMetric,
) -> MaterialThreshold:
    materiality = config.metrics_and_statistics.materiality
    if metric is ComparisonMetric.ATTACK_SUCCESS_RATE:
        return materiality.source_exclusion_asr_reduction_minimum
    if metric is ComparisonMetric.MALICIOUS_ADMISSION:
        return materiality.malicious_admission_reduction_minimum
    if metric is ComparisonMetric.WORST_DOMAIN_TARGET_F1:
        return materiality.worst_domain_target_f1_gain_minimum
    if metric is ComparisonMetric.FALSE_LAUNCH:
        return materiality.false_launch_reduction_minimum
    if metric is ComparisonMetric.REPRODUCTION_ATTEMPTS:
        return materiality.reproduction_attempt_relative_reduction_minimum
    if metric is ComparisonMetric.POST_EVIDENCE_OVERHEAD:
        return materiality.post_evidence_overhead_relative_reduction_minimum
    if metric is ComparisonMetric.LEGITIMATE_ADMISSION:
        return materiality.legitimate_admission_noninferiority_margin
    if variant is AblationVariant.CAPABILITY_CONTRACT_GRANULARITY:
        granularity_thresholds = config.claim_support_thresholds.capability_granularity_boundary
        return granularity_thresholds.false_same_capability_certification_rate_minimum
    raise ValueError(f"no material threshold for ablation metric {metric}")


def _ablation_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    definitions: list[ComparisonDefinition] = []
    for variant in AblationVariant:
        if variant is AblationVariant.FULL_FEDSIRA:
            continue
        metric, orientation = _ablation_metric(variant)
        effect_scale = (
            ComparisonEffectScale.RELATIVE_REFERENCE_REDUCTION
            if metric
            in (
                ComparisonMetric.REPRODUCTION_ATTEMPTS,
                ComparisonMetric.POST_EVIDENCE_OVERHEAD,
            )
            else ComparisonEffectScale.ABSOLUTE
        )
        definitions.append(
            _definition(
                ClaimFamily.MECHANISM_ABLATION,
                MECHANISM_ABLATION_NAME,
                ablation_scenario_for_variant(variant),
                variant.value,
                AblationVariant.FULL_FEDSIRA.value,
                _superiority(
                    metric,
                    orientation,
                    _ablation_threshold(config, variant, metric),
                    effect_scale=effect_scale,
                    materiality_direction=MaterialityDirection.DETERIORATION_AT_LEAST,
                ),
            )
        )
    return tuple(definitions)


def _shared_epistemic_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    clean_materiality = config.attacks_and_boundaries.clean_oracle_materiality
    templates = (
        _superiority(
            ComparisonMetric.TARGET_F1,
            ComparisonOrientation.HIGHER_IS_BETTER,
            clean_materiality.target_f1_decrease,
            materiality_direction=MaterialityDirection.DETERIORATION_AT_LEAST,
        ),
        _superiority(
            ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
            ComparisonOrientation.LOWER_IS_BETTER,
            clean_materiality.supported_macro_f1_drop,
            materiality_direction=MaterialityDirection.DETERIORATION_AT_LEAST,
        ),
        _superiority(
            ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
            ComparisonOrientation.LOWER_IS_BETTER,
            clean_materiality.benign_false_alarm_rate_increase,
            materiality_direction=MaterialityDirection.DETERIORATION_AT_LEAST,
        ),
    )
    return tuple(
        _definition(
            ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
            SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            f"{failure_type.value}|{strength}",
            CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
            CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
            template,
            reference_experiment=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
            reference_scenario=PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
        )
        for failure_type in EpistemicFailureType
        for strength in epistemic_strength_tokens(failure_type)
        for template in templates
    )


def _capability_boundary_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    granularity_thresholds = config.claim_support_thresholds.capability_granularity_boundary
    threshold = granularity_thresholds.false_same_capability_certification_rate_minimum
    return tuple(
        _definition(
            ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
            CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            mixture.value,
            CapabilityContractGranularity.BROAD_TARGET_ONLY.value,
            CoreMethodIdentity.ZERO_REFERENCE.value,
            _superiority(
                ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
                ComparisonOrientation.HIGHER_IS_BETTER,
                threshold,
            ),
            reference_kind=ComparisonReferenceKind.ZERO,
        )
        for mixture in RootCauseMixture
    )


def _heterogeneity_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    boundary = config.claim_support_thresholds.heterogeneity_boundary
    methods = (
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
        BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value,
    )
    definitions: list[ComparisonDefinition] = []
    for method in methods:
        for regime in HeterogeneityRegime:
            if regime is HeterogeneityRegime.NATURAL:
                continue
            definitions.extend(
                (
                    _definition(
                        ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
                        HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
                        regime.value,
                        method,
                        method,
                        _non_inferiority(
                            ComparisonMetric.LEGITIMATE_ADMISSION,
                            ComparisonOrientation.HIGHER_IS_BETTER,
                            boundary.legitimate_admission_change_from_natural_maximum,
                        ),
                        reference_scenario=HeterogeneityRegime.NATURAL.value,
                    ),
                    _definition(
                        ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
                        HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
                        regime.value,
                        method,
                        method,
                        _non_inferiority(
                            ComparisonMetric.WORST_DOMAIN_TARGET_F1,
                            ComparisonOrientation.HIGHER_IS_BETTER,
                            boundary.worst_domain_target_f1_change_from_natural_maximum,
                        ),
                        reference_scenario=HeterogeneityRegime.NATURAL.value,
                    ),
                )
            )
    return tuple(definitions)


def _secondary_generalization_comparisons(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    boundary = config.claim_support_thresholds.secondary_generalization
    references = (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
        BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
    )
    definitions = list(
        _matrix(
            ClaimFamily.SECONDARY_GENERALIZATION,
            SECONDARY_DATASET_GENERALIZATION_NAME,
            tuple(scenario.value for scenario in SecondaryScenario),
            CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
            references,
            (
                _non_inferiority(
                    ComparisonMetric.TARGET_F1,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    boundary.target_f1_noninferiority_margin,
                ),
            ),
        )
    )
    definitions.extend(
        _matrix(
            ClaimFamily.SECONDARY_GENERALIZATION,
            SECONDARY_DATASET_GENERALIZATION_NAME,
            (SecondaryScenario.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,),
            CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
            references,
            (
                _non_inferiority(
                    ComparisonMetric.MALICIOUS_ADMISSION,
                    ComparisonOrientation.LOWER_IS_BETTER,
                    boundary.malicious_admission_worsening_maximum,
                ),
            ),
        )
    )
    return tuple(definitions)


def build_comparison_registry(
    config: ScientificConfig,
) -> tuple[ComparisonDefinition, ...]:
    return (
        *_proposal_screen_comparisons(config),
        *_plurality_comparisons(config),
        *_source_exclusion_comparisons(config),
        *_external_verification_comparisons(config),
        *_primary_baseline_comparisons(config),
        *_reproducer_robustness_comparisons(config),
        *_verifier_robustness_comparisons(config),
        *_ablation_comparisons(config),
        *_shared_epistemic_comparisons(config),
        *_capability_boundary_comparisons(config),
        *_heterogeneity_comparisons(config),
        *_secondary_generalization_comparisons(config),
    )
