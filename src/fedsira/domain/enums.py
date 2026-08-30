from enum import StrEnum


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


class SeedNamespace(StrEnum):
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


class ArtifactLifecycleState(StrEnum):
    STAGING = "Staging"
    COMPLETE = "Complete"
    STALE = "Stale"
    RETIRED = "Retired"


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
    FIXED_PROTOCOL_CONFIGURATION = "Fixed Capability Claim Contract/Krum/protocol configuration"
    VERIFIER_ASSIGNMENT_REPORT = "Verifier assignment/report"
    REPRODUCTION_CERTIFICATE = "Reproduction certificate"
    KRUM_SYNTHESIZED_UPDATE = "Krum synthesized update/model"
    FINAL_GATE_DECISION = "Final-gate evaluation/decision"
    DOMAIN_SEED_METRIC_ARTIFACT = "Domain/seed metric artifact"
    STATISTICAL_COMPARISON_ARTIFACT = "Statistical comparison/gate artifact"
    CLAIM_STATE_ARTIFACT = "Claim-state artifact"
    TABLE_FIGURE_SOURCE_DATA = "Table/figure source data"
    TABLE_FIGURE_REPORT_EXPORT = "Table/figure/report export"


class ArtifactPathScope(StrEnum):
    PREPROCESSING = "preprocessing"
    PROJECT_ARTIFACT = "project_artifact"
    EXPERIMENT_ARTIFACT = "experiment_artifact"
    MANUSCRIPT_RESULT = "manuscript_result"


class ProducerFingerprintFamily(StrEnum):
    RAW_SCHEMA_EXCLUSION_MANIFEST = "raw_schema_exclusion_manifest"
    ROLE_SPLIT_SAMPLE_PREPARED_SCALER = "role_split_sample_prepared_scaler"
    ANCHOR_FEDAVG_CHECKPOINTS = "anchor_fedavg_checkpoints"
    SOURCE_REPRODUCTION_CHECKPOINTS = "source_reproduction_checkpoints"
    BASELINE_CHECKPOINT_CALIBRATION = "baseline_checkpoint_calibration"
    MODEL_SCORES = "model_scores"
    OPENING_VERIFIER_CERTIFICATE_SYNTHESIS_FINAL_GATE = (
        "opening_verifier_certificate_synthesis_final_gate"
    )
    BOUNDARY_TRANSFORMATION = "boundary_transformation"
    METRIC_ARTIFACT = "metric_artifact"
    STATISTICAL_COMPARISON_ARTIFACT = "statistical_comparison_artifact"
    CLAIM_STATE_ARTIFACT = "claim_state_artifact"
    REPORT_SOURCE_EXPORT = "report_source_export"


class ClaimOpeningMode(StrEnum):
    PROPOSAL_ASSISTED = "PROPOSAL_ASSISTED"
    CANDIDATE_FREE = "CANDIDATE_FREE"


class ClaimState(StrEnum):
    CANDIDATE_SCREEN = "Candidate Screen"
    CLAIM_OPEN = "Claim Open"
    REPRODUCTION_PENDING = "Reproduction Pending"
    VERIFICATION_PENDING = "Verification Pending"
    SYNTHESIS_PENDING = "Synthesis Pending"
    ADMITTED = "Admitted"
    DORMANT = "Dormant"
    REJECTED_CLAIM = "Rejected Claim"
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


class VerificationOmissionMarker(StrEnum):
    EXTERNAL_VERIFICATION_NOT_USED = "External Verification Not Used"


class ByzantineVerifierBehavior(StrEnum):
    FALSE_POSITIVE = "False Positive"
    FALSE_NEGATIVE = "False Negative"


class TernaryOutcome(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    ABSTAIN = "ABSTAIN"


class ProvenanceValidationOutcome(StrEnum):
    PARTIAL_OR_STALE_PAYLOAD = "partial_or_stale_payload"
    SCIENTIFIC_CONFIGURATION_MISMATCH = "scientific_configuration_mismatch"
    DATASET_SPLIT_UPSTREAM_MISMATCH = "dataset_split_upstream_mismatch"
    PRODUCER_CODE_RUNTIME_MISMATCH = "producer_code_runtime_mismatch"
    NON_MATERIAL_CHANGE = "non_material_change"


class CoreMethodIdentity(StrEnum):
    RESOLVED_FEDSIRA_CORE = "Resolved FedSIRA Core"
    FULL_PLURALITY_PATH = "Full Plurality Path"
    ZERO_REFERENCE = "zero"
