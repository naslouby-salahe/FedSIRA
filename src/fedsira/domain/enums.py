from enum import StrEnum


class LogEvent(StrEnum):
    DATASET_INGEST = "dataset.ingest"
    DATASET_ROLES = "dataset.roles"
    DATASET_INGEST_COMPLETED = "dataset.ingest.completed"
    DATASET_SHARD_WIDTH_EXCLUDED = "dataset.shard.width.excluded"
    DATASET_SCALER_FITTED = "dataset.scaler.fitted"
    DATASET_VIEW_WRITTEN = "dataset.view.written"
    DATASET_PREPROCESSING_STARTED = "dataset.preprocessing.started"
    DATASET_PREPROCESSING_COMPLETED = "dataset.preprocessing.completed"
    EXPERIMENT_STARTED = "experiment.started"
    EXPERIMENT_CONFIGURATION_RESOLVED = "experiment.configuration.resolved"
    EXPERIMENT_PLAN_CREATED = "experiment.plan.created"
    EXPERIMENT_PREREQUISITES_VALIDATED = "experiment.prerequisites.validated"
    EXPERIMENT_PROGRESS = "experiment.progress"
    EXPERIMENT_COMPLETED = "experiment.completed"
    EXPERIMENT_FAILED = "experiment.failed"
    CELL_STARTED = "cell.started"
    CELL_COMPLETED = "cell.completed"
    CELL_REUSED = "cell.reused"
    CELL_RECORD_PERSISTED = "cell.record.persisted"
    CELL_METRIC_COMPUTED = "cell.metric.computed"
    CELL_REUSE_REJECTED = "cell.reuse.rejected"
    CELL_PHASE_STARTED = "cell.phase.started"
    CELL_PHASE_TIMEOUT = "cell.phase.timeout"
    CELL_PHASE_COMPLETED = "cell.phase.completed"
    ABLATION_REFERENCE_REUSED = "ablation.reference.reused"
    ABLATION_REFERENCE_PUBLISHED = "ablation.reference.published"
    ABLATION_REFERENCES_MATERIALIZED = "ablation.references.materialized"
    COMPARISON_STARTED = "comparison.started"
    COMPARISON_COMPLETED = "comparison.completed"
    COMPARISON_EVIDENCE_PERSISTED = "comparison.evidence.persisted"
    REPORT_STARTED = "report.started"
    REPORT_COMPLETED = "report.completed"
    REPORT_TABLE_STARTED = "report.table.started"
    REPORT_EXPERIMENT_ARTIFACTS_RENDERED = "report.experiment.artifacts.rendered"
    REPORT_PROJECT_TABLES_STARTED = "report.project.tables.started"
    REPORT_TABLE_GENERATED = "report.table.generated"
    REPORT_TABLES_COMPLETED = "report.tables.completed"
    REPORT_FIGURE_STARTED = "report.figure.started"
    REPORT_FIGURE_GENERATED = "report.figure.generated"
    ANCHOR_ROUND_EVALUATED = "anchor.round.evaluated"
    ANCHOR_TRAINING_STARTED = "anchor.training.started"
    ANCHOR_TRAINING_COMPLETED = "anchor.training.completed"
    ARTIFACT_REUSED = "artifact.reused"
    ARTIFACT_PUBLISHED = "artifact.published"


class DatasetId(StrEnum):
    N_BAIOT = "N-BaIoT"
    CICIOT2023 = "CICIoT2023"


class Role(StrEnum):
    ANCHOR_TRAIN = "Anchor Train"
    ANCHOR_VALIDATION = "Anchor Validation"
    POST_REFERENCE_REPLAY = "Post-Reference Replay"
    ROW_VERIFICATION = "Row Verification"
    FINAL_GATE = "Final Gate"
    REPORT_TEST = "Report Test"
    SOURCE_PROPOSAL = "Source Proposal"
    CANDIDATE_SCREEN = "Candidate Screen"
    REPRODUCTION = "Reproduction"


class ByteUnit(StrEnum):
    IEC = "IEC"


class CICIoT2023Acquisition(StrEnum):
    LABELED_SHARDS = "Labeled shards"
    PER_ATTACK_SHARDS = "Per-attack shards"


class ArtifactLifecycleState(StrEnum):
    STAGING = "Staging"
    COMPLETE = "Complete"


class CellPhaseState(StrEnum):
    PLANNED = "Planned"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    INVALID = "Invalid"


class ExperimentLifecycleState(StrEnum):
    NOT_STARTED = "Not Started"
    BLOCKED = "Blocked"
    READY = "Ready"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    INVALID = "Invalid"


class ProjectStage(StrEnum):
    DOCTOR_READINESS = "doctor readiness diagnosis"
    PREPROCESSING_AND_DATA_VALIDATION = "preprocessing and data/domain validation"
    PROTOCOL_INVARIANT_SMOKE = "protocol/invariant smoke"
    BASELINE_IMPLEMENTATION_VALIDATION = "baseline implementation validation"
    MECHANISM_COLLAPSE = "four mechanism-collapse experiments"
    RESOLVED_CORE_DERIVATION = "resolved-core derivation"
    PRIMARY_CONFIRMATORY_EVALUATION = "primary confirmatory evaluation"
    MECHANISM_ABLATIONS = "mechanism ablations"
    BYZANTINE_ROBUSTNESS = "Byzantine robustness and bound violations"
    EVIDENCE_AND_FAILURE_BOUNDARIES = "evidence and scientific failure boundaries"
    DELAY_AND_EFFICIENCY = "delay and efficiency"
    SECONDARY_GENERALIZATION = "secondary generalization"
    STATISTICAL_EVIDENCE_COMPLETION = "project statistical/evidence completion"
    REPORT_EXPORT = "report project verification and export"


class ScientificCellPhase(StrEnum):
    PREPARE = "PREPARE"
    TRAIN = "TRAIN"
    SCORE = "SCORE"
    PROTOCOL_EVALUATION = "PROTOCOL_EVALUATION"
    METRIC_AGGREGATION = "METRIC_AGGREGATION"
    STATISTICAL_ANALYSIS = "STATISTICAL_ANALYSIS"


class FailureClass(StrEnum):
    CONFIGURATION_INVALID = "Configuration Invalid"
    DATA_INVALID = "Data Invalid"
    INVARIANT_VIOLATION = "Invariant Violation"
    IMPLEMENTATION_ERROR = "Implementation Error"
    NUMERICAL_FAILURE = "Numerical Failure"
    INFRASTRUCTURE_INTERRUPTION = "Infrastructure Interruption"
    TIMEOUT = "Timeout"
    EVIDENCE_INSUFFICIENT = "Evidence Insufficient"
    ASSUMPTION_VIOLATION = "Assumption Violation"


class ArtifactFamily(StrEnum):
    RAW_DATASET_IDENTITY = "Raw dataset identity"
    DATASET_MANIFEST = "Dataset/schema/exclusion manifest"
    ROLE_SPLIT_SAMPLE_MANIFEST = "Role/split/sample manifest"
    SCALER = "Scaler"
    PREPARED_ROLE_VIEW = "Prepared role view"
    ANCHOR_CHECKPOINT = "Anchor checkpoint and round checkpoints"
    SOURCE_CANDIDATE_CHECKPOINT = "Source candidate checkpoint/update"
    REPRODUCTION_CHECKPOINT = "Honest or Byzantine reproduction checkpoint/update"
    BASELINE_CHECKPOINT = "Standard FL/baseline checkpoint/update"
    MODEL_SCORE_ARTIFACT = "Model score artifact"
    SCREEN_MATCHING_ARTIFACT = "Screen matching/differential artifact"
    BASELINE_CALIBRATION_ARTIFACT = "Baseline calibration artifact"
    FIXED_PROTOCOL_CONFIGURATION = "Fixed Capability Contract/Krum/protocol configuration"
    VERIFIER_ASSIGNMENT_REPORT = "Verifier assignment/report"
    REPRODUCTION_CERTIFICATE = "Reproduction certificate"
    KRUM_SYNTHESIZED_UPDATE = "Krum synthesized update/model"
    FINAL_GATE_DECISION = "Final-gate evaluation/decision"
    DOMAIN_SEED_METRIC_ARTIFACT = "Domain/seed metric artifact"
    STATISTICAL_COMPARISON_ARTIFACT = "Statistical comparison/gate artifact"
    TABLE_FIGURE_SOURCE_DATA = "Table/figure source data"
    TABLE_FIGURE_REPORT_EXPORT = "Table/figure/report export"


class ArtifactFamilyDirectoryToken(StrEnum):
    RAW_DATASET_IDENTITY = "raw-dataset-identity"
    DATASET_MANIFEST = "dataset-manifest"
    ROLE_SPLIT_SAMPLE_MANIFEST = "role-split-sample-manifest"
    SCALER = "scaler"
    PREPARED_ROLE_VIEW = "prepared-role-view"
    ANCHOR_CHECKPOINT = "anchor-checkpoint"
    SOURCE_CANDIDATE_CHECKPOINT = "source-candidate-checkpoint"
    REPRODUCTION_CHECKPOINT = "reproduction-checkpoint"
    BASELINE_CHECKPOINT = "baseline-checkpoint"
    MODEL_SCORE_ARTIFACT = "model-score-artifact"
    SCREEN_MATCHING_ARTIFACT = "screen-matching-artifact"
    BASELINE_CALIBRATION_ARTIFACT = "baseline-calibration-artifact"
    FIXED_PROTOCOL_CONFIGURATION = "fixed-protocol-configuration"
    VERIFIER_ASSIGNMENT_REPORT = "verifier-assignment-report"
    REPRODUCTION_CERTIFICATE = "reproduction-certificate"
    KRUM_SYNTHESIZED_UPDATE = "krum-synthesized-update"
    FINAL_GATE_DECISION = "final-gate-decision"
    DOMAIN_SEED_METRIC_ARTIFACT = "domain-seed-metric-artifact"
    STATISTICAL_COMPARISON_ARTIFACT = "statistical-comparison-artifact"
    TABLE_FIGURE_SOURCE_DATA = "table-figure-source-data"
    TABLE_FIGURE_REPORT_EXPORT = "table-figure-report-export"


class ArtifactFileToken(StrEnum):
    PAYLOAD_SUFFIX = ".artifact.bin"
    MANIFEST_SUFFIX = ".manifest.json"
    CURRENT_FILE = "current.json"
    LOG_FILE = "artifacts.log"


class ArtifactInstanceLabel(StrEnum):
    ROLE_SPLIT = "role-split"
    RESOLVED_CORE = "resolved-fedsira-core"
    COMPARISONS = "comparisons"
    SOURCE_DATA = "source-data"
    REPORT_EXPORT = "report-export"
    SMOKE_INVARIANT = "smoke-invariant"
    SMOKE_PARENT = "smoke-parent"
    SMOKE_DESCENDANT = "smoke-descendant"


class ArtifactDependencyLabel(StrEnum):
    RAW_DATASET = "raw-dataset"
    PARENT = "parent"
    PREPARED_EVIDENCE = "prepared-evidence"
    PREPARED_ROLE_VIEW = "prepared-role-view"
    RAW_FILE_MANIFEST = "raw-file-manifest"
    DATASET_FILE_MANIFEST = "dataset-file-manifest"
    DATASET_MANIFEST = "dataset-manifest"
    ROLE_SPLIT_SAMPLE_MANIFEST = "role-split-manifest"
    EXECUTION_EVIDENCE = "execution-evidence"
    METRIC_EVIDENCE = "metric-evidence"
    SOURCE_DATA = "source-data"
    MODEL_CHECKPOINT = "model-checkpoint"
    OUTPUT_CLASS_REGISTRY = "output-class-registry"
    SCORING_TRANSFORM = "scoring-transform"
    NUMERICAL_RUNTIME = "numerical-runtime"
    ANCHOR_MODEL = "anchor-model"
    SOURCE_CANDIDATE_MODEL = "source-candidate-model"
    PRODUCTION_MODEL = "production-model"
    COMMITMENT_IDENTITY = "commitment-identity"
    CERTIFIED_ROW_REPORTS = "certified-row-reports"
    CERTIFIED_REPRODUCTION_ROWS = "certified-reproduction-rows"


class GitMetadataToken(StrEnum):
    GIT_DIR = ".git"
    HEAD = "HEAD"


class WorkspaceDirectoryToken(StrEnum):
    PREPROCESSING = "preprocessing"
    METADATA = "metadata"
    CACHE = "cache"
    STAGING = "staging"
    ARTIFACTS = "artifacts"
    LOGS = "logs"
    EXPERIMENTS = "experiments"
    PREPARED = "prepared"
    FEATURES = "features"
    VALIDATION = "validation"
    TELEMETRY = "telemetry"
    REPETITIONS = "repetitions"
    TABLES = "tables"
    FIGURES = "figures"
    METRICS = "metrics"
    MAIN = "main"
    PRIMARY = "primary"
    PROJECT_SUMMARY = "project_summary"
    RECORDS = "records"
    REPRODUCIBILITY = "reproducibility"
    EXECUTION = "execution"


class WorkspaceFileToken(StrEnum):
    SMOKE_RECORD = "smoke_record.json"
    PREPROCESSING_LOG = "preprocessing.log"
    EXPERIMENT_LOG = "experiment.log"
    SUMMARY_JSON = "summary.json"
    MANIFEST_JSON = "manifest.json"
    EXECUTION_SUMMARY_JSON = "execution_summary.json"
    TIMING_OBSERVATION_JSON = "timing-observation.json"


class AblationReproducerStrategy(StrEnum):
    NONE = "None"
    MODEL_REPLACEMENT = "Model replacement"
    VERIFIER_AWARE = "Verifier-aware"


class ArtifactDependencyKind(StrEnum):
    ARTIFACT = "Artifact identity"
    CONTENT = "Content digest"


class ArtifactProducer(StrEnum):
    RAW_ACQUISITION = "Raw acquisition"
    DATASET_PREPARATION = "Dataset preparation"
    PREPROCESSING = "Preprocessing"
    ANCHOR_TRAINING = "Anchor training"
    SOURCE_TRAINING = "Source training"
    REPRODUCTION_PRODUCER = "Reproduction producer"
    BASELINE_TRAINER = "Baseline trainer"
    SCORING_PRODUCER = "Scoring producer"
    PROPOSAL_SCREEN_CALIBRATION = "Proposal-screen calibration"
    BASELINE_CALIBRATION = "Baseline calibration"
    CONFIGURATION = "Configuration"
    EXTERNAL_VERIFICATION = "External verification"
    CERTIFICATE_PRODUCER = "Certificate producer"
    SYNTHESIS_PRODUCER = "Synthesis producer"
    FINAL_GATE_EVALUATOR = "Final-gate evaluator"
    METRIC_REGISTRY = "Metric registry"
    EVALUATION_PRODUCER = "Evaluation producer"
    REPORTING_SOURCE_DATA = "Reporting source data"
    REPORT_EXPORT = "Report export"


class ArtifactPathScope(StrEnum):
    PREPROCESSING = "preprocessing"
    PROJECT_ARTIFACT = "project_artifact"
    EXPERIMENT_ARTIFACT = "experiment_artifact"
    MANUSCRIPT_RESULT = "manuscript_result"


class AdmissionOpeningMode(StrEnum):
    PROPOSAL_ASSISTED = "PROPOSAL_ASSISTED"
    CANDIDATE_FREE = "CANDIDATE_FREE"


class AdmissionState(StrEnum):
    CANDIDATE_SCREEN = "Candidate Screen"
    ADMISSION_OPEN = "Admission Open"
    REPRODUCTION_PENDING = "Reproduction Pending"
    VERIFICATION_PENDING = "Verification Pending"
    SYNTHESIS_PENDING = "Synthesis Pending"
    ADMITTED = "Admitted"
    DORMANT = "Dormant"
    REJECTED = "Rejected Admission"
    EXPIRED = "Expired"


class DormantOrigin(StrEnum):
    CANDIDATE_SCREEN = "CANDIDATE_SCREEN"
    REPRODUCTION_PENDING = "REPRODUCTION_PENDING"
    SYNTHESIS_PENDING = "SYNTHESIS_PENDING"


class RootCause(StrEnum):
    A = "ROOT_CAUSE_A"
    B = "ROOT_CAUSE_B"


class CapabilityContractScope(StrEnum):
    BROAD_TARGET_ONLY = "Broad Target Only"
    ROOT_CAUSE_A_SCOPED = "Root-Cause A Scoped"
    ROOT_CAUSE_B_SCOPED = "Root-Cause B Scoped"


class RootCauseMixture(StrEnum):
    BALANCED_50_50 = "Balanced 50/50"
    A_DOMINANT_80_20 = "A-Dominant 80/20"


class EvaluationInsufficiencyReason(StrEnum):
    INSUFFICIENT_MATCHED_BENIGN_REPORT_TEST_CONTROLS = (
        "Insufficient Matched Benign Report-Test Controls"
    )


class ByzantineVerifierBehavior(StrEnum):
    FALSE_POSITIVE = "False Positive"
    FALSE_NEGATIVE = "False Negative"


class TernaryOutcome(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    ABSTAIN = "ABSTAIN"


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


class EnvironmentReadinessEffect(StrEnum):
    BLOCKING = "Blocking"
    ADVISORY = "Advisory"


class EpistemicFailureType(StrEnum):
    SHARED_LABEL_ERROR = "shared label/threat-intelligence error"
    SHARED_SPURIOUS_FEATURE = "shared spurious feature"
    ATTACKER_INDUCED_COMMON_CONTEXT = "attacker-induced common context"


class ProposalEpisode(StrEnum):
    LEGITIMATE_TARGET_CAPABILITY = "Legitimate Target Capability"
    GENERIC_HARD_SUPPORTED_EXAMPLES = "Generic Hard Supported Examples"
    IRRELEVANT_SOURCE_IMPROVEMENT = "Irrelevant Source Improvement"
    USEFUL_BACKDOORED_SOURCE_5_PERCENT = "Useful Backdoored Source — 5%"


class ExperimentName(StrEnum):
    DATA_AND_DOMAIN_EVIDENCE_VALIDATION = "Data and Domain Evidence Validation"
    PROTOCOL_INVARIANT_VALIDATION = "Protocol Invariant Validation"
    BASELINE_IMPLEMENTATION_VALIDATION = "Baseline Implementation Validation"
    PROPOSAL_ASSISTED_OPENING_NECESSITY = "Proposal-Assisted Opening Necessity"
    SINGLE_REPRODUCTION_NECESSITY = "Single-Reproduction Necessity"
    SOURCE_ARTIFACT_EXCLUSION_NECESSITY = "Source-Artifact Exclusion Necessity"
    EXTERNAL_VERIFICATION_NECESSITY = "External Verification Necessity"
    PRIMARY_CONFIRMATORY_EVALUATION = "Primary Confirmatory Evaluation"
    MECHANISM_ABLATION = "Mechanism Ablation"
    COMPROMISED_REPRODUCER_ROBUSTNESS = "Compromised-Reproducer Robustness"
    COMPROMISED_VERIFIER_ROBUSTNESS = "Compromised-Verifier Robustness"
    BYZANTINE_BOUND_VIOLATION = "Byzantine-Bound Violation"
    EVIDENCE_SCARCITY_AND_DORMANCY = "Evidence Scarcity and Dormancy"
    SHARED_EPISTEMIC_FAILURE_BOUNDARY = "Shared Epistemic-Failure Boundary"
    CAPABILITY_UNDER_SPECIFICATION_BOUNDARY = "Capability Under-Specification Boundary"
    HETEROGENEOUS_REPRODUCTION_BOUNDARY = "Heterogeneous-Reproduction Boundary"
    ADMISSION_DELAY_DECOMPOSITION = "Admission-Delay Decomposition"
    EFFICIENCY_MEASUREMENT = "Efficiency Measurement"
    SECONDARY_DATASET_GENERALIZATION = "Secondary-Dataset Generalization"


class TableName(StrEnum):
    DATASET_AND_DOMAIN_PROTOCOL = "Dataset and Domain Protocol"
    PRIMARY_DOMAIN_STATISTICS = "Primary Domain Statistics"
    MODEL_AND_TRAINING_PROTOCOL = "Model and Training Protocol"
    SECURITY_AND_CAPABILITY_CONTRACT_PROTOCOL = "Security and Capability-Contract Protocol"
    BASELINE_PROTOCOL = "Baseline Protocol"
    EXPERIMENT_PLAN = "Experiment Plan"
    METRIC_AND_STATISTICS_PROTOCOL = "Metric and Statistics Protocol"
    PRIMARY_RESULTS = "Primary Results"
    SOURCE_EXCLUSION_RESULTS = "Source-Exclusion Results"
    COLLAPSE_DECISIONS = "Collapse Decisions"
    ABLATION_RESULTS = "Ablation Results"
    BYZANTINE_ROBUSTNESS = "Byzantine Robustness"
    FAILURE_BOUNDARIES = "Failure Boundaries"
    DELAY_AND_EFFICIENCY = "Delay and Efficiency"
    GENERALIZATION_RESULTS = "Generalization Results"
    CELL_METRICS = "Cell Metrics"
    STATISTICAL_SUMMARY = "Statistical Summary"


class FigureName(StrEnum):
    PROTOCOL_SCHEMATIC = "FedSIRA Protocol Schematic"
    PRIMARY_SECURITY_UTILITY_TRADEOFF = "Primary Security-Utility Tradeoff"
    USEFUL_BACKDOORED_SOURCE = "Useful Backdoored Source"
    COLLAPSE_DECISION_EFFECTS = "Collapse Decision Effects"
    COMPROMISED_REPRODUCER_BOUNDARY = "Compromised-Reproducer Boundary"
    COMPROMISED_VERIFIER_BOUNDARY = "Compromised-Verifier Boundary"
    SHARED_EPISTEMIC_FAILURE = "Shared Epistemic Failure"
    CAPABILITY_GRANULARITY_BOUNDARY = "Capability-Granularity Boundary"
    HETEROGENEITY_SYNTHESIS_BOUNDARY = "Heterogeneity Synthesis Boundary"
    ADMISSION_DELAY_DECOMPOSITION = "Admission-Delay Decomposition"
    EFFICIENCY_PROFILE = "Efficiency Profile"
    EVIDENCE_ARRIVAL_STATE_TRAJECTORY = "Evidence-Arrival State Trajectory"
    SECONDARY_GENERALIZATION = "Secondary Generalization"


class ProtocolSchematicStage(StrEnum):
    SOURCE_COMMITMENT = "source commitment\n(zero direct weight)"
    FIXED_CAPABILITY_CONTRACT = "fixed Capability\nContract"
    NON_SOURCE_REPRODUCTION = "non-source\nreproduction"
    POST_COMMITMENT_VERIFIER_PANELS = "post-commitment\nverifier panels"
    EXTERNAL_REPRODUCTION_VERIFICATION = "five-row external\nreproduction verification"
    KRUM = "Krum"
    FINAL_FRESH_GATE = "final\nfresh gate"
    ADMISSION_DORMANCY_OR_REJECTION = "admission /\ndormancy / rejection"


class SmokeCheckName(StrEnum):
    NO_TARGET_SAMPLE_IN_ANCHOR_ROLES = "no target sample in anchor roles"
    NO_CROSS_ROLE_SAMPLE_OVERLAP = "no cross-role sample overlap"
    SOURCE_CANNOT_BE_VERIFIER = "source cannot be verifier"
    CELL_PHASE_SEQUENCE_WELL_FORMED = "canonical cell phase sequence is well-formed"
    PLURALITY_IMPLIES_HONEST_POSITIVE = (
        "2 positives with f_V=1 implies at least one honest positive"
    )
    KRUM_FIVE_ONE_ADMISSIBLE = "Krum n=5 f=1 admissible"
    KRUM_THREE_ONE_REJECTED = "Krum n=3 f=1 rejected"
    VERIFIER_ASSIGNMENT_BEFORE_COMMITMENT_THROWS = "verifier assignment before commitment throws"
    RANDOM_COMMITTEE_CONTAMINATION_PROBABILITY = (
        "random committee contamination probability 1/7 for b=2"
    )
    EXACT_SIGN_FLIP_TEST_ENUMERATES_ASSIGNMENTS = "exact sign-flip test enumerates all assignments"
    HOLM_ADJUSTMENT_MATCHES_FIXTURE = "Holm adjustment matches hand fixture"
    ONE_BATCH_FORWARD_BACKWARD_FINITE = "one-batch forward/backward finite"
    ONE_ROUND_FEDAVG_MATCHES_FIXTURE = "one-round FedAvg matches weighted average fixture"
    CHECKPOINT_RESTORE_REPRODUCES_PREDICTIONS = "checkpoint restore reproduces predictions"
    REPORT_TEST_LOADER_NOT_REQUESTED_BY_TRAINING = (
        "report-test loader cannot be requested by training"
    )
    POST_REFERENCE_MINIBATCH_KEEPS_KL_DEFINED = (
        "post-reference minibatch with no supported rows keeps KL defined"
    )
    HONEST_REPRODUCTION_HAS_NO_SOURCE_ARTIFACT = (
        "honest reproduction constructor has no source-artifact parameter"
    )
    SOURCE_DIRECT_PRODUCTION_WEIGHT_ZERO = "source direct production weight cannot become nonzero"
    ABSTAIN_NOT_CASTABLE_TO_BOOLEAN_VOTE = "Abstain cannot be cast to boolean vote"
    FEWER_THAN_FIVE_ROWS_CANNOT_SYNTHESIZE = (
        "fewer than five certified rows cannot call primary Krum synthesis"
    )
    FINAL_ADMISSION_REQUIRES_FINAL_GATE_ARTIFACT = (
        "final admission without final-gate artifact is impossible"
    )
    EIGHT_COLLAPSE_COMBINATIONS_RESOLVE = "all eight collapse combinations resolve"
    ROLES_ARE_DISJOINT = "source/reproducer/verifier/final/report roles are disjoint"
    RANDOM_COMMITTEE_EXACT_PROBABILITY_ZERO = (
        "random-committee exact probability is 0 for compromised-verifier counts 0/1"
    )
    POST_EVIDENCE_COMPONENTS_SUM_TO_TOTAL = "post-evidence wall-clock components sum to T_post"
    TYPE_SEVEN_QUANTILES_MATCH_NUMPY = "type-7 quantiles match NumPy linear fixtures"
    SAMPLE_SD_USES_DDOF_ONE = "sample SD uses ddof=1"
    CONFUSION_METRICS_MATCH_HAND_CALCULATIONS = "confusion-derived metrics match hand calculations"
    ZERO_DENOMINATORS_RETURN_NA = "zero denominators return NA plus reason"
    BOOTSTRAP_DRAWS_DETERMINISTIC = "bootstrap draws are deterministic under the analysis seed"
    COMPLETE_ARTIFACT_MANIFEST_IS_READABLE = "complete artifact manifest is readable"
    PARENT_IDENTITY_CHANGE_STALES_DESCENDANTS = (
        "changing one parent identity marks transitive descendants stale"
    )


class AlgorithmName(StrEnum):
    ANCHOR_FEDAVG = "ANCHOR_FEDAVG"
    LOCAL_ONLY_REFERENCE = "LOCAL_ONLY_REFERENCE"
    CENTRALIZED_REFERENCE = "CENTRALIZED_REFERENCE"
    SOURCE_CANDIDATE = "SOURCE_CANDIDATE"
    REPRODUCTION = "REPRODUCTION"
    VERIFIER_AWARE_REPRODUCTION = "VERIFIER_AWARE_REPRODUCTION"
    IRRELEVANT_SOURCE_IMPROVEMENT = "IRRELEVANT_SOURCE_IMPROVEMENT"
    GENERIC_HARD_SUPPORTED_EXAMPLES = "GENERIC_HARD_SUPPORTED_EXAMPLES"
    CERTIFIED_ENSEMBLE_ANCHOR = "CERTIFIED_ENSEMBLE_ANCHOR"
    CERTIFIED_ENSEMBLE_POST_REFERENCE = "CERTIFIED_ENSEMBLE_POST_REFERENCE"
    FEDAVG_REFERENCE = "FEDAVG_REFERENCE"
    SECURE_CONTINUAL_ASSESSMENT = "SECURE_CONTINUAL_ASSESSMENT"
    RECOVERY_AFTER_SOURCE_ADMISSION = "RECOVERY_AFTER_SOURCE_ADMISSION"
    DENSITY_CLUSTER_TRIMMED_MEAN = "DENSITY_CLUSTER_TRIMMED_MEAN"
    ANCHOR_ROUND_CALIBRATION = "ANCHOR_ROUND_CALIBRATION"
    UPDATE_RECONSTRUCTION_FILTER = "UPDATE_RECONSTRUCTION_FILTER"
    KRUM_REFERENCE = "KRUM_REFERENCE"


class RuntimeComponentName(StrEnum):
    DOCTOR = "doctor"
    ANCHOR_TRAINING = "anchor_training"
    REPORTING = "reporting"
    CREATING_REPORT = "report"
    PREPROCESSING = "preprocessing"
    DATASET_PREPARATION = "dataset_preparation"
    EXECUTION = "execution"
    ARTIFACTS = "artifacts"
    SCIENTIFIC_CELL_PHASE = "scientific_cell_phase"
    FINAL_EXPORT_VERIFICATION = "final_export_verification"


class EnvironmentComponent(StrEnum):
    GPU_AVAILABILITY = "gpu_availability"
    UNRAR_VERSION = "unrar_version"
    REPOSITORY_LAYOUT = "repository_layout"


class RepositoryRootName(StrEnum):
    SOURCE = "source-root"
    TESTS = "tests-root"
    RAW_DATA = "raw-data-root"
    MANUSCRIPT_RESULTS = "manuscript-results-root"


class EnvironmentExpectation(StrEnum):
    AVAILABLE = "available"
    CONFIGURED_SOURCE_ROOT_EXISTS = "configured source root exists"
    CONFIGURED_TESTS_ROOT_EXISTS = "configured tests root exists"
    CONFIGURED_RAW_DATA_ROOT_EXISTS = "configured raw data root exists"
    CONFIGURED_MANUSCRIPT_RESULTS_ROOT_EXISTS = "configured manuscript results root exists"


class EnvironmentObservation(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_INSTALLED = "not installed"
    MISSING = "missing"


class CublasWorkspaceConfig(StrEnum):
    REFERENCE = ":4096:8"


class Fp32PrecisionMode(StrEnum):
    IEEE = "ieee"


class NBaiotTriggerFeature(StrEnum):
    MI_DIR_WEIGHT = "MI_dir_L0.1_weight"
    H_WEIGHT = "H_L0.1_weight"
    HH_MAGNITUDE = "HH_L0.1_magnitude"
    HPHP_MEAN = "HpHp_L0.1_mean"


class ReviewPanelProfile(StrEnum):
    CLIENT_REVIEW = "Client Review"
    SECURE_CONTINUAL_ASSESSMENT = "Secure Continual Assessment"
    INDEPENDENT_LOCAL_REFERENCE = "Independent Local Reference"


class MetricObservationKey(StrEnum):
    EVIDENCE_ARRIVAL_CYCLE = "evidence-arrival-cycle"
    TARGET_ROW_IDS = "target-row-ids"
    DEFINED_DOMAIN_COUNT = "defined-domain-count"
    DIAGNOSTIC_MARKER_VALUE = "diagnostic-marker-value"
    DIAGNOSTIC_MARKER_INSUFFICIENT = "diagnostic-marker-insufficient"
    FEATURE_SHIFT_COUNT = "feature-shift-count"
    FEATURE_SHIFT_SIGN = "feature-shift-sign"
    QUANTITY_SKEW_CAP = "quantity-skew-cap"
    PROPOSAL_ORACLE_LABEL = "proposal-oracle-label"
    SUPPORTED_MACRO_F1_DROP = "supported-macro-f1-drop"
    PARAMETER_SIMILARITY_COMMITTED_ROWS = "parameter-similarity-committed-rows"
    PARAMETER_SIMILARITY_CERTIFIED_ROWS = "parameter-similarity-certified-rows"
    KRUM_N3_F1_INVALID = "krum-n3-f1-invalid"
    CAPABILITY_CONTRACT_GRANULARITY_BROAD_CERTIFIED_ROWS = (
        "capability-contract-granularity-broad-certified-rows"
    )
    ROOT_CAUSE_A_TARGET_F1 = "root-cause-a-target-f1"
    ROOT_CAUSE_B_TARGET_F1 = "root-cause-b-target-f1"


class ReportCellLiteral(StrEnum):
    NOT_AVAILABLE = "NA"
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    NONE = "none"


class SeedDerivationLabel(StrEnum):
    DATA_SPLIT = "DATA_SPLIT"
    DOMAIN_PARTITION = "DOMAIN_PARTITION"
    MODEL_INITIALIZATION = "MODEL_INITIALIZATION"
    CLIENT_SAMPLING = "CLIENT_SAMPLING"
    SOURCE_SELECTION = "SOURCE_SELECTION"
    SOURCE_TRAINING = "SOURCE_TRAINING"
    ATTACK_GENERATION = "ATTACK_GENERATION"
    SCREEN_DOMAIN_ORDER = "SCREEN_DOMAIN_ORDER"
    SCREEN_FOLD = "SCREEN_FOLD"
    REPRODUCER_ORDER = "REPRODUCER_ORDER"
    VERIFIER_ASSIGNMENT = "VERIFIER_ASSIGNMENT"
    BYZANTINE_SELECTION = "BYZANTINE_SELECTION"
    LOCAL_TRAINING = "LOCAL_TRAINING"
    COMMITTEE_DRAW = "COMMITTEE_DRAW"
    HETEROGENEITY = "HETEROGENEITY"
    SCREEN_FOLD_SEED = "SCREEN_FOLD_SEED"
    ATTACK_GENERATION_SEED = "ATTACK_GENERATION_SEED"
    HETEROGENEITY_SEED = "HETEROGENEITY_SEED"
    REPRODUCER_ORDER_SEED = "REPRODUCER_ORDER_SEED"
    ANCHOR_CLIENT_DROPOUT = "ANCHOR_CLIENT_DROPOUT"
    LOCAL_TRAINING_JOB = "LOCAL_TRAINING_JOB"
    LOCAL_TRAINING_BATCH_ORDER = "LOCAL_TRAINING_BATCH_ORDER"
    REPLAY_CAP_SELECTION = "REPLAY_CAP_SELECTION"
    CAPABILITY_ROOT_CAUSE = "CAPABILITY_ROOT_CAUSE"
    HETEROGENEITY_FEATURE_ORDER = "HETEROGENEITY_FEATURE_ORDER"
    HETEROGENEITY_FEATURE_SIGN = "HETEROGENEITY_FEATURE_SIGN"
    PSEUDO_DOMAIN_HASH = "CIC_IOT_2023_PSEUDO_DOMAIN"
    DATASET_MANIFEST = "CICIOT2023_DATASET_MANIFEST_V1"
    CAPABILITY_CONTRACT_IDENTITY = "FedSIRA|capability_contract_identity"
    SOURCE_SELECTION_SEED = "SOURCE_SELECTION_SEED"
    SCREEN_DOMAIN_ORDER_SEED = "SCREEN_DOMAIN_ORDER_SEED"
    REPRODUCTION_COMMITMENT = "REPRODUCTION_COMMITMENT"
    COMMITMENT_HASH = "COMMITMENT_HASH"
    VERIFIER_ASSIGNMENT_NAMESPACE = "VERIFIER_ASSIGNMENT_NAMESPACE"
    BYZANTINE_VERIFIER_SELECTION = "BYZANTINE_VERIFIER_SELECTION"
    LOCAL_ONLY_REFERENCE_INIT = "LOCAL_ONLY_REFERENCE_INIT"
    CENTRALIZED_REFERENCE_INIT = "CENTRALIZED_REFERENCE_INIT"
    CERTIFIED_ENSEMBLE_GROUP_INIT = "CERTIFIED_ENSEMBLE_GROUP_INIT"
    VERIFIER_ROW_SEED = "VERIFIER_ROW_SEED"


class ResolvedCoreDecisionToken(StrEnum):
    PROPOSAL_ASSISTED = "proposal-assisted"
    CANDIDATE_FREE = "candidate-free"
    PLURALITY = "plurality"
    SINGLE_REPRODUCTION = "single-reproduction"
    EXTERNALLY_VERIFIED = "externally-verified"
    UNVERIFIED_ROW = "unverified-row"


class EnvironmentVariableName(StrEnum):
    CUBLAS_WORKSPACE_CONFIG = "CUBLAS_WORKSPACE_CONFIG"


class StructuredLogField(StrEnum):
    TIMESTAMP = "timestamp"
    LEVEL = "level"
    COMPONENT = "component"
    MESSAGE = "message"


class ReportColumnName(StrEnum):
    ADJUSTED_P = "adjusted_p"
    ADJUSTED_P_VALUE = "adjusted_p_value"
    ADMISSION_DORMANCY = "admission_dormancy"
    ADMISSION_STATE = "admission_state"
    AGGREGATION_SYNTHESIS = "aggregation_synthesis"
    AGGREGATION_UNIT = "aggregation_unit"
    ALPHA = "alpha"
    ARCHITECTURE = "architecture"
    ASR_DIFFERENCE_VS_FEDSIRA = "asr_difference_vs_fedsira"
    ASR_OR_MALICIOUS_ADMISSION = "asr_or_malicious_admission"
    ASSIGNMENT_SECONDS = "assignment_seconds"
    BATCH_SIZE = "batch_size"
    BENIGN_FALSE_ALARM_RATE_INCREASE = "benign_false_alarm_rate_increase"
    BENIGN_FPR_INCREASE = "benign_fpr_increase"
    BENIGN_FPR_MARGIN = "benign_fpr_margin"
    BOUND_FAMILY = "bound_family"
    BOUND_STATUS = "bound_status"
    BOUNDARY_FAMILY = "boundary_family"
    DISTINCT_CLASS_COUNT = "canonical_class_count"
    CERTIFIED_ROW_REQUIREMENT = "certified_row_requirement"
    CERTIFIED_YIELD = "certified_yield"
    CHECKPOINT_RULE = "checkpoint_rule"
    CI_METHOD = "ci_method"
    CLAIM_FAMILY = "claim_family"
    CLASS = "class"
    CLEAN_ORACLE_ERROR = "clean_oracle_error"
    COMMUNICATION_BYTES = "communication_bytes"
    COMPARATOR = "comparator"
    COMPARISON = "comparison"
    COMPARISON_FAMILY = "comparison_family"
    COMPLETE_SEED_COUNT = "complete_seed_count"
    COMPLETE_SEEDS = "complete_seeds"
    COMPROMISED_COUNT = "compromised_count"
    CONDITION = "condition"
    CONFIDENCE_INTERVAL_95 = "confidence_interval_95"
    CORE_ACTION = "core_action"
    DATA_ROLES = "data_roles"
    DATASET = "dataset"
    DEVICE_TYPE = "device_type"
    DIFFERENCE_FROM_FULL_REFERENCE = "difference_from_full_reference"
    DIRECTION = "direction"
    DOMAIN_ID = "domain_id"
    DOMAIN_PROXY_COUNT = "domain_proxy_count"
    DORMANT_RATE = "dormant_rate"
    DOWNSTREAM_ROLE = "downstream_role"
    EFFECT_THRESHOLD = "effect_threshold"
    EPOCHS_OR_ROUNDS = "epochs_or_rounds"
    EVIDENCE_MINIMUM = "evidence_minimum"
    EVIDENCE_MINIMUM_RULE = "evidence_minimum_rule"
    EXPERIMENT = "experiment"
    EXTERNAL_VERIFICATION = "external_verification"
    F_R = "f_R"
    F_V = "f_V"
    FAMILY = "family"
    FINAL_COMPARISON_STATE = "final_comparison_state"
    FINAL_GATE_ELIGIBILITY = "final_gate_eligibility"
    GPU_SECONDS = "gpu_seconds"
    GRADIENT_CLIP = "gradient_clip"
    HOLM_P = "holm_p"
    HOST_RSS = "host_rss"
    IMPLEMENTATION_STATUS = "implementation_status"
    INDEPENDENT_RETRAINING_COUNT = "independent_retraining_count"
    INITIALIZATION = "initialization"
    KRUM_N = "krum_n"
    KRUM_NEAREST_NEIGHBOR_COUNT = "krum_nearest_neighbor_count"
    LEARNING_RATE = "learning_rate"
    LEGITIMATE_ADMISSION = "legitimate_admission"
    LIVENESS_SAFETY_CONSTRAINT = "liveness_safety_constraint"
    LOGICAL_EVIDENCE_CYCLE = "logical_evidence_cycle"
    LOSS = "loss"
    MALICIOUS_ADMISSION = "malicious_admission"
    MARGIN = "margin"
    MASTER_SEED = "master_seed"
    MATERIALITY_DIRECTION = "materiality_direction"
    MATERIALITY_PASS = "materiality_pass"
    MATERIALITY_THRESHOLD = "materiality_threshold"
    MATERIALIZED_ROWS = "materialized_rows"
    MATHEMATICAL_ORIENTATION = "mathematical_orientation"
    MEAN_DIFFERENCE = "mean_difference"
    MEAN_PAIRED_DIFFERENCE = "mean_paired_difference"
    MEAN_VALUE = "mean_value"
    MECHANISM = "mechanism"
    MECHANISM_FAMILY = "mechanism_family"
    MEDIAN_DIFFERENCE = "median_difference"
    METHOD = "method"
    METHODS = "methods"
    METRIC = "metric"
    MULTIPLICITY_FAMILY = "multiplicity_family"
    N_PAIRS = "n_pairs"
    NOMINAL_RUN_COUNT = "nominal_run_count"
    OBSERVATION_COUNT = "observation_count"
    OBSERVED_OUTCOME = "observed_outcome"
    OPTIMIZER = "optimizer"
    PAIRED_DZ = "paired_dz"
    PAIRED_EFFECT_VS_FEDSIRA = "paired_effect_vs_fedsira"
    PANEL_SIZE = "panel_size"
    PEAK_GPU_MEMORY = "peak_gpu_memory"
    POSITIVE_THRESHOLD = "positive_threshold"
    POST_EVIDENCE_WALL_CLOCK = "post_evidence_wall_clock"
    POST_PRODUCTION_ASR = "post_production_asr"
    PREDECLARED_COMPARATOR = "predeclared_comparator"
    PREPARED_VIEW_DIGEST = "prepared_view_digest"
    PREREQUISITE = "prerequisite"
    PRIMARY_MATERIAL_EFFECT = "primary_material_effect"
    PRIMARY_METRIC = "primary_metric"
    PRIMARY_METRICS = "primary_metrics"
    PRIMARY_SECONDARY_ROLE = "primary_secondary_role"
    PRODUCTION_OBJECT = "production_object"
    PROFILE = "profile"
    PROXY_SEMANTICS = "proxy_semantics"
    RAW_P = "raw_p"
    REGULARIZERS = "regularizers"
    REPETITION = "repetition"
    REPORT_TEST_ROWS = "report_test_rows"
    REPRODUCTION_ELIGIBILITY = "reproduction_eligibility"
    REPRODUCTION_SECONDS = "reproduction_seconds"
    RETAINED_FEATURE_COUNT = "retained_feature_count"
    ROLE_TARGET_COUNTS = "role_target_counts"
    SCENARIO = "scenario"
    SCENARIOS_OR_VARIANTS = "scenarios_or_variants"
    SCOPE = "scope"
    SCOPE_BOUNDARY = "scope_boundary"
    SCOPE_LABEL = "scope_label"
    SEEDS = "seeds"
    SIDEDNESS = "sidedness"
    SOURCE_ARTIFACT_DEPLOYED = "source_artifact_deployed"
    SOURCE_EXCLUSION_GATE_OUTCOME = "source_exclusion_gate_outcome"
    SOURCE_IDENTIFIER = "source_identifier"
    SPLIT_REPLAY_SEMANTICS = "split_replay_semantics"
    STAGE = "stage"
    STATE = "state"
    STATISTICAL_PASS = "statistical_pass"
    STORAGE_BYTES = "storage_bytes"
    STRATEGY = "strategy"
    STRENGTH = "strength"
    SUPPORTED_F1_HARM = "supported_f1_harm"
    SUPPORTED_F1_MARGIN = "supported_f1_margin"
    SUPPORTED_HARM = "supported_harm"
    SUPPORTED_MACRO_F1_HARM = "supported_macro_f1_harm"
    SUPPORTED_ROLE_COUNTS = "supported_role_counts"
    SURVIVAL_RULE = "survival_rule"
    SYNTHESIS_SECONDS = "synthesis_seconds"
    T_EVIDENCE = "t_evidence"
    TARGET_AVAILABILITY = "target_availability"
    TARGET_CLASS = "target_class"
    TARGET_F1 = "target_f1"
    TARGET_F1_95_CI = "target_f1_95_ci"
    TARGET_F1_MEAN = "target_f1_mean"
    TARGET_F1_OR_GAIN = "target_f1_or_gain"
    TARGET_HOLDERS = "target_holders"
    TARGET_NONINFERIORITY_PASS = "target_noninferiority_pass"
    TARGET_THRESHOLD = "target_threshold"
    TARGETED_MECHANISM = "targeted_mechanism"
    TERMINAL_STATE = "terminal_state"
    TEST = "test"
    TEST_KIND = "test_kind"
    TRAINING_BUDGET = "training_budget"
    TRANSMISSIONS = "transmissions"
    TUNING_DATA = "tuning_data"
    UNDEFINED_RULE = "undefined_rule"
    VALUE = "value"
    VARIANT = "variant"
    VERIFICATION_SECONDS = "verification_seconds"
    VERIFIER_ELIGIBILITY = "verifier_eligibility"
    WORST_DOMAIN_F1 = "worst_domain_f1"
    WORST_DOMAIN_TARGET_F1 = "worst_domain_target_f1"


class DelayPhaseMetric(StrEnum):
    ASSIGNMENT_SECONDS = "assignment-seconds"
    REPRODUCE_SECONDS = "reproduce-seconds"
    VERIFY_SECONDS = "verify-seconds"
    SYNTHESIZE_SECONDS = "synthesize-seconds"


class FigureAxisName(StrEnum):
    LOGICAL_EVIDENCE_CYCLE = "logical evidence cycle"
    FRACTION_OF_SEED_INSTANCES = "fraction of seed instances"
    COMPROMISED_REPRODUCER_COUNT = "compromised reproducer count"
    COMPROMISED_VERIFIER_COUNT = "compromised verifier count"
    MALICIOUS_ADMISSION_RATE = "malicious admission rate"
    LEGITIMATE_ADMISSION_RATE = "legitimate admission rate"
    ATTACK_SUCCESS_RATE = "attack success rate"
    CORRUPTION_CONFOUND_STRENGTH = "corruption/confound strength"
    CLEAN_ORACLE_TARGET_F1_DIFFERENCE = "clean-oracle target-F1 difference"
    ADMISSION_RATE_UNDER_CORRUPTED_EVIDENCE = "admission rate under corrupted operational evidence"
    CAPABILITY_CONTRACT_GRANULARITY = "Capability Contract granularity"
    FALSE_SAME_CAPABILITY_CERTIFICATION_RATE = "false same-capability certification rate"
    TARGET_F1 = "target F1"
    HETEROGENEITY_REGIME = "heterogeneity regime"
    WORST_DOMAIN_TARGET_F1 = "worst-domain target F1"
    POST_PRODUCTION_ASR = "post-production ASR (lower is better)"
    POST_EVIDENCE_WALL_CLOCK_SECONDS = "post-evidence wall-clock seconds"
    PRIMARY_MATERIAL_EFFECT_OVER_THRESHOLD = "primary material effect / material threshold"
    MECHANISM = "mechanism"
    TARGET_F1_PAIRED_EFFECT_VS_COMPARATOR = "target-F1 paired effect vs predeclared comparator"
    METHOD_PER_SECONDARY_SCENARIO = "method / secondary scenario"


class FigureLegendLabel(StrEnum):
    TARGET_F1_THRESHOLD = "target-F1 threshold"
    ASSIGNMENT = "assignment"
    REPRODUCE = "reproduce"
    VERIFY = "verify"
    SYNTHESIZE = "synthesize"


class FigurePanelTitle(StrEnum):
    MALICIOUS_ADMISSION = "malicious admission"
    ATTACK_SUCCESS_RATE = "attack success rate"
    COMPROMISED_REPRODUCER_BOUNDARY_ASR = "Compromised-Reproducer Boundary — ASR"
    FALSE_POSITIVE = "false positive"
    FALSE_NEGATIVE = "false negative"
    COMPROMISED_VERIFIER_BOUNDARY_FALSE_POSITIVE_MODE = (
        "Compromised-Verifier Boundary — false-positive mode"
    )
    COMPROMISED_VERIFIER_BOUNDARY_FALSE_NEGATIVE_MODE = (
        "Compromised-Verifier Boundary — false-negative mode"
    )
    CLEAN_ORACLE = "clean oracle"
    ADMISSION = "admission"
    SHARED_EPISTEMIC_FAILURE_CLEAN_ORACLE = "Shared Epistemic Failure — clean oracle"
    SHARED_EPISTEMIC_FAILURE_ADMISSION = "Shared Epistemic Failure — admission"
    FALSE_EQUIVALENCE = "false equivalence"
    ROOT_CAUSE = "root cause"
    CAPABILITY_GRANULARITY_BOUNDARY_FALSE_EQUIVALENCE = (
        "Capability-Granularity Boundary — false equivalence"
    )
    CAPABILITY_GRANULARITY_BOUNDARY_ROOT_CAUSE_TARGET_F1 = (
        "Capability-Granularity Boundary — per-root-cause target F1"
    )
    LEGITIMATE_ADMISSION = "legitimate admission"
    WORST_DOMAIN_TARGET_F1 = "worst-domain target F1"
    HETEROGENEITY_SYNTHESIS_BOUNDARY_LEGITIMATE_ADMISSION = (
        "Heterogeneity Synthesis Boundary — legitimate admission"
    )
    HETEROGENEITY_SYNTHESIS_BOUNDARY_WORST_DOMAIN_TARGET_F1 = (
        "Heterogeneity Synthesis Boundary — worst-domain target F1"
    )


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
    PERMANENT_SINGLETON_ADMISSION = "permanent-singleton-admission"
    VERIFIER_ABSTENTION_RATE = "verifier-abstention-rate"
    REPRODUCTION_ABSTENTION_RATE = "reproduction-abstention-rate"
    DEFINED_DOMAIN_FRACTION = "defined-domain-fraction"
    TERMINAL_STATE = "terminal-state"
    ACCURACY = "accuracy"
    MACRO_F1 = "macro-f1"
    WEIGHTED_F1 = "weighted-f1"
    BALANCED_ACCURACY = "balanced-accuracy"
    TARGET_F1_GAIN = "target-f1-gain"
    P10_DOMAIN_TARGET_F1 = "p10-domain-target-f1"
    DOMAIN_DISPARITY = "domain-disparity"
    DOMAIN_IQR = "domain-iqr"
    COEFFICIENT_OF_VARIATION = "coefficient-of-variation"
    EQUAL_WEIGHT_DOMAIN_MEAN_TARGET_F1 = "equal-weight-domain-mean-target-f1"


class OpeningMode(StrEnum):
    PROPOSAL_ASSISTED = "Proposal-Assisted"
    CANDIDATE_FREE = "Candidate-Free"


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


class HeterogeneityRegime(StrEnum):
    NATURAL = "Natural"
    QUANTITY_SKEW = "Quantity Skew"
    FEATURE_SHIFT_0_5 = "Feature Shift ±0.5"
    FEATURE_SHIFT_1_0 = "Feature Shift ±1.0"


class SecondaryScenario(StrEnum):
    LEGITIMATE_BACKDOOR_MALWARE_CAPABILITY = "Legitimate Backdoor-Malware Capability"
    ONE_BYZANTINE_SOURCE_COPY_REPRODUCER = "One Byzantine Source-Copy Reproducer"


class BaselineIdentity(StrEnum):
    LOCAL_ONLY_REFERENCE = "Local-Only Reference"
    CENTRALIZED_REFERENCE = "Centralized Reference"
    FEDAVG_REFERENCE = "FedAvg Reference"
    CLIENT_REVIEW_WITH_DIRECT_SOURCE_ADMISSION = "Client Review with Direct Source Admission"
    CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN = "Client Review then One Independent Retrain"
    ONE_INDEPENDENT_RETRAIN = "One Independent Retrain"
    CANDIDATE_FREE_FULL_PATH = "Candidate-Free Full Path"
    MULTIPLE_RETRAINS_WITH_DIRECT_KRUM = "Multiple Retrains with Direct Krum"
    THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE = "Three-Row Coordinate-Median Alternative"
    MULTIPLE_MODEL_CERTIFIED_ENSEMBLE = "Multiple-Model Certified Ensemble"
    INDEPENDENT_LOCAL_REFERENCE_WITH_SOURCE_ADMISSION = (
        "Independent Local Reference with Source Admission"
    )
    UPDATE_RECONSTRUCTION_FILTER = "Update Reconstruction Filter"
    DENSITY_CLUSTER_TRIMMED_MEAN = "Density-Cluster Trimmed Mean"
    SECURE_CONTINUAL_ASSESSMENT_REFERENCE = "Secure Continual Assessment Reference"
    RECOVERY_AFTER_SOURCE_ADMISSION = "Recovery after Source Admission"
    SOURCE_UPDATE_SANITIZATION_REFERENCE = "Source-Update Sanitization Reference"
    KRUM_ROBUST_AGGREGATION_REFERENCE = "Krum Robust Aggregation Reference"


class EvidenceArrivalSchedule(StrEnum):
    PERMANENT_SINGLETON = "Permanent Singleton"
    ONE_HONEST_HOLDER = "One Honest Holder"
    GRADUAL_TO_QUORUM = "Gradual to Quorum"
    IMMEDIATE_QUORUM = "Immediate Quorum"
