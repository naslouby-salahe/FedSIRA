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


class ComparisonTemplate(FrozenDomainModel):
    metric: ComparisonMetric
    orientation: ComparisonOrientation
    test_kind: ComparisonTestKind
    margin: ComparisonMargin | None = None
    material_threshold: MaterialThreshold | None = None


def complete_paired_seeds(
    seed_metrics: Mapping[MasterSeed, Mapping[MethodName, MetricDifference | None]],
    method: MethodName,
    reference: MethodName,
    metric: ComparisonMetric,
) -> tuple[MasterSeed, ...]:
    del metric
    return tuple(
        seed
        for seed, values in sorted(seed_metrics.items())
        if values.get(method) is not None and values.get(reference) is not None
    )


def _effect_size(values: Sequence[PairedDifference]) -> EffectSize | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    if len(values) < 2:
        return None
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    deviation = math.sqrt(variance)
    if deviation == 0.0:
        return math.inf if mean > 0 else -math.inf if mean < 0 else 0.0
    return mean / deviation


def evaluate_comparison(
    definition: ComparisonDefinition,
    paired_differences: Sequence[PairedDifference],
    multiplicity_config: MultiplicityConfig,
    bootstrap_config: BootstrapConfig,
    analysis_seed: MasterSeed,
) -> ComparisonResult:
    del multiplicity_config
    differences = tuple(paired_differences)
    count = len(differences)
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
    mean = sum(differences) / count
    ordered = sorted(differences)
    middle = count // 2
    median = ordered[middle] if count % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    interval = bootstrap_percentile_confidence_interval(
        differences, bootstrap_config, analysis_seed
    )
    if definition.test_kind is ComparisonTestKind.SUPERIORITY:
        raw_p = exact_sign_flip_two_sided_p_value(differences)
    else:
        if definition.margin is None:
            raise ValueError(
                f"non-inferiority comparison {definition.comparison_name} requires a margin"
            )
        raw_p = exact_sign_flip_non_inferiority_p_value(differences, definition.margin)
    return ComparisonResult(
        definition=definition,
        paired_differences=differences,
        complete_seed_count=count,
        mean_paired_difference=mean,
        median_paired_difference=median,
        paired_standardized_effect=_effect_size(differences),
        raw_p_value=raw_p,
        adjusted_p_value=raw_p,
        confidence_interval=interval,
        materiality_passes=None,
        comparison_state=ComparisonState.PENDING,
    )


def apply_holm_adjustment(
    family_result: ComparisonFamilyResult,
    multiplicity_config: MultiplicityConfig,
) -> ComparisonFamilyResult:
    raw_values = tuple(
        (result.definition.comparison_name, result.raw_p_value)
        for result in family_result.comparisons
        if result.raw_p_value is not None
    )
    adjusted = dict(holm_adjusted_p_values(raw_values))
    results: list[ComparisonResult] = []
    for result in family_result.comparisons:
        p_value = adjusted.get(result.definition.comparison_name)
        if p_value is None:
            results.append(result)
            continue
        threshold = result.definition.material_threshold
        effect = result.mean_paired_difference
        materiality_passes = None if threshold is None or effect is None else abs(effect) >= threshold
        passed = p_value < multiplicity_config.family_wise_alpha and materiality_passes is not False
        results.append(
            result.model_copy(
                update={
                    "adjusted_p_value": p_value,
                    "materiality_passes": materiality_passes,
                    "comparison_state": ComparisonState.PASSED if passed else ComparisonState.FAILED,
                }
            )
        )
    return ComparisonFamilyResult(family=family_result.family, comparisons=tuple(results))


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


def _definition(
    family: ClaimFamily,
    experiment: ExperimentName,
    scenario: ScenarioName,
    method: MethodName,
    reference: MethodName,
    template: ComparisonTemplate,
) -> ComparisonDefinition:
    return ComparisonDefinition(
        comparison_name=build_comparison_name(
            family, experiment, scenario, method, reference, template.metric, template.test_kind
        ),
        family=family,
        method=method,
        reference=reference,
        experiment=experiment,
        scientific_scenario=scenario,
        metric=template.metric,
        orientation=template.orientation,
        test_kind=template.test_kind,
        margin=template.margin,
        material_threshold=template.material_threshold,
    )


def _superiority(
    metric: ComparisonMetric,
    orientation: ComparisonOrientation,
    threshold: MaterialThreshold | None = None,
) -> ComparisonTemplate:
    return ComparisonTemplate(
        metric=metric,
        orientation=orientation,
        test_kind=ComparisonTestKind.SUPERIORITY,
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
    scenarios: Sequence[ScenarioName],
    method: MethodName,
    references: Sequence[MethodName],
    templates: Sequence[ComparisonTemplate],
) -> tuple[ComparisonDefinition, ...]:
    return tuple(
        _definition(family, experiment, scenario, method, reference, template)
        for reference in references
        for scenario in scenarios
        for template in templates
    )


PRIMARY_SCENARIOS: tuple[ScenarioName, ...] = (
    PrimaryScenario.LEGITIMATE_UNSUPPORTED_CAPABILITY.value,
    PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
    PrimaryScenario.ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT.value,
)


def _proposal_screen_comparisons(materiality: MaterialityConfig) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.PROPOSAL_SCREEN_NECESSITY
    experiment = PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME
    method = OpeningMode.PROPOSAL_ASSISTED.value
    reference = OpeningMode.CANDIDATE_FREE.value
    false_launch = _superiority(
        ComparisonMetric.FALSE_LAUNCH,
        ComparisonOrientation.LOWER_IS_BETTER,
        materiality.false_launch_reduction_minimum,
    )
    attempts = _superiority(
        ComparisonMetric.REPRODUCTION_ATTEMPTS,
        ComparisonOrientation.LOWER_IS_BETTER,
        materiality.reproduction_attempt_relative_reduction_minimum,
    )
    overhead = _superiority(
        ComparisonMetric.POST_EVIDENCE_OVERHEAD,
        ComparisonOrientation.LOWER_IS_BETTER,
        materiality.post_evidence_overhead_relative_reduction_minimum,
    )
    definitions = [
        _definition(
            family,
            experiment,
            scenario,
            method,
            reference,
            false_launch,
        )
        for scenario in (
            ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value,
            ProposalEpisode.IRRELEVANT_SOURCE_IMPROVEMENT.value,
        )
    ]
    for template in (attempts, overhead):
        definitions.extend(
            _definition(family, experiment, scenario, method, reference, template)
            for scenario in (
                ProposalEpisode.LEGITIMATE_TARGET_CAPABILITY.value,
                ProposalEpisode.GENERIC_HARD_SUPPORTED_EXAMPLES.value,
                ProposalEpisode.IRRELEVANT_SOURCE_IMPROVEMENT.value,
                ProposalEpisode.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,
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
                    materiality.supported_macro_f1_noninferiority_margin,
                ),
            ),
        )
    )
    return tuple(definitions)


def _plurality_comparisons(materiality: MaterialityConfig) -> tuple[ComparisonDefinition, ...]:
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


def _source_exclusion_comparisons(materiality: MaterialityConfig) -> tuple[ComparisonDefinition, ...]:
    return _matrix(
        ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM,
        SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        (PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,),
        SourceExclusionMethod.FULL_FEDSIRA.value,
        (BaselineIdentity.SOURCE_UPDATE_SANITIZATION_REFERENCE.value,),
        (
            _superiority(
                ComparisonMetric.ATTACK_SUCCESS_RATE,
                ComparisonOrientation.LOWER_IS_BETTER,
                materiality.source_exclusion_asr_reduction_minimum,
            ),
            _non_inferiority(
                ComparisonMetric.TARGET_F1,
                ComparisonOrientation.HIGHER_IS_BETTER,
                materiality.supported_macro_f1_noninferiority_margin,
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
        ),
    )


def _external_verification_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    return _matrix(
        ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY,
        EXTERNAL_VERIFICATION_NECESSITY_NAME,
        (
            PluralityCondition.HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0.value,
            PluralityCondition.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
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


def _primary_baseline_comparisons(materiality: MaterialityConfig) -> tuple[ComparisonDefinition, ...]:
    comparators = tuple(
        item.value
        for item in (
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
    return _matrix(
        ClaimFamily.PRIMARY_BASELINE_SUPERIORITY,
        PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        PRIMARY_SCENARIOS,
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
        comparators,
        (
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
        ),
    )


def _reproducer_robustness_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    references = tuple(
        item.value
        for item in (
            BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
            BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM,
            BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE,
        )
    )
    adversarial = _matrix(
        ClaimFamily.REPRODUCER_ROBUSTNESS,
        COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
        tuple(
            item.value
            for item in (
                ReproducerCondition.ONE_SOURCE_COPY,
                ReproducerCondition.ONE_MODEL_REPLACEMENT_BACKDOOR,
                ReproducerCondition.ONE_VERIFIER_AWARE_BACKDOOR,
                ReproducerCondition.TWO_SOURCE_COPIES,
                ReproducerCondition.TWO_MODEL_REPLACEMENT_BACKDOORS,
                ReproducerCondition.TWO_VERIFIER_AWARE_BACKDOORS,
            )
        ),
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
        references,
        (
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
        ),
    )
    clean = _matrix(
        ClaimFamily.REPRODUCER_ROBUSTNESS,
        COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
        (ReproducerCondition.CLEAN.value,),
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
        references,
        (
            _non_inferiority(
                ComparisonMetric.LEGITIMATE_ADMISSION,
                ComparisonOrientation.HIGHER_IS_BETTER,
                materiality.legitimate_admission_noninferiority_margin,
            ),
            _non_inferiority(
                ComparisonMetric.TARGET_F1,
                ComparisonOrientation.HIGHER_IS_BETTER,
                materiality.supported_macro_f1_noninferiority_margin,
            ),
        ),
    )
    return (*adversarial, *clean)


def _verifier_robustness_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.VERIFIER_ROBUSTNESS
    experiment = COMPROMISED_VERIFIER_ROBUSTNESS_NAME
    cases = (
        (
            VerifierCondition.ONE_FALSE_POSITIVE,
            _superiority(
                ComparisonMetric.MALICIOUS_ADMISSION,
                ComparisonOrientation.LOWER_IS_BETTER,
                materiality.malicious_admission_reduction_minimum,
            ),
        ),
        (
            VerifierCondition.TWO_FALSE_POSITIVES,
            _superiority(
                ComparisonMetric.MALICIOUS_ADMISSION,
                ComparisonOrientation.LOWER_IS_BETTER,
                materiality.malicious_admission_reduction_minimum,
            ),
        ),
        (
            VerifierCondition.ONE_FALSE_NEGATIVE,
            _non_inferiority(
                ComparisonMetric.LEGITIMATE_ADMISSION,
                ComparisonOrientation.HIGHER_IS_BETTER,
                materiality.legitimate_admission_noninferiority_margin,
            ),
        ),
        (
            VerifierCondition.TWO_FALSE_NEGATIVES,
            _non_inferiority(
                ComparisonMetric.LEGITIMATE_ADMISSION,
                ComparisonOrientation.HIGHER_IS_BETTER,
                materiality.legitimate_admission_noninferiority_margin,
            ),
        ),
    )
    return tuple(
        _definition(
            family,
            experiment,
            condition.value,
            condition.value,
            VerifierCondition.ALL_HONEST.value,
            template,
        )
        for condition, template in cases
    )


def _ablation_comparisons(
    materiality: MaterialityConfig,
    capability_granularity_minimum: CapabilityCertificationRate,
) -> tuple[ComparisonDefinition, ...]:
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
    variants = (
        (AblationVariant.NO_PROPOSAL_SCREEN, ComparisonMetric.REPRODUCTION_ATTEMPTS, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.RAW_TARGET_F1_SCREEN_ONLY, ComparisonMetric.FALSE_LAUNCH, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.NO_MATCHED_CONTROL, ComparisonMetric.FALSE_LAUNCH, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW, ComparisonMetric.ATTACK_SUCCESS_RATE, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK, ComparisonMetric.ATTACK_SUCCESS_RATE, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.ONE_INDEPENDENT_REPRODUCTION, ComparisonMetric.WORST_DOMAIN_TARGET_F1, ComparisonOrientation.HIGHER_IS_BETTER),
        (AblationVariant.MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION, ComparisonMetric.MALICIOUS_ADMISSION, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.SAME_CONTEXT_VERIFICATION_ONLY, ComparisonMetric.LEGITIMATE_ADMISSION, ComparisonOrientation.HIGHER_IS_BETTER),
        (AblationVariant.NO_ORIGIN_EXCLUSION, ComparisonMetric.ATTACK_SUCCESS_RATE, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION, ComparisonMetric.LEGITIMATE_ADMISSION, ComparisonOrientation.HIGHER_IS_BETTER),
        (AblationVariant.CANDIDATE_FREE_REPRODUCTION, ComparisonMetric.POST_EVIDENCE_OVERHEAD, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.DIRECT_KRUM_OF_RETRAINS, ComparisonMetric.MALICIOUS_ADMISSION, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.GENERIC_THREE_ROW_THRESHOLD, ComparisonMetric.MALICIOUS_ADMISSION, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.RANDOM_COMMITTEE_PROFILE, ComparisonMetric.MALICIOUS_ADMISSION, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.NO_FINAL_SYNTHESIS_GATE, ComparisonMetric.WORST_DOMAIN_TARGET_F1, ComparisonOrientation.HIGHER_IS_BETTER),
        (AblationVariant.BYZANTINE_REPRODUCER_COPIES_SOURCE, ComparisonMetric.ATTACK_SUCCESS_RATE, ComparisonOrientation.LOWER_IS_BETTER),
        (AblationVariant.CAPABILITY_CONTRACT_GRANULARITY, ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE, ComparisonOrientation.HIGHER_IS_BETTER),
    )
    return tuple(
        _definition(
            ClaimFamily.MECHANISM_ABLATION,
            MECHANISM_ABLATION_NAME,
            ExperimentClass.ABLATION.value,
            variant.value,
            SourceExclusionMethod.FULL_FEDSIRA.value,
            _superiority(
                metric,
                orientation,
                thresholds.get(metric, materiality.target_f1_gain_minimum),
            ),
        )
        for variant, metric, orientation in variants
    )


def _heterogeneity_boundary_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    definitions: list[ComparisonDefinition] = []
    family = ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY
    for regime in (
        HeterogeneityRegime.QUANTITY_SKEW,
        HeterogeneityRegime.FEATURE_SHIFT_0_5,
        HeterogeneityRegime.FEATURE_SHIFT_1_0,
    ):
        for metric in (
            ComparisonMetric.LEGITIMATE_ADMISSION,
            ComparisonMetric.WORST_DOMAIN_TARGET_F1,
        ):
            definitions.append(
                _definition(
                    family,
                    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
                    regime.value,
                    regime.value,
                    HeterogeneityRegime.NATURAL.value,
                    _superiority(metric, ComparisonOrientation.HIGHER_IS_BETTER),
                )
            )
    for mixture in (RootCauseMixture.BALANCED_50_50, RootCauseMixture.A_DOMINANT_80_20):
        definitions.append(
            _definition(
                family,
                CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
                mixture.value,
                CapabilityContractScope.BROAD_TARGET_ONLY.value,
                CoreMethodIdentity.ZERO_REFERENCE.value,
                _superiority(
                    ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    materiality.malicious_admission_reduction_minimum,
                ),
            )
        )
    return tuple(definitions)


def _secondary_generalization_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    return _matrix(
        ClaimFamily.SECONDARY_GENERALIZATION,
        SECONDARY_DATASET_GENERALIZATION_NAME,
        (
            SecondaryScenario.LEGITIMATE_BACKDOOR_MALWARE_CAPABILITY.value,
            SecondaryScenario.ONE_BYZANTINE_SOURCE_COPY_REPRODUCER.value,
        ),
        CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
        (
            BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
            BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
        ),
        (
            _non_inferiority(
                ComparisonMetric.TARGET_F1,
                ComparisonOrientation.HIGHER_IS_BETTER,
                materiality.supported_macro_f1_noninferiority_margin,
            ),
            _non_inferiority(
                ComparisonMetric.MALICIOUS_ADMISSION,
                ComparisonOrientation.LOWER_IS_BETTER,
                materiality.legitimate_admission_noninferiority_margin,
            ),
        ),
    )


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
