from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from fedsira.baselines.registry import BaselineIdentity
from fedsira.config.schema import BootstrapConfig, MaterialityConfig, MultiplicityConfig
from fedsira.domain.enums import CapabilityContractScope
from fedsira.domain.records import CanonicalToken, MasterSeed, Probability
from fedsira.evaluation.aggregation import bootstrap_percentile_confidence_interval
from fedsira.evaluation.statistics import (
    exact_sign_flip_non_inferiority_p_value,
    exact_sign_flip_two_sided_p_value,
    holm_adjusted_p_values,
)
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


@dataclass(frozen=True)
class PairingKey:
    dataset: CanonicalToken
    experiment: CanonicalToken
    scientific_scenario: CanonicalToken
    master_seed: MasterSeed

    @property
    def canonical(self) -> CanonicalToken:
        return "|".join(
            (self.dataset, self.experiment, self.scientific_scenario, str(self.master_seed))
        )


class ComparisonTestKind(StrEnum):
    SUPERIORITY = "superiority"
    NON_INFERIORITY = "non-inferiority"


class ComparisonOrientation(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


@dataclass(frozen=True)
class ComparisonDefinition:
    canonical_name: CanonicalToken
    family: ClaimFamily
    method: CanonicalToken
    reference: CanonicalToken
    experiment: CanonicalToken
    scientific_scenario: CanonicalToken
    metric: CanonicalToken
    orientation: ComparisonOrientation
    test_kind: ComparisonTestKind
    margin: float | None = None
    material_threshold: float | None = None


@dataclass(frozen=True)
class ComparisonResult:
    definition: ComparisonDefinition
    paired_differences: tuple[float, ...]
    complete_seed_count: int
    mean_paired_difference: float | None
    median_paired_difference: float | None
    paired_standardized_effect: float | None
    raw_p_value: Probability | None
    adjusted_p_value: Probability | None
    confidence_interval: tuple[float, float] | None
    materiality_passes: bool | None
    comparison_state: CanonicalToken


@dataclass(frozen=True)
class ComparisonFamilyResult:
    family: ClaimFamily
    comparisons: tuple[ComparisonResult, ...]


def complete_paired_seeds(
    seed_metrics: Mapping[MasterSeed, Mapping[CanonicalToken, float | None]],
    method: CanonicalToken,
    reference: CanonicalToken,
    metric: CanonicalToken,
) -> tuple[MasterSeed, ...]:
    return tuple(
        master_seed
        for master_seed, values in sorted(seed_metrics.items())
        if values.get(method) is not None and values.get(reference) is not None
    )


def _signed_standard_deviation(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def _effect_size(differences: Sequence[float]) -> float | None:
    if len(differences) == 0:
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
    paired_differences: Sequence[float],
    multiplicity_config: MultiplicityConfig,
    bootstrap_config: BootstrapConfig,
    analysis_seed: MasterSeed,
) -> ComparisonResult:
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
            comparison_state="Undefined",
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
        comparison_state="Pending",
    )


def apply_holm_adjustment(
    family_result: ComparisonFamilyResult, multiplicity_config: MultiplicityConfig
) -> ComparisonFamilyResult:
    raw_values = tuple(
        (result.definition.canonical_name, result.raw_p_value)
        for result in family_result.comparisons
        if result.raw_p_value is not None
    )
    adjusted = holm_adjusted_p_values(raw_values)
    adjusted_by_name = dict(adjusted)
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
        comparison_state = "Passed" if (statistical_pass and materiality_pass) else "Failed"
        updated_comparisons.append(
            ComparisonResult(
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
                comparison_state=comparison_state,
            )
        )
    return ComparisonFamilyResult(
        family=family_result.family, comparisons=tuple(updated_comparisons)
    )


def comparison_canonical_name(
    family: ClaimFamily,
    experiment: CanonicalToken,
    scientific_scenario: CanonicalToken,
    method: CanonicalToken,
    reference: CanonicalToken,
    metric: CanonicalToken,
    test_kind: ComparisonTestKind,
) -> CanonicalToken:
    return (
        f"{family.value}|{experiment}|{scientific_scenario}|"
        f"{method}__vs__{reference}|{metric}|{test_kind.value}"
    )


def _definition(
    family: ClaimFamily,
    experiment: CanonicalToken,
    scientific_scenario: CanonicalToken,
    method: CanonicalToken,
    reference: CanonicalToken,
    metric: CanonicalToken,
    orientation: ComparisonOrientation,
    test_kind: ComparisonTestKind,
    margin: float | None = None,
    material_threshold: float | None = None,
) -> ComparisonDefinition:
    return ComparisonDefinition(
        canonical_name=comparison_canonical_name(
            family, experiment, scientific_scenario, method, reference, metric, test_kind
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


PRIMARY_SCENARIOS: tuple[CanonicalToken, ...] = (
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
            "false-launch",
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
            "false-launch",
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
            "reproduction-attempts",
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
            "reproduction-attempts",
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
            "reproduction-attempts",
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
            "reproduction-attempts",
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
            "post-evidence-overhead",
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
            "post-evidence-overhead",
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
            "post-evidence-overhead",
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
            "post-evidence-overhead",
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
            "legitimate-admission",
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
            "malicious-admission",
            ComparisonOrientation.LOWER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.supported_macro_f1_noninferiority_margin,
        ),
    )


def _plurality_comparisons(materiality: MaterialityConfig) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.PLURALITY_NECESSITY
    experiment = SINGLE_REPRODUCTION_NECESSITY_NAME
    method = "Full Plurality Path"
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
            "malicious-admission",
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
            "worst-domain-target-f1",
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
            "asr",
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
            "target-f1",
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
            "supported-macro-f1-harm",
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
            "benign-far-increase",
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
            "malicious-admission",
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
            "worst-domain-target-f1",
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
    method = "Resolved FedSIRA Core"
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
            definitions.append(
                _definition(
                    family,
                    experiment,
                    scenario,
                    method,
                    comparator,
                    "target-f1",
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    ComparisonTestKind.SUPERIORITY,
                    material_threshold=materiality.target_f1_gain_minimum,
                )
            )
            definitions.append(
                _definition(
                    family,
                    experiment,
                    scenario,
                    method,
                    comparator,
                    "legitimate-admission",
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    ComparisonTestKind.NON_INFERIORITY,
                    margin=materiality.legitimate_admission_noninferiority_margin,
                )
            )
            definitions.append(
                _definition(
                    family,
                    experiment,
                    scenario,
                    method,
                    comparator,
                    "supported-macro-f1-harm",
                    ComparisonOrientation.LOWER_IS_BETTER,
                    ComparisonTestKind.NON_INFERIORITY,
                    margin=materiality.supported_macro_f1_noninferiority_margin,
                )
            )
            definitions.append(
                _definition(
                    family,
                    experiment,
                    scenario,
                    method,
                    comparator,
                    "benign-far-increase",
                    ComparisonOrientation.LOWER_IS_BETTER,
                    ComparisonTestKind.NON_INFERIORITY,
                    margin=materiality.benign_false_alarm_rate_noninferiority_margin,
                )
            )
            definitions.append(
                _definition(
                    family,
                    experiment,
                    scenario,
                    method,
                    comparator,
                    "malicious-admission",
                    ComparisonOrientation.LOWER_IS_BETTER,
                    ComparisonTestKind.SUPERIORITY,
                    material_threshold=materiality.malicious_admission_reduction_minimum,
                )
            )
            definitions.append(
                _definition(
                    family,
                    experiment,
                    scenario,
                    method,
                    comparator,
                    "asr",
                    ComparisonOrientation.LOWER_IS_BETTER,
                    ComparisonTestKind.SUPERIORITY,
                    material_threshold=materiality.source_exclusion_asr_reduction_minimum,
                )
            )
    return tuple(definitions)


def _reproducer_robustness_comparisons(
    materiality: MaterialityConfig,
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.REPRODUCER_ROBUSTNESS
    experiment = COMPROMISED_REPRODUCER_ROBUSTNESS_NAME
    method = "Resolved FedSIRA Core"
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
            definitions.append(
                _definition(
                    family,
                    experiment,
                    condition,
                    method,
                    comparator,
                    "malicious-admission",
                    ComparisonOrientation.LOWER_IS_BETTER,
                    ComparisonTestKind.SUPERIORITY,
                    material_threshold=materiality.malicious_admission_reduction_minimum,
                )
            )
            definitions.append(
                _definition(
                    family,
                    experiment,
                    condition,
                    method,
                    comparator,
                    "target-f1",
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    ComparisonTestKind.SUPERIORITY,
                    material_threshold=materiality.target_f1_gain_minimum,
                )
            )
            definitions.append(
                _definition(
                    family,
                    experiment,
                    condition,
                    method,
                    comparator,
                    "asr",
                    ComparisonOrientation.LOWER_IS_BETTER,
                    ComparisonTestKind.SUPERIORITY,
                    material_threshold=materiality.source_exclusion_asr_reduction_minimum,
                )
            )
    for comparator in comparators:
        definitions.append(
            _definition(
                family,
                experiment,
                ReproducerCondition.CLEAN.value,
                method,
                comparator,
                "legitimate-admission",
                ComparisonOrientation.HIGHER_IS_BETTER,
                ComparisonTestKind.NON_INFERIORITY,
                margin=materiality.legitimate_admission_noninferiority_margin,
            )
        )
        definitions.append(
            _definition(
                family,
                experiment,
                ReproducerCondition.CLEAN.value,
                method,
                comparator,
                "target-f1",
                ComparisonOrientation.HIGHER_IS_BETTER,
                ComparisonTestKind.NON_INFERIORITY,
                margin=materiality.supported_macro_f1_noninferiority_margin,
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
            "malicious-admission",
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
            "malicious-admission",
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
            "legitimate-admission",
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
            "legitimate-admission",
            ComparisonOrientation.HIGHER_IS_BETTER,
            ComparisonTestKind.NON_INFERIORITY,
            margin=materiality.legitimate_admission_noninferiority_margin,
        ),
    )


def _ablation_comparisons(
    materiality: MaterialityConfig, capability_granularity_minimum: float
) -> tuple[ComparisonDefinition, ...]:
    family = ClaimFamily.MECHANISM_ABLATION
    experiment = MECHANISM_ABLATION_NAME
    scenario = ExperimentClass.ABLATION.value
    variants = (
        (
            AblationVariant.NO_PROPOSAL_SCREEN.value,
            "reproduction-attempts",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.RAW_TARGET_F1_SCREEN_ONLY.value,
            "false-launch",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.NO_MATCHED_CONTROL.value,
            "false-launch",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW.value,
            "asr",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK.value,
            "asr",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.ONE_INDEPENDENT_REPRODUCTION.value,
            "worst-domain-target-f1",
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
        (
            AblationVariant.MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION.value,
            "malicious-admission",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.SAME_CONTEXT_VERIFICATION_ONLY.value,
            "legitimate-admission",
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
        (AblationVariant.NO_ORIGIN_EXCLUSION.value, "asr", ComparisonOrientation.LOWER_IS_BETTER),
        (
            AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION.value,
            "legitimate-admission",
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
        (
            AblationVariant.CANDIDATE_FREE_REPRODUCTION.value,
            "post-evidence-overhead",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.DIRECT_KRUM_OF_RETRAINS.value,
            "malicious-admission",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.GENERIC_THREE_ROW_THRESHOLD.value,
            "malicious-admission",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.RANDOM_COMMITTEE_PROFILE.value,
            "malicious-admission",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.NO_FINAL_SYNTHESIS_GATE.value,
            "worst-domain-target-f1",
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
        (
            AblationVariant.BYZANTINE_REPRODUCER_COPIES_SOURCE.value,
            "asr",
            ComparisonOrientation.LOWER_IS_BETTER,
        ),
        (
            AblationVariant.CAPABILITY_CONTRACT_GRANULARITY.value,
            "false-same-capability-certification-rate",
            ComparisonOrientation.HIGHER_IS_BETTER,
        ),
    )

    def ablation_threshold(metric: CanonicalToken) -> float:
        if metric == "asr":
            return materiality.source_exclusion_asr_reduction_minimum
        if metric == "malicious-admission":
            return materiality.malicious_admission_reduction_minimum
        if metric == "worst-domain-target-f1":
            return materiality.worst_domain_target_f1_gain_minimum
        if metric == "false-launch":
            return materiality.false_launch_reduction_minimum
        if metric == "reproduction-attempts":
            return materiality.reproduction_attempt_relative_reduction_minimum
        if metric == "post-evidence-overhead":
            return materiality.post_evidence_overhead_relative_reduction_minimum
        if metric == "legitimate-admission":
            return materiality.legitimate_admission_noninferiority_margin
        if metric == "false-same-capability-certification-rate":
            return capability_granularity_minimum
        return materiality.target_f1_gain_minimum

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
        definitions.append(
            _definition(
                family,
                HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
                regime,
                regime,
                HeterogeneityRegime.NATURAL.value,
                "legitimate-admission",
                ComparisonOrientation.HIGHER_IS_BETTER,
                ComparisonTestKind.SUPERIORITY,
                material_threshold=None,
            )
        )
        definitions.append(
            _definition(
                family,
                HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
                regime,
                regime,
                HeterogeneityRegime.NATURAL.value,
                "worst-domain-target-f1",
                ComparisonOrientation.HIGHER_IS_BETTER,
                ComparisonTestKind.SUPERIORITY,
                material_threshold=None,
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
                "zero",
                "false-same-capability-certification-rate",
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
    method = "Resolved FedSIRA Core"
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
            definitions.append(
                _definition(
                    family,
                    experiment,
                    scenario,
                    method,
                    comparator,
                    "target-f1",
                    ComparisonOrientation.HIGHER_IS_BETTER,
                    ComparisonTestKind.NON_INFERIORITY,
                    margin=materiality.supported_macro_f1_noninferiority_margin,
                )
            )
            definitions.append(
                _definition(
                    family,
                    experiment,
                    scenario,
                    method,
                    comparator,
                    "malicious-admission",
                    ComparisonOrientation.LOWER_IS_BETTER,
                    ComparisonTestKind.NON_INFERIORITY,
                    margin=materiality.legitimate_admission_noninferiority_margin,
                )
            )
    return tuple(definitions)


def build_comparison_registry(
    materiality: MaterialityConfig,
    capability_granularity_minimum: float,
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
