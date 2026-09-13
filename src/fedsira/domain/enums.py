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


class SeedNamespace(StrEnum): #TODO: to be removed since this will become SeedDerivationLabel enum
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


class ArtifactInstanceToken(StrEnum):
    ROLE_SPLIT = "role-split"
    RESOLVED_CORE = "resolved-fedsira-core"
    COMPARISONS = "comparisons"
    SOURCE_DATA = "source-data"
    REPORT_EXPORT = "report-export"
    SMOKE_INVARIANT = "smoke-invariant"
    SMOKE_PARENT = "smoke-parent"
    SMOKE_DESCENDANT = "smoke-descendant"


class ArtifactDependencyName(StrEnum):
    RAW_DATASET = "raw-dataset"
    PARENT = "parent"


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
