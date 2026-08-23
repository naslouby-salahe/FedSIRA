from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fedsira.baselines.registry import (
    BASELINE_VALIDATION_FIXTURE_MAP,
    BaselineIdentity,
    BaselineValidationFixture,
)
from fedsira.boundaries.evidence_arrival import EvidenceArrivalSchedule
from fedsira.domain.enums import DatasetId
from fedsira.domain.records import CanonicalToken, NonNegativeInt, PositiveInt

ExperimentId = CanonicalToken


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


class RootCauseMixture(StrEnum):
    BALANCED_50_50 = "Balanced 50/50"
    A_DOMINANT_80_20 = "A-Dominant 80/20"


class HeterogeneityRegime(StrEnum):
    NATURAL = "Natural"
    QUANTITY_SKEW = "Quantity Skew"
    FEATURE_SHIFT_0_5 = "Feature Shift ±0.5"
    FEATURE_SHIFT_1_0 = "Feature Shift ±1.0"


class SecondaryScenario(StrEnum):
    LEGITIMATE_BACKDOOR_MALWARE_CAPABILITY = "Legitimate Backdoor-Malware Capability"
    ONE_BYZANTINE_SOURCE_COPY_REPRODUCER = "One Byzantine Source-Copy Reproducer"


@dataclass(frozen=True)
class ExperimentDefinition:
    name: ExperimentId
    experiment_class: ExperimentClass
    methods: tuple[CanonicalToken, ...]
    conditions: tuple[CanonicalToken, ...]
    seed_count: PositiveInt
    nominal_cell_count: NonNegativeInt
    claim_family: CanonicalToken | None
    prerequisites: tuple[CanonicalToken, ...]
    dataset: DatasetId = DatasetId.N_BAIOT


PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME = "Proposal-Assisted Opening Necessity"
SINGLE_REPRODUCTION_NECESSITY_NAME = "Single-Reproduction Necessity"
SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME = "Source-Artifact Exclusion Necessity"
EXTERNAL_VERIFICATION_NECESSITY_NAME = "External Verification Necessity"
PRIMARY_CONFIRMATORY_EVALUATION_NAME = "Primary Confirmatory Evaluation"
MECHANISM_ABLATION_NAME = "Mechanism Ablation"
COMPROMISED_REPRODUCER_ROBUSTNESS_NAME = "Compromised-Reproducer Robustness"
COMPROMISED_VERIFIER_ROBUSTNESS_NAME = "Compromised-Verifier Robustness"
BYZANTINE_BOUND_VIOLATION_NAME = "Byzantine-Bound Violation"
EVIDENCE_SCARCITY_AND_DORMANCY_NAME = "Evidence Scarcity and Dormancy"
SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME = "Shared Epistemic-Failure Boundary"
CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME = "Capability Under-Specification Boundary"
HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME = "Heterogeneous-Reproduction Boundary"
ADMISSION_DELAY_DECOMPOSITION_NAME = "Admission-Delay Decomposition"
EFFICIENCY_MEASUREMENT_NAME = "Efficiency Measurement"
SECONDARY_DATASET_GENERALIZATION_NAME = "Secondary-Dataset Generalization"

DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME = "Data and Domain Evidence Validation"
PROTOCOL_INVARIANT_VALIDATION_NAME = "Protocol Invariant Validation"
BASELINE_IMPLEMENTATION_VALIDATION_NAME = "Baseline Implementation Validation"

COLLAPSE_EXPERIMENT_NAMES: tuple[CanonicalToken, ...] = (
    PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
    SINGLE_REPRODUCTION_NECESSITY_NAME,
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
    EXTERNAL_VERIFICATION_NECESSITY_NAME,
)

POST_CORE_EXPERIMENT_NAMES: tuple[CanonicalToken, ...] = (
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

_MASTER_SEED_COUNT = 10
_SMOKE_SEED_COUNT = 1

_EPISTEMIC_STRENGTHS: dict[EpistemicFailureType, tuple[str, ...]] = {
    EpistemicFailureType.SHARED_LABEL_ERROR: ("0.05", "0.10", "0.20"),
    EpistemicFailureType.SHARED_SPURIOUS_FEATURE: ("0.25", "0.50", "1.00"),
    EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT: ("0.25", "0.50", "1.00"),
}

_BASELINE_FIXTURE_BY_NAME: tuple[tuple[CanonicalToken, CanonicalToken], ...] = tuple(
    (identity.value, fixture.value)
    for identity, fixture in BASELINE_VALIDATION_FIXTURE_MAP.items()
    if fixture
    in (
        BaselineValidationFixture.LEGITIMATE_TARGET_CAPABILITY,
        BaselineValidationFixture.USEFUL_BACKDOORED_SOURCE_5_PERCENT,
        BaselineValidationFixture.MODEL_REPLACEMENT_BACKDOOR,
    )
)

_BASELINE_METHODS: tuple[CanonicalToken, ...] = tuple(name for name, _ in _BASELINE_FIXTURE_BY_NAME)
_BASELINE_FIXTURES: tuple[CanonicalToken, ...] = tuple(
    fixture for _, fixture in _BASELINE_FIXTURE_BY_NAME
)

EXPERIMENT_REGISTRY: tuple[ExperimentDefinition, ...] = (
    ExperimentDefinition(
        name=DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,
        experiment_class=ExperimentClass.VALIDATION,
        methods=("Data and Domain Evidence Validation",),
        conditions=("primary",),
        seed_count=_SMOKE_SEED_COUNT,
        nominal_cell_count=1,
        claim_family=None,
        prerequisites=(),
    ),
    ExperimentDefinition(
        name=PROTOCOL_INVARIANT_VALIDATION_NAME,
        experiment_class=ExperimentClass.VALIDATION,
        methods=("Protocol Invariant Validation",),
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
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=80,
        claim_family="proposal-screen necessity",
        prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
    ),
    ExperimentDefinition(
        name=SINGLE_REPRODUCTION_NECESSITY_NAME,
        experiment_class=ExperimentClass.EXPLORATORY,
        methods=("One Independent Retrain", "Full Plurality Path"),
        conditions=tuple(condition.value for condition in PluralityCondition),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=60,
        claim_family="plurality necessity",
        prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
    ),
    ExperimentDefinition(
        name=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
        experiment_class=ExperimentClass.EXPLORATORY,
        methods=tuple(method.value for method in SourceExclusionMethod),
        conditions=(PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=60,
        claim_family="source-exclusion central claim",
        prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
    ),
    ExperimentDefinition(
        name=EXTERNAL_VERIFICATION_NECESSITY_NAME,
        experiment_class=ExperimentClass.EXPLORATORY,
        methods=("Full FedSIRA", "Multiple Retrains with Direct Krum"),
        conditions=tuple(condition.value for condition in ExternalVerificationCondition),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=80,
        claim_family="external reproduction verification necessity",
        prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
    ),
    ExperimentDefinition(
        name=PRIMARY_CONFIRMATORY_EVALUATION_NAME,
        experiment_class=ExperimentClass.CONFIRMATORY,
        methods=(
            "Resolved FedSIRA Core",
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
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=420,
        claim_family="primary baseline superiority",
        prerequisites=(PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,),
    ),
    ExperimentDefinition(
        name=MECHANISM_ABLATION_NAME,
        experiment_class=ExperimentClass.ABLATION,
        methods=tuple(variant.value for variant in AblationVariant),
        conditions=("Ablation",),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=180,
        claim_family="mechanism ablation",
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=COMPROMISED_REPRODUCER_ROBUSTNESS_NAME,
        experiment_class=ExperimentClass.ROBUSTNESS,
        methods=(
            "Resolved FedSIRA Core",
            BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
            BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
            BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value,
        ),
        conditions=tuple(condition.value for condition in ReproducerCondition),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=280,
        claim_family="reproducer robustness",
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
        experiment_class=ExperimentClass.ROBUSTNESS,
        methods=tuple(profile.value for profile in VerifierProfile),
        conditions=tuple(condition.value for condition in VerifierCondition),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=100,
        claim_family="verifier robustness",
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=BYZANTINE_BOUND_VIOLATION_NAME,
        experiment_class=ExperimentClass.FAILURE_BOUNDARY,
        methods=("Resolved FedSIRA Core", "Multiple Retrains with Direct Krum"),
        conditions=tuple(condition.value for condition in BoundCondition),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=80,
        claim_family=None,
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
        experiment_class=ExperimentClass.FAILURE_BOUNDARY,
        methods=("Resolved FedSIRA Core",),
        conditions=tuple(schedule.value for schedule in EvidenceArrivalSchedule),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=40,
        claim_family=None,
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=SHARED_EPISTEMIC_FAILURE_BOUNDARY_NAME,
        experiment_class=ExperimentClass.FAILURE_BOUNDARY,
        methods=("Resolved FedSIRA Core",),
        conditions=tuple(
            f"{failure_type.value}|{strength}"
            for failure_type in EpistemicFailureType
            for strength in _EPISTEMIC_STRENGTHS[failure_type]
        ),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=90,
        claim_family="heterogeneity/failure-boundary secondary comparisons",
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
        experiment_class=ExperimentClass.FAILURE_BOUNDARY,
        methods=tuple(granularity.value for granularity in CapabilityContractGranularity),
        conditions=tuple(mixture.value for mixture in RootCauseMixture),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=60,
        claim_family="heterogeneity/failure-boundary secondary comparisons",
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=HETEROGENEOUS_REPRODUCTION_BOUNDARY_NAME,
        experiment_class=ExperimentClass.ROBUSTNESS,
        methods=(
            "Resolved FedSIRA Core",
            BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
            BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
            BaselineIdentity.KRUM_ROBUST_AGGREGATION_REFERENCE.value,
        ),
        conditions=tuple(regime.value for regime in HeterogeneityRegime),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=160,
        claim_family="heterogeneity/failure-boundary secondary comparisons",
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=ADMISSION_DELAY_DECOMPOSITION_NAME,
        experiment_class=ExperimentClass.DIAGNOSTIC,
        methods=(
            "Resolved FedSIRA Core",
            BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
            BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
        ),
        conditions=tuple(schedule.value for schedule in EvidenceArrivalSchedule),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=120,
        claim_family=None,
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
    ),
    ExperimentDefinition(
        name=EFFICIENCY_MEASUREMENT_NAME,
        experiment_class=ExperimentClass.DIAGNOSTIC,
        methods=(
            "Resolved FedSIRA Core",
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
            "Resolved FedSIRA Core",
            BaselineIdentity.ONE_INDEPENDENT_RETRAIN.value,
            BaselineIdentity.MULTIPLE_RETRAINS_WITH_DIRECT_KRUM.value,
            BaselineIdentity.CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION.value,
            BaselineIdentity.FEDAVG_REFERENCE.value,
        ),
        conditions=tuple(scenario.value for scenario in SecondaryScenario),
        seed_count=_MASTER_SEED_COUNT,
        nominal_cell_count=100,
        claim_family="secondary generalization",
        prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
        dataset=DatasetId.CICIOT2023,
    ),
)


def experiment_by_name(name: CanonicalToken) -> ExperimentDefinition:
    for definition in EXPERIMENT_REGISTRY:
        if definition.name == name:
            return definition
    raise KeyError(f"unknown experiment {name!r}")


def experiment_names() -> tuple[CanonicalToken, ...]:
    return tuple(definition.name for definition in EXPERIMENT_REGISTRY)
