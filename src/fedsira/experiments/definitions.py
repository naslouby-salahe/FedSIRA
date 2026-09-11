from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import TypeAlias

from fedsira.domain.enums import (
    ComparisonMetric,
    CoreMethodIdentity,
    DatasetId,
    RootCauseMixture,
)
from fedsira.domain.types import (
    ArtifactFileName,
    BooleanValue,
    ConditionName,
    ExperimentName,
    FigureName,
    FrozenDomainModel,
    MethodName,
    ScientificCellCount,
    SeedCount,
    TableName,
)
from fedsira.protocol.baselines.registry import (
    BASELINE_VALIDATION_FIXTURE_MAP,
    BaselineIdentity,
    BaselineValidationFixture,
)
from fedsira.protocol.specification import EvidenceArrivalSchedule
from fedsira.runtime import current_application_context


class ComparisonFamily(StrEnum):
    PROPOSAL_SCREEN_NECESSITY = "proposal-screen necessity"
    PLURALITY_NECESSITY = "plurality necessity"
    SOURCE_EXCLUSION_CENTRAL_EFFECT = "source-exclusion central effect"
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


class EfficiencyCondition(StrEnum):
    TIMED = "timed"


class TrainingProtocolStage(StrEnum):
    ANCHOR = "anchor"
    SOURCE_CANDIDATE = "source candidate"
    HONEST_REPRODUCTION = "honest reproduction"


class DescriptiveScientificMetric(StrEnum):
    VALIDATION_GATE = "validation gate"
    LOGICAL_STATE_BY_CYCLE = "state-by-logical-cycle"
    TIME_TO_FIRST_REPRODUCTION = "time-to-first-reproduction"
    T_EVIDENCE = "t-evidence"
    TIME_TO_CERTIFICATE = "time-to-certificate"
    TERMINAL_PROTOCOL_OUTCOME = "terminal-protocol-outcome"
    CROSS_DOMAIN_VERIFIER_AGREEMENT = "cross-domain-verifier-agreement"
    CERTIFIED_ROW_YIELD = "certified-row-yield"
    ROOT_CAUSE_TARGET_F1 = "root-cause-target-f1"
    CERTIFICATE_ADMISSION_RATE = "certificate-admission-rate-under-corrupted-operational-evidence"
    WALL_CLOCK_SECONDS = "post-evidence-wall-clock-seconds"
    GPU_SECONDS = "gpu-seconds"
    PEAK_GPU_MEMORY_BYTES = "peak-gpu-memory-bytes"
    PEAK_HOST_RSS_BYTES = "peak-host-rss-bytes"
    COMMUNICATION_BYTES = "communication-bytes"
    MODEL_TRANSMISSIONS = "model-transmissions"
    PERSISTENT_STORAGE_BYTES = "persistent-storage-bytes"
    TOTAL_ATTEMPTS = "total-attempts"
    DORMANT_ADMISSION_RATE = "dormant-admission-rate"


ScientificMetric: TypeAlias = ComparisonMetric | DescriptiveScientificMetric


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


CELL_METRICS_TABLE_NAME: TableName = "Cell Metrics"
CELL_METRICS_PARQUET_NAME: ArtifactFileName = "cell-metrics.parquet"
SEED_METRICS_PARQUET_NAME: ArtifactFileName = "seed-metrics.parquet"
AGGREGATE_METRICS_PARQUET_NAME: ArtifactFileName = "aggregate-metrics.parquet"
STATE_TRAJECTORY_PARQUET_NAME: ArtifactFileName = "state-trajectory.parquet"
PROTOCOL_SCHEMATIC_FIGURE_NAME: FigureName = "FedSIRA Protocol Schematic"
PRIMARY_SECURITY_UTILITY_TRADEOFF_FIGURE_NAME: FigureName = "Primary Security-Utility Tradeoff"
USEFUL_BACKDOORED_SOURCE_FIGURE_NAME: FigureName = "Useful Backdoored Source"
COLLAPSE_DECISION_EFFECTS_FIGURE_NAME: FigureName = "Collapse Decision Effects"
COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME: FigureName = "Compromised-Reproducer Boundary"
COMPROMISED_VERIFIER_BOUNDARY_FIGURE_NAME: FigureName = "Compromised-Verifier Boundary"
SHARED_EPISTEMIC_FAILURE_FIGURE_NAME: FigureName = "Shared Epistemic Failure"
CAPABILITY_GRANULARITY_BOUNDARY_FIGURE_NAME: FigureName = "Capability-Granularity Boundary"
HETEROGENEITY_SYNTHESIS_BOUNDARY_FIGURE_NAME: FigureName = "Heterogeneity Synthesis Boundary"
ADMISSION_DELAY_DECOMPOSITION_FIGURE_NAME: FigureName = "Admission-Delay Decomposition"
EFFICIENCY_PROFILE_FIGURE_NAME: FigureName = "Efficiency Profile"
EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME: FigureName = "Evidence-Arrival State Trajectory"
SECONDARY_GENERALIZATION_FIGURE_NAME: FigureName = "Secondary Generalization"


class ExperimentArtifactSpecification(FrozenDomainModel):
    metrics_required: BooleanValue
    required_metric_artifacts: tuple[ArtifactFileName, ...]
    required_tables: tuple[TableName, ...]
    required_figures: tuple[FigureName, ...]


def experiment_artifacts(
    *specialized_figures: FigureName,
    additional_metric_artifacts: tuple[ArtifactFileName, ...] = (),
) -> ExperimentArtifactSpecification:
    return ExperimentArtifactSpecification(
        metrics_required=True,
        required_metric_artifacts=(
            CELL_METRICS_PARQUET_NAME,
            SEED_METRICS_PARQUET_NAME,
            AGGREGATE_METRICS_PARQUET_NAME,
            *additional_metric_artifacts,
        ),
        required_tables=(CELL_METRICS_TABLE_NAME,),
        required_figures=(PROTOCOL_SCHEMATIC_FIGURE_NAME, *specialized_figures),
    )


class ExperimentDefinition(FrozenDomainModel):
    name: ExperimentName
    experiment_class: ExperimentClass
    methods: tuple[MethodName, ...]
    conditions: tuple[ConditionName, ...]
    seed_count: SeedCount
    nominal_cell_count: ScientificCellCount
    primary_metrics: tuple[ScientificMetric, ...]
    comparison_family: ComparisonFamily | None
    prerequisites: tuple[ExperimentName, ...]
    dataset: DatasetId
    artifacts: ExperimentArtifactSpecification


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

_VALIDATION_METRICS: tuple[ScientificMetric, ...] = (DescriptiveScientificMetric.VALIDATION_GATE,)
_OPENING_NECESSITY_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.FALSE_LAUNCH,
    ComparisonMetric.REPRODUCTION_ATTEMPTS,
    ComparisonMetric.POST_EVIDENCE_OVERHEAD,
    ComparisonMetric.LEGITIMATE_ADMISSION,
    ComparisonMetric.MALICIOUS_ADMISSION,
)
_PLURALITY_NECESSITY_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.LEGITIMATE_ADMISSION,
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
    ComparisonMetric.WORST_DOMAIN_TARGET_F1,
)
_SOURCE_EXCLUSION_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.ATTACK_SUCCESS_RATE,
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
    ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
)
_EXTERNAL_VERIFICATION_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.LEGITIMATE_ADMISSION,
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
    ComparisonMetric.WORST_DOMAIN_TARGET_F1,
)
_PRIMARY_CONFIRMATORY_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
    ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
    ComparisonMetric.LEGITIMATE_ADMISSION,
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.ATTACK_SUCCESS_RATE,
)
_MECHANISM_ABLATION_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.ATTACK_SUCCESS_RATE,
    ComparisonMetric.REPRODUCTION_ATTEMPTS,
    ComparisonMetric.FALSE_LAUNCH,
    ComparisonMetric.WORST_DOMAIN_TARGET_F1,
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.LEGITIMATE_ADMISSION,
    ComparisonMetric.POST_EVIDENCE_OVERHEAD,
    ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
)
_REPRODUCER_ROBUSTNESS_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.ATTACK_SUCCESS_RATE,
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
)
_VERIFIER_ROBUSTNESS_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.LEGITIMATE_ADMISSION,
)
_BYZANTINE_BOUND_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.LEGITIMATE_ADMISSION,
    ComparisonMetric.ATTACK_SUCCESS_RATE,
    ComparisonMetric.TARGET_F1,
)
_EVIDENCE_SCARCITY_METRICS: tuple[ScientificMetric, ...] = (
    DescriptiveScientificMetric.LOGICAL_STATE_BY_CYCLE,
    DescriptiveScientificMetric.TIME_TO_FIRST_REPRODUCTION,
    DescriptiveScientificMetric.T_EVIDENCE,
    DescriptiveScientificMetric.TIME_TO_CERTIFICATE,
    DescriptiveScientificMetric.TERMINAL_PROTOCOL_OUTCOME,
)
_EPISTEMIC_FAILURE_METRICS: tuple[ScientificMetric, ...] = (
    DescriptiveScientificMetric.CERTIFICATE_ADMISSION_RATE,
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
    ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
)
_CAPABILITY_GRANULARITY_METRICS: tuple[ScientificMetric, ...] = (
    DescriptiveScientificMetric.CROSS_DOMAIN_VERIFIER_AGREEMENT,
    DescriptiveScientificMetric.CERTIFIED_ROW_YIELD,
    DescriptiveScientificMetric.ROOT_CAUSE_TARGET_F1,
    ComparisonMetric.FALSE_SAME_CAPABILITY_CERTIFICATION_RATE,
)
_HETEROGENEITY_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.WORST_DOMAIN_TARGET_F1,
    ComparisonMetric.LEGITIMATE_ADMISSION,
    DescriptiveScientificMetric.DORMANT_ADMISSION_RATE,
)
_DELAY_METRICS: tuple[ScientificMetric, ...] = (
    DescriptiveScientificMetric.T_EVIDENCE,
    DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
    DescriptiveScientificMetric.TOTAL_ATTEMPTS,
    DescriptiveScientificMetric.TERMINAL_PROTOCOL_OUTCOME,
)
_EFFICIENCY_METRICS: tuple[ScientificMetric, ...] = (
    DescriptiveScientificMetric.WALL_CLOCK_SECONDS,
    DescriptiveScientificMetric.GPU_SECONDS,
    DescriptiveScientificMetric.PEAK_GPU_MEMORY_BYTES,
    DescriptiveScientificMetric.PEAK_HOST_RSS_BYTES,
    DescriptiveScientificMetric.COMMUNICATION_BYTES,
    DescriptiveScientificMetric.MODEL_TRANSMISSIONS,
    DescriptiveScientificMetric.PERSISTENT_STORAGE_BYTES,
)
_SECONDARY_GENERALIZATION_METRICS: tuple[ScientificMetric, ...] = (
    ComparisonMetric.TARGET_F1,
    ComparisonMetric.SUPPORTED_MACRO_F1_HARM,
    ComparisonMetric.BENIGN_FALSE_ALARM_RATE_INCREASE,
    ComparisonMetric.MALICIOUS_ADMISSION,
    ComparisonMetric.LEGITIMATE_ADMISSION,
)


def _confirmatory_seed_count() -> SeedCount:
    seeds = current_application_context().scientific_config.seeds_and_determinism
    return seeds.confirmatory_seed_count


def _timing_diagnostic_seed_count() -> SeedCount:
    timing = current_application_context().scientific_config.execution.timing
    return timing.diagnostic_master_seed_count


def _unique(values: Iterable[ConditionName]) -> tuple[ConditionName, ...]:
    result: list[ConditionName] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def epistemic_strength_tokens(failure_type: EpistemicFailureType) -> tuple[ConditionName, ...]:
    attacks = current_application_context().scientific_config.attacks_and_boundaries
    if failure_type is EpistemicFailureType.SHARED_LABEL_ERROR:
        strengths = attacks.shared_label_error.strengths
    elif failure_type is EpistemicFailureType.SHARED_SPURIOUS_FEATURE:
        strengths = attacks.shared_spurious_feature.strengths
    elif failure_type is EpistemicFailureType.ATTACKER_INDUCED_COMMON_CONTEXT:
        strengths = attacks.attacker_induced_common_context.strengths
    else:
        raise ValueError(f"unsupported epistemic failure type: {failure_type.value}")
    return tuple(f"{strength:.2f}" for strength in strengths)


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
            primary_metrics=_VALIDATION_METRICS,
            comparison_family=None,
            prerequisites=(),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(),
        ),
        ExperimentDefinition(
            name=PROTOCOL_INVARIANT_VALIDATION_NAME,
            experiment_class=ExperimentClass.VALIDATION,
            methods=(PROTOCOL_INVARIANT_VALIDATION_NAME,),
            conditions=("aggregate",),
            seed_count=_SMOKE_SEED_COUNT,
            nominal_cell_count=1,
            primary_metrics=_VALIDATION_METRICS,
            comparison_family=None,
            prerequisites=(),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(),
        ),
        ExperimentDefinition(
            name=BASELINE_IMPLEMENTATION_VALIDATION_NAME,
            experiment_class=ExperimentClass.VALIDATION,
            methods=_BASELINE_METHODS,
            conditions=_BASELINE_FIXTURES,
            seed_count=_SMOKE_SEED_COUNT,
            nominal_cell_count=17,
            primary_metrics=_VALIDATION_METRICS,
            comparison_family=None,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(),
        ),
        ExperimentDefinition(
            name=PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,
            experiment_class=ExperimentClass.EXPLORATORY,
            methods=tuple(mode.value for mode in OpeningMode),
            conditions=tuple(episode.value for episode in ProposalEpisode),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=80,
            primary_metrics=_OPENING_NECESSITY_METRICS,
            comparison_family=ComparisonFamily.PROPOSAL_SCREEN_NECESSITY,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(COLLAPSE_DECISION_EFFECTS_FIGURE_NAME),
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
            primary_metrics=_PLURALITY_NECESSITY_METRICS,
            comparison_family=ComparisonFamily.PLURALITY_NECESSITY,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(COLLAPSE_DECISION_EFFECTS_FIGURE_NAME),
        ),
        ExperimentDefinition(
            name=SOURCE_ARTIFACT_EXCLUSION_NECESSITY_NAME,
            experiment_class=ExperimentClass.EXPLORATORY,
            methods=tuple(method.value for method in SourceExclusionMethod),
            conditions=(PrimaryScenario.USEFUL_BACKDOORED_SOURCE_5_PERCENT.value,),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=60,
            primary_metrics=_SOURCE_EXCLUSION_METRICS,
            comparison_family=ComparisonFamily.SOURCE_EXCLUSION_CENTRAL_EFFECT,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(
                USEFUL_BACKDOORED_SOURCE_FIGURE_NAME,
                COLLAPSE_DECISION_EFFECTS_FIGURE_NAME,
            ),
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
            primary_metrics=_EXTERNAL_VERIFICATION_METRICS,
            comparison_family=ComparisonFamily.EXTERNAL_VERIFICATION_NECESSITY,
            prerequisites=(DATA_AND_DOMAIN_EVIDENCE_VALIDATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(COLLAPSE_DECISION_EFFECTS_FIGURE_NAME),
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
            primary_metrics=_PRIMARY_CONFIRMATORY_METRICS,
            comparison_family=ComparisonFamily.PRIMARY_BASELINE_SUPERIORITY,
            prerequisites=(PROPOSAL_ASSISTED_OPENING_NECESSITY_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(PRIMARY_SECURITY_UTILITY_TRADEOFF_FIGURE_NAME),
        ),
        ExperimentDefinition(
            name=MECHANISM_ABLATION_NAME,
            experiment_class=ExperimentClass.ABLATION,
            methods=tuple(variant.value for variant in AblationVariant),
            conditions=_ABLATION_SCENARIOS,
            seed_count=confirmatory_seed_count,
            nominal_cell_count=180,
            primary_metrics=_MECHANISM_ABLATION_METRICS,
            comparison_family=ComparisonFamily.MECHANISM_ABLATION,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(),
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
            primary_metrics=_REPRODUCER_ROBUSTNESS_METRICS,
            comparison_family=ComparisonFamily.REPRODUCER_ROBUSTNESS,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(COMPROMISED_REPRODUCER_BOUNDARY_FIGURE_NAME),
        ),
        ExperimentDefinition(
            name=COMPROMISED_VERIFIER_ROBUSTNESS_NAME,
            experiment_class=ExperimentClass.ROBUSTNESS,
            methods=tuple(profile.value for profile in VerifierProfile),
            conditions=tuple(condition.value for condition in VerifierCondition),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=100,
            primary_metrics=_VERIFIER_ROBUSTNESS_METRICS,
            comparison_family=ComparisonFamily.VERIFIER_ROBUSTNESS,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(COMPROMISED_VERIFIER_BOUNDARY_FIGURE_NAME),
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
            primary_metrics=_BYZANTINE_BOUND_METRICS,
            comparison_family=None,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(),
        ),
        ExperimentDefinition(
            name=EVIDENCE_SCARCITY_AND_DORMANCY_NAME,
            experiment_class=ExperimentClass.FAILURE_BOUNDARY,
            methods=(CoreMethodIdentity.RESOLVED_FEDSIRA_CORE.value,),
            conditions=tuple(schedule.value for schedule in EvidenceArrivalSchedule),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=40,
            primary_metrics=_EVIDENCE_SCARCITY_METRICS,
            comparison_family=None,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(
                EVIDENCE_ARRIVAL_STATE_TRAJECTORY_FIGURE_NAME,
                additional_metric_artifacts=(STATE_TRAJECTORY_PARQUET_NAME,),
            ),
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
            primary_metrics=_EPISTEMIC_FAILURE_METRICS,
            comparison_family=ComparisonFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(SHARED_EPISTEMIC_FAILURE_FIGURE_NAME),
        ),
        ExperimentDefinition(
            name=CAPABILITY_UNDER_SPECIFICATION_BOUNDARY_NAME,
            experiment_class=ExperimentClass.FAILURE_BOUNDARY,
            methods=tuple(granularity.value for granularity in CapabilityContractGranularity),
            conditions=tuple(mixture.value for mixture in RootCauseMixture),
            seed_count=confirmatory_seed_count,
            nominal_cell_count=60,
            primary_metrics=_CAPABILITY_GRANULARITY_METRICS,
            comparison_family=ComparisonFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(CAPABILITY_GRANULARITY_BOUNDARY_FIGURE_NAME),
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
            primary_metrics=_HETEROGENEITY_METRICS,
            comparison_family=ComparisonFamily.HETEROGENEITY_FAILURE_BOUNDARY_SECONDARY,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(HETEROGENEITY_SYNTHESIS_BOUNDARY_FIGURE_NAME),
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
            primary_metrics=_DELAY_METRICS,
            comparison_family=None,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(ADMISSION_DELAY_DECOMPOSITION_FIGURE_NAME),
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
            conditions=(EfficiencyCondition.TIMED.value,),
            seed_count=_timing_diagnostic_seed_count(),
            nominal_cell_count=60,
            primary_metrics=_EFFICIENCY_METRICS,
            comparison_family=None,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.N_BAIOT,
            artifacts=experiment_artifacts(EFFICIENCY_PROFILE_FIGURE_NAME),
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
            primary_metrics=_SECONDARY_GENERALIZATION_METRICS,
            comparison_family=ComparisonFamily.SECONDARY_GENERALIZATION,
            prerequisites=(PRIMARY_CONFIRMATORY_EVALUATION_NAME,),
            dataset=DatasetId.CICIOT2023,
            artifacts=experiment_artifacts(SECONDARY_GENERALIZATION_FIGURE_NAME),
        ),
    )


def experiment_by_name(name: ExperimentName) -> ExperimentDefinition:
    for definition in experiment_registry():
        if definition.name == name:
            return definition
    raise KeyError(f"unknown experiment {name!r}")


def experiment_names() -> tuple[ExperimentName, ...]:
    return tuple(definition.name for definition in experiment_registry())
