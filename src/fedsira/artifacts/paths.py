from pathlib import Path

from fedsira.domain.enums import ArtifactFamily, ArtifactPathScope, DatasetId
from fedsira.domain.records import ExperimentName

OUTPUTS_ROOT = Path("outputs")
RESULTS_ROOT = Path("results")

PREPROCESSING_FAMILIES: frozenset[ArtifactFamily] = frozenset(
    (
        ArtifactFamily.RAW_DATASET_IDENTITY,
        ArtifactFamily.DATASET_MANIFEST,
        ArtifactFamily.ROLE_SPLIT_SAMPLE_MANIFEST,
        ArtifactFamily.SCALER,
        ArtifactFamily.PREPARED_ROLE_VIEW,
    )
)
PROJECT_ARTIFACT_FAMILIES: frozenset[ArtifactFamily] = frozenset(
    (
        ArtifactFamily.ANCHOR_CHECKPOINT,
        ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT,
        ArtifactFamily.REPRODUCTION_CHECKPOINT,
        ArtifactFamily.BASELINE_CHECKPOINT,
        ArtifactFamily.MODEL_SCORE_ARTIFACT,
        ArtifactFamily.SCREEN_MATCHING_ARTIFACT,
        ArtifactFamily.BASELINE_CALIBRATION_ARTIFACT,
        ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION,
    )
)
EXPERIMENT_ARTIFACT_FAMILIES: frozenset[ArtifactFamily] = frozenset(
    (
        ArtifactFamily.VERIFIER_ASSIGNMENT_REPORT,
        ArtifactFamily.REPRODUCTION_CERTIFICATE,
        ArtifactFamily.KRUM_SYNTHESIZED_UPDATE,
        ArtifactFamily.FINAL_GATE_DECISION,
        ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT,
        ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        ArtifactFamily.CLAIM_STATE_ARTIFACT,
        ArtifactFamily.TABLE_FIGURE_SOURCE_DATA,
    )
)
RESULT_FAMILIES: frozenset[ArtifactFamily] = frozenset((ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT,))


def preprocessing_root() -> Path:
    return OUTPUTS_ROOT / "preprocessing"


def preprocessing_metadata_root() -> Path:
    return preprocessing_root() / "metadata"


def prepared_evidence_root(dataset: DatasetId) -> Path:
    return preprocessing_root() / "prepared" / dataset


def prepared_feature_root() -> Path:
    return preprocessing_root() / "features"


def smoke_record_path() -> Path:
    return preprocessing_root() / "validation" / "smoke_record.json"


def path_scope_for_family(family: ArtifactFamily) -> ArtifactPathScope:
    if family in PREPROCESSING_FAMILIES:
        return ArtifactPathScope.PREPROCESSING
    if family in PROJECT_ARTIFACT_FAMILIES:
        return ArtifactPathScope.PROJECT_ARTIFACT
    if family in EXPERIMENT_ARTIFACT_FAMILIES:
        return ArtifactPathScope.EXPERIMENT_ARTIFACT
    if family in RESULT_FAMILIES:
        return ArtifactPathScope.MANUSCRIPT_RESULT
    raise ValueError(f"unsupported artifact family: {family.value}")


def workspace_root_for_family(
    family: ArtifactFamily,
    experiment: ExperimentName | None = None,
) -> Path:
    scope = path_scope_for_family(family)
    if scope is ArtifactPathScope.PREPROCESSING:
        return preprocessing_root()
    if scope is ArtifactPathScope.PROJECT_ARTIFACT:
        return OUTPUTS_ROOT / "artifacts"
    if scope is ArtifactPathScope.EXPERIMENT_ARTIFACT:
        if experiment is None:
            raise ValueError(f"artifact family {family.value} requires an owning experiment name")
        return OUTPUTS_ROOT / "experiments" / experiment
    if experiment is None:
        raise ValueError(f"artifact family {family.value} requires an owning experiment name")
    return RESULTS_ROOT / "experiments" / experiment
