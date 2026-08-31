from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from fedsira.baselines.registry import (
    BASELINE_VALIDATION_FIXTURE_MAP,
    BaselineIdentity,
    BaselineValidationFixture,
)
from fedsira.domain.enums import CoreMethodIdentity, DatasetId, RootCauseMixture
from fedsira.domain.types import (
    ConditionName,
    ExperimentName,
    FrozenDomainModel,
    MethodName,
    ScientificCellCount,
    SeedCount,
)
from fedsira.experiments.scenarios.evidence_arrival import EvidenceArrivalSchedule
from fedsira.runtime.state import current_application_context


class ClaimFamily(StrEnum):
    PROPOSAL_SCREEN_NECESSITY = "proposal-screen necessity"
    PLURALITY_NECESSITY = "plurality necessity"
    SOURCE_EXCLUSION_CENTRAL_CLAIM = "source-exclusion central claim"
    EXTERNAL_VERIFICATION_NECESSITY = "external reproduction verification necessity"
    PRIMARY_BASELINE_SUPERIORITY = "primary baseline superiority"
    REPRODUCER_ROBUSTNESS = "reproducer robustness"
    VERIFIER_ROBUSTNESS = "verifier robustness"
    MECHANISM_ABLATION = "mechanism ablation"
    HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY = (
        "heterogeneity/failure-boundary secondary comparisons"
    )
    SECONDARY_GENERALIZATION = "secondary generalization"


class ExperimentClass(StrEnum):
    VALIDATION = "Validation"
    EXPLORATORY = "Exploratory"
    CONFIRMATORY = "Confirmatory"
    ABLATION = "Ablation"
    ROBUSTNESS = "Robustness"
    FAILURE_BOUNDARY = "Failure Boundary"
    DIAGNOSTIC = "Diagnostic"
    GENERALIZATION = "Generalization"


class OpeningMode(StrEnum):
    PROPOSAL_ASSISTED = "Proposal-Assisted"
    CANDIDATE_FREE = "Candidate-Free"


class ProposalEpisode(StrEnum):
    LEGITIMATE_TARGET_CAPABILITY = "Legitimate Target Capability"
    GENERIC_HARD_SUPPORTED_EXAMPLES = "Generic Hard Supported Examples"
    IRRELEVANT_SOURCE_IMPROVEMENT = "Irrelevant Source Improvement"
    USEFUL_BACKDOORED_SOURCE_5_PERCENT = "Useful Backdoored Source — 5%"


class PluralityCondition(StrEnum):
    LEGITIMATE_TRANSFERABLE_CAPABILITY = "Legitimate Transferable Capability"
    HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0 = "Honest Site-Specific Feature Shift — 1.0"
    ONE_BYZANTINE_SOURCE_COPY_REPRODUCER = "One Byzantine Source-Copy Reproducer"


class ExternalVerificationCondition(StrEnum):
    LEGITIMATE_TRANSFERABLE_CAPABILITY = "Legitimate Transferable Capability"
    HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0 = "Honest Site-Specific Feature Shift — 1.0"
    ONE_BYZANTINE_SOURCE_COPY_REPRODUCER = "One Byzantine Source-Copy Reproducer"
    ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER = "One Verifier-Aware Backdoor Reproducer"


class PrimaryScenario(StrEnum):
    LEGITIMATE_UNSUPPORTED_CAPABILITY = "Legitimate Unsupported Capability"
    USEFUL_BACKDOORED_SOURCE_5_PERCENT = "Useful Backdoored Source — 5%"
    ONE_BYZANTINE_POST_REFERENCE_PARTICIPANT = "One Byzantine Post-Reference Participant"


class SourceExclusionMethod(StrEnum):
    FULL_FEDSIRA = "Full FedSIRA"
    CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION = "Client Review with Direct Source Admission"
    CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN = "Client Review then One Independent Retrain"
    ONE_INDEPENDENT_RETRAIN = "One Independent Retrain"
    SOURCE_UPDATE_SANITIZATION_REFERENCE = "Source-Update Sanitization Reference"
    RECOVERY_AFTER_SOURCE_ADMISSION = "Recovery after Source Admission"


class AblationVariant(StrEnum):
    FULL_FEDSIRA = "Full FedSIRA"
    NO_PROPOSAL_SCREEN = "No Proposal Screen"
    RAW_TARGET_F1_SCREEN_ONLY = "Raw Target-F1 Screen Only"
    NO_MATCHED_CONTROL = "No Matched Control"
    SOURCE_RELEASE_AFTER_PEER_REVIEW = "Source Release after Peer Review"
    SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK = "Source Release after Full External Check"
    ONE_INDEPENDENT_REPRODUCTION = "One Independent Reproduction"
    MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION = (
        "Multiple Reproductions without Cross-Verification"
    )
    SAME_CONTEXT_VERIFICATION_ONLY = "Same-Context Verification Only"
    NO_ORIGIN_EXCLUSION = "No Origin Exclusion"
    PARAMETER_SIMILARITY_CERTIFICATION = "Parameter-Similarity Certification"
    CANDIDATE_FREE_REPRODUCTION = "Candidate-Free Reproduction"
    DIRECT_KRUM_OF_RETRAINS = "Direct Krum of Retrains"
    GENERIC_THREE_ROW_THRESHOLD = "Generic Three-Row Threshold"
    RANDOM_COMMITTEE_PROFILE = "Random Committee Profile"
    NO_FINAL_SYNTHESIS_GATE = "No Final Synthesis Gate"
    BYZANTINE_REPRODUCER_COPIES_SOURCE = "Byzantine Reproducer Copies Source"
    CAPABILITY_CONTRACT_GRANULARITY = "Capability-Contract Granularity"


class AblationScenario(StrEnum):
    USEFUL_BACKDOORED_SOURCE_5_PERCENT = "Useful Backdoored Source — 5%"
    MIXED_LEGITIMATE_IRRELEVANT_PROPOSAL = "Mixed Legitimate/Irrelevant Proposal Episode"
    GENERIC_HARD_SUPPORTED_EXAMPLES = "Generic Hard Supported Examples"
    HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0 = "Honest Site-Specific Feature Shift — 1.0"
    ONE_MALICIOUS_REPRODUCER = "One Malicious Reproducer"
    NATURAL = "Natural"
    FEATURE_SHIFT_1_0 = "Feature Shift ±1.0"
    LEGITIMATE_TARGET_CAPABILITY = "Legitimate Target Capability"
    ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER = "One Verifier-Aware Backdoor Reproducer"
    ONE_COMPROMISED_VERIFIER = "One Compromised Verifier"
    UNDER_SPECIFICATION_FIXTURE = "Under-Specification Fixture"


class ReproducerCondition(StrEnum):
    CLEAN = "CLEAN"
    ONE_SOURCE_COPY = "One Source Copy"
    ONE_MODEL_REPLACEMENT_BACKDOOR = "One Model-Replacement Backdoor"
    ONE_VERIFIER_AWARE_BACKDOOR = "One Verifier-Aware Backdoor"
    TWO_SOURCE_COPIES = "Two Source Copies"
    TWO_MODEL_REPLACEMENT_BACKDOORS = "Two Model-Replacement Backdoors"
    TWO_VERIFIER_AWARE_BACKDOORS = "Two Verifier-Aware Backdoors"


class VerifierProfile(StrEnum):
    DETERMINISTIC_BOUND = "Deterministic Bound"
    RANDOM_COMMITTEE_DIAGNOSTIC = "Random-Committee Diagnostic"


class VerifierCondition(StrEnum):
    ALL_HONEST = "All Honest"
    ONE_FALSE_POSITIVE = "One False Positive"
    TWO_FALSE_POSITIVES = "Two False Positives"
    ONE_FALSE_NEGATIVE = "One False Negative"
    TWO_FALSE_NEGATIVES = "Two False Negatives"


class BoundCondition(StrEnum):
    ONE_BYZANTINE_REPRODUCER_WITHIN_BOUND = "One Byzantine Reproducer — Within Bound"
    TWO_BYZANTINE_REPRODUCERS_ABOVE_BOUND = "Two Byzantine Reproducers — Above Bound"
    ONE_BYZANTINE_VERIFIER_WITHIN_BOUND = "One Byzantine Verifier — Within Bound"
    TWO_BYZANTINE_VERIFIERS_ABOVE_BOUND = "Two Byzantine Verifiers — Above Bound"


class EpistemicFailureType(StrEnum):
    SHARED_LABEL_ERROR = "shared label/threat-intelligence error"
    SHARED_SPURIOUS_FEATURE = "shared spurious feature"
    ATTACKER_INDUCED_COMMON_CONTEXT = "attacker-induced common context"


class CapabilityContractGranularity(StrEnum):
    BROAD_TARGET_ONLY = "Broad Target Only"
    ROOT_CAUSE_A_SCOPED = "Root-Cause A Scoped"
    ROOT_CAUSE_B_SCOPED = "Root-Cause B Scoped"


class HeterogeneityRegime(StrEnum):
    NATURAL = "Natural"
    QUANTITY_SKEW = "Quantity Skew"
    FEATURE_SHIFT_0_5 = "Feature Shift ±0.5"
    FEATURE_SHIFT_1_0 = "Feature Shift ±1.0"


class SecondaryScenario(StrEnum):
    LEGITIMATE_BACKDOOR_MALWARE_CAPABILITY = "Legitimate Backdoor-Malware Capability"
    ONE_BYZANTINE_SOURCE_COPY_REPRODUCER = "One Byzantine Source-Copy Reproducer"


class ExperimentDefinition(FrozenDomainModel):
    name: ExperimentName
    experiment_class: ExperimentClass
    methods: tuple[MethodName, ...]
    conditions: tuple[ConditionName, ...]
    seed_count: SeedCount
    nominal_cell_count: ScientificCellCount
    claim_family: ClaimFamily | None
    prerequisites: tuple[ExperimentName, ...]
    dataset: DatasetId = DatasetId.N_BAIOT


DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME: ExperimentName = "Data and Domain Evidence Validation"
PROTOCOL_INVARIANT_VALIDATION_NAME: ExperimentName = "Protocol Invariant Validation"
BASELINE_IMPLEMENTATION_VALIDATION_NAME: ExperimentName = "Baseline Implementation Validation"
PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME: ExperimentName = "Proposal-Assisted Opening Necessity"
SINGLE_REPRODUCTION_NECESSITY_NAME: ExperimentName = "Single-Reproduction Necessity"
SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME: ExperimentName = "Source-Artifact Exclusion Necessity"
EXTERNAL_VERIFICATION_NECESSITY_NAME: ExperimentName = "External Verification Necessity"
PRIMARY_CONFIRMATORY_EVALUATION_NAME: ExperimentName = "Primary Confirmatory Evaluation"
MECHANISM_ABLATION_NAME: ExperimentName = "Mechanism Ablation"
COMPROMISED_REPRODUCER_ROBUSTNESS_NAME: ExperimentName = "Compromised-Reproducer Robustness"
COMPROMISED_VERIFIER_ROBUSTNESS_NAME: ExperimentName = "Compromised-Verifier Robustness"
BYZANTINE_BOUND_VIOLATION_NAME: ExperimentName = "Byzantine-Bound Violation"
EVIDENCE_SCARCITY_AND_DORMANCY_NAME: ExperimentName = "Evidence Scarcity and Dormancy"
SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME: ExperimentName = "Shared Epistemic-Failure Boundary"
CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME: ExperimentName = (
    "Capability Under-Specification Boundary"
)
HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME: ExperimentName = "Heterogeneous-Reproduction Boundary"
ADMISSION_DELAY_DECOMPOSITION_NAME: ExperimentName = "Admission-Delay Decomposition"
EFFICIENCY_MEASUREMENT_NAME: ExperimentName = "Efficiency Measurement"
SECONDARY_DATASET_GENERALIZATION_NAME: ExperimentName = "Secondary-Dataset Generalization"

COLLAPSE_EXPERIMENT_NAMES: tuple[ExperimentName, ...] = (
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
)

POST_CORE_EXPERIMENT_NAMES: tuple[ExperimentName, ...] = (
    PRIMARY_CONFIRMATORY_EVALUATION_NAME,
    MECHANISM_ABLATION_NAME,
    COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
    COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
    BYZANTINE_BOUND_VIOLATION_NAME,
    EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
    SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
    HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
    ADMISSION_DELAY_DECOMPOSITION_NAME,
    EFFICIENCY_MEASUREMENT_NAME,
    SECONDARY_DATASET_GENERALIZATION_NAME,
)

_SMOKE_SEED_COUNT: SeedCount = 1


def _confirmatory_seed_count() -> SeedCount:
    seeds = current_application_context().scientific_config.seeds_and_determinism
    return seeds.confirmatory_seed_count


def _unique(values: Iterable[ConditionName]) -> tuple[ConditionName, ...]:
    result: list[ConditionName] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def epistemic_strength_tokens(failure_type: EpistemicFailureType) -> tuple[ConditionName, ...]:
    if failure_type is EpistemicFailureType.SHARED_LABEL_ERROR:
        return ("0.05", "0.10", "0.20")
    return ("0.25", "0.50", "1.00")


def ablation_scenario_for_variant(variant: AblationVariant) -> AblationScenario:
    if variant is AblationVariant.NO_PROPOSAL_SCREEN:
        return AblationScenario.MIXED_LEGITIMATE_IRRELEVANT_PROPOSAL
    if variant in (
        AblationVariant.RAW_TARGET_F1_SCREEN_ONLY,
        AblationVariant.NO_MATCHED_CONTROL,
    ):
        return AblationScenario.GENERIC_HARD_SUPPORTED_EXAMPLES
    if variant in (
        AblationVariant.FULL_FEDSIRA,
        AblationVariant.SOURCE_RELEASE_AFTER_PEER_REVIEW,
        AblationVariant.SOURCE_RELEASE_AFTER_FULL_EXTERNAL_CHECK,
        AblationVariant.NO_ORIGIN_EXCLUSION,
        AblationVariant.BYZANTINE_REPRODUCER_COPIES_SOURCE,
    ):
        return AblationScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT
    if variant is AblationVariant.ONE_INDEPENDENT_REPRODUCTION:
        return AblationScenario.HONEST_SITE_SPECIFIC_FEATURE_SHIFT_1_0
    if variant in (
        AblationVariant.MULTIPLE_REPRODUCTIONS_WITHOUT_CROSS_VERIFICATION,
        AblationVariant.GENERIC_THREE_ROW_THRESHOLD,
    ):
        return AblationScenario.ONE_MALICIOUS_REPRODUCER
    if variant is AblationVariant.SAME_CONTEXT_VERIFICATION_ONLY:
        return AblationScenario.NATURAL
    if variant in (
        AblationVariant.PARAMETER_SIMILARITY_CERTIFICATION,
        AblationVariant.NO_FINAL_SYNTHESIS_GATE,
    ):
        return AblationScenario.FEATURE_SHIFT_1_0
    if variant is AblationVariant.CANDIDATE_FREE_REPRODUCTION:
        return AblationScenario.LEGITIMATE_TARGET_CAPABILITY
    if variant is AblationVariant.DIRECT_KRUM_OF_RETRAINS:
        return AblationScenario.ONE_VERIFIER_AWARE_BACKDOOR_REPRODUCER
    if variant is AblationVariant.RANDOM_COMMITTEE_PROFILE:
        return AblationScenario.ONE_COMPROMISED_VERIFIER
    if variant is AblationVariant.CAPABILITY_CONTRACT_GRANULARITY:
        return AblationScenario.UNDER_SPECIFICATION_FIXTURE
    raise ValueError(f"unmapped ablation variant {variant}")


_BASELINE_FIXTURE_BY_METHOD: tuple[tuple[MethodName, ConditionName], ...] = tuple(
    (identity.value, fixture.value)
    for identity, fixture in BASELINE_VALIDATION_FIXTURE_MAP
    if fixture
    in (
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
    )
)


def baseline_validation_fixture_for_method(method: MethodName) -> ConditionName:
    for registered_method, fixture in _BASELINE_FIXTURE_BY_METHOD:
        if registered_method == method:
            return fixture
    raise KeyError(f"no baseline validation fixture for {method!r}")


_BASELINE_METHODS = tuple(method for method, _fixture in _BASELINE_FIXTURE_BY_METHOD)
_BASELINE_FIXTURES = _unique(fixture for _method, fixture in _BASELINE_FIXTURE_BY_METHOD)
_ABLATION_SCENARIOS = _unique(ablation_scenario_for_variant(variant) for variant in AblationVariant)


def experiment_registry() -> tuple[ExperimentDefinition, ...]:
    confirmatory_seed_count = _confirmatory_seed_count()
    return (
        ExperimentDefinition(
            name=DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
            experiment_class=ExperimentClass.VALIDATION,
            methods=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
            conditions=("primary",),
            seed_count=_SMOKE_SEED_COUNT,
            nominal_cell_count=1,
            claim_family=None,
            prerequisites=(),
        ),
        ExperimentDefinition(
            name=PROTOCOL_INVARIANT_VALIDATION_NAME,
            experiment_class=ExperimentClass.VALIDATION,
            methods=(PROTOCOL_INVARIANT_VALIDATION_NAME,),
            conditions=("aggregate",),
            seed_count=_SMOKE_SEED_COUNT,
            nominal_cell_count=1,
            claim_family=None,
            prerequisites=(),
        ),
        ExperimentDefinition(
            name=BASELINE_IMPLEMENTATION_VALIDATION_NAME,
            experiment_class=ExperimentClass.VALIDATION,
            methods=_BASELINE_METHODS,
            conditions=_BASELINE_FIXTURES,
            seed_count=_SMOKE_SEED_COUNT,
            nominal_cell_count=17,
            claim_family=None,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
        ),
        ExperimentDefinition(
            name=PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
            experiment_class=ExperimentClass.EXPLORATORY,
            methods=tuple(mode.value for mode in OpeningMode),
            conditions=tuple(episode.value for episode in ProposalEpisode),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=80,
            claim_family=ClaimFamily.PROPOSAL_SCREEN_NECESSITY,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
        ),
        ExperimentDefinition(
            name=SINGLE_REPRODUCTION_NECESSITY_NAME,
            experiment_class=ExperimentClass.EXPLORATORY,
            methods=(
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                CoreMethodIdentity.FULL_PLURALITY_PATH.value,
            ),
            conditions=tuple(condition.value for condition in PluralityCondition),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=60,
            claim_family=ClaimFamily.PLURALITY_NECESSITY,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
        ),
        ExperimentDefinition(
            name=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            experiment_class=ExperimentClass.EXPLORATORY,
            methods=tuple(method.value for method in SourceExclusionMethod),
            conditions=(PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=60,
            claim_family=ClaimFamily.SOURCE_EXCLUSION_CENTRAL_CLAIM,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
        ),
        ExperimentDefinition(
            name=EXTERNAL_VERIFICATION_NECESSITY_NAME,
            experiment_class=ExperimentClass.EXPLORATORY,
            methods=(
                SourceExclusionMethod.FULL_FEDSIRA.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
            ),
            conditions=tuple(condition.value for condition in ExternalVerificationCondition),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=80,
            claim_family=ClaimFamily.EXTERNAL_VERIFICATION_NECESSITY,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
        ),
        ExperimentDefinition(
            name=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
            experiment_class=ExperimentClass.CONFIRMATORY,
            methods=(
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
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
            ),
            conditions=tuple(scenario.value for scenario in PrimaryScenario),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=420,
            claim_family=ClaimFamily.PRIMARY_BASELINE_SUPERIORITY,
            prerequisites=(PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,),
        ),
        ExperimentDefinition(
            name=MECHANISM_ABLATION_NAME,
            experiment_class=ExperimentClass.ABLATION,
            methods=tuple(variant.value for variant in AblationVariant),
            conditions=_ABLATION_SCENARIOS,
            seed_count=confirmatory_seed_count,
            nominal_cell_count=180,
            claim_family=ClaimFamily.MECHANISM_ABLATION,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
            experiment_class=ExperimentClass.ROBUSTNESS,
            methods=(
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
                BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value,
            ),
            conditions=tuple(condition.value for condition in ReproducerCondition),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=280,
            claim_family=ClaimFamily.REPRODUCER_ROBUSTNESS,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
            experiment_class=ExperimentClass.ROBUSTNESS,
            methods=tuple(profile.value for profile in VerifierProfile),
            conditions=tuple(condition.value for condition in VerifierCondition),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=100,
            claim_family=ClaimFamily.VERIFIER_ROBUSTNESS,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=BYZANTINE_BOUND_VIOLATION_NAME,
            experiment_class=ExperimentClass.FAILURE_BOUNDARY,
            methods=(
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
            ),
            conditions=tuple(condition.value for condition in BoundCondition),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=80,
            claim_family=None,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
            experiment_class=ExperimentClass.FAILURE_BOUNDARY,
            methods=(CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,),
            conditions=tuple(schedule.value for schedule in EvidenceArrivalSchedule),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=40,
            claim_family=None,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
            experiment_class=ExperimentClass.FAILURE_BOUNDARY,
            methods=(CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,),
            conditions=tuple(
                f"{failure_type.value}|{strength}"
                for failure_type in EpistemicFailureType
                for strength in epistemic_strength_tokens(failure_type)
            ),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=90,
            claim_family=ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            experiment_class=ExperimentClass.FAILURE_BOUNDARY,
            methods=tuple(granularity.value for granularity in CapabilityContractGranularity),
            conditions=tuple(mixture.value for mixture in RootCauseMixture),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=60,
            claim_family=ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
            experiment_class=ExperimentClass.ROBUSTNESS,
            methods=(
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
                BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value,
            ),
            conditions=tuple(regime.value for regime in HeterogeneityRegime),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=160,
            claim_family=ClaimFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=ADMISSION_DELAY_DECOMPOSITION_NAME,
            experiment_class=ExperimentClass.DIAGNOSTIC,
            methods=(
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
            ),
            conditions=tuple(schedule.value for schedule in EvidenceArrivalSchedule),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=120,
            claim_family=None,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=EFFICIENCY_MEASUREMENT_NAME,
            experiment_class=ExperimentClass.DIAGNOSTIC,
            methods=(
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
                BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value,
            ),
            conditions=("timed",),
            seed_count=3,
            nominal_cell_count=60,
            claim_family=None,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        ),
        ExperimentDefinition(
            name=SECONDARY_DATASET_GENERALIZATION_NAME,
            experiment_class=ExperimentClass.GENERALIZATION,
            methods=(
                CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,
                BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
                BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
                BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value,
                BaselineIdentity.FEDAVG_REFERENCE.value,
            ),
            conditions=tuple(scenario.value for scenario in SecondaryScenario),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=100,
            claim_family=ClaimFamily.SECONDARY_GENERALIZATION,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.CICIOT2023,
        ),
    )


def experiment_by_name(name: ExperimentName) -> ExperimentDefinition:
    for definition in experiment_registry():
        if definition.name == name:
            return definition
    raise KeyError(f"unknown experiment {name!r}")


def experiment_names() -> tuple[ExperimentName, ...]:
    return tuple(definition.name for definition in experiment_registry())
