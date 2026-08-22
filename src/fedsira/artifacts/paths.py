from pathlib import Path

from fedsira.domain.enums import ArtifactFamily, ArtifactPathScope
from fedsira.domain.records import ExperimentId

ARTIFACT_FAMILY_PATH_SCOPE: dict[ArtifactFamily, ArtifactPathScope] = {
    ArtifactFamily.RAW_DATASET_IDENTITY: ArtifactPathScope.PREPROCESSING,
    ArtifactFamily.CANONICAL_DATASET_MANIFEST: ArtifactPathScope.PREPROCESSING,
    ArtifactFamily.ROLE_SPLIT_SAMPLE_MANIFEST: ArtifactPathScope.PREPROCESSING,
    ArtifactFamily.SCALER: ArtifactPathScope.PREPROCESSING,
    ArtifactFamily.PREPARED_ROLE_VIEW: ArtifactPathScope.PREPROCESSING,
    ArtifactFamily.ANCHOR_CHECKPOINT: ArtifactPathScope.PROJECT_ARTIFACT,
    ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT: ArtifactPathScope.PROJECT_ARTIFACT,
    ArtifactFamily.REPRODUCTION_CHECKPOINT: ArtifactPathScope.PROJECT_ARTIFACT,
    ArtifactFamily.BASELINE_CHECKPOINT: ArtifactPathScope.PROJECT_ARTIFACT,
    ArtifactFamily.MODEL_SCORE_ARTIFACT: ArtifactPathScope.PROJECT_ARTIFACT,
    ArtifactFamily.SCREEN_MATCHING_ARTIFACT: ArtifactPathScope.PROJECT_ARTIFACT,
    ArtifactFamily.BASELINE_CALIBRATION_ARTIFACT: ArtifactPathScope.PROJECT_ARTIFACT,
    ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION: ArtifactPathScope.PROJECT_ARTIFACT,
    ArtifactFamily.VERIFIER_ASSIGNMENT_REPORT: ArtifactPathScope.EXPERIMENT_ARTIFACT,
    ArtifactFamily.REPRODUCTION_CERTIFICATE: ArtifactPathScope.EXPERIMENT_ARTIFACT,
    ArtifactFamily.KRUM_SYNTHESIZED_UPDATE: ArtifactPathScope.EXPERIMENT_ARTIFACT,
    ArtifactFamily.FINAL_GATE_DECISION: ArtifactPathScope.EXPERIMENT_ARTIFACT,
    ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT: ArtifactPathScope.EXPERIMENT_ARTIFACT,
    ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT: ArtifactPathScope.EXPERIMENT_ARTIFACT,
    ArtifactFamily.CLAIM_STATE_ARTIFACT: ArtifactPathScope.EXPERIMENT_ARTIFACT,
    ArtifactFamily.TABLE_FIGURE_SOURCE_DATA: ArtifactPathScope.EXPERIMENT_ARTIFACT,
    ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT: ArtifactPathScope.MANUSCRIPT_RESULT,
}

OUTPUTS_ROOT = Path("outputs")
RESULTS_ROOT = Path("results")


def path_scope_for_family(family: ArtifactFamily) -> ArtifactPathScope:
    return ARTIFACT_FAMILY_PATH_SCOPE[family]


def workspace_root_for_family(
    family: ArtifactFamily, experiment: ExperimentId | None = None
) -> Path:
    scope = path_scope_for_family(family)
    if scope is ArtifactPathScope.PREPROCESSING:
        return OUTPUTS_ROOT / "preprocessing"
    if scope is ArtifactPathScope.PROJECT_ARTIFACT:
        return OUTPUTS_ROOT / "artifacts"
    if scope is ArtifactPathScope.EXPERIMENT_ARTIFACT:
        if experiment is None:
            raise ValueError(f"artifact family {family.value} requires an owning experiment name")
        return OUTPUTS_ROOT / "experiments" / experiment
    if experiment is None:
        raise ValueError(f"artifact family {family.value} requires an owning experiment name")
    return RESULTS_ROOT / "experiments" / experiment
