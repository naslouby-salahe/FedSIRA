import hashlib
import re
from pathlib import Path

from fedsira.artifacts.store import ArtifactSlot
from fedsira.domain.enums import (
    ArtifactFamily,
    ArtifactFamilyDirectoryToken,
    ArtifactFileToken,
    ArtifactPathScope,
    DatasetId,
    ExperimentName,
    WorkspaceDirectoryToken,
    WorkspaceFileToken,
)
from fedsira.domain.types import (
    ArtifactInstanceName,
    ArtifactInstanceToken,
    FramingField,
    MasterSeed,
    MethodName,
    RepetitionIndex,
)
from fedsira.runtime import current_application_context, framed_bytes


def execution_workspace_root() -> Path:
    return Path(
        current_application_context().scientific_config.execution.repository_layout.execution_workspace
    )


def manuscript_results_root() -> Path:
    return Path(
        current_application_context().scientific_config.execution.repository_layout.manuscript_results
    )


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
        ArtifactFamily.TABLE_FIGURE_SOURCE_DATA,
    )
)
RESULT_FAMILIES: frozenset[ArtifactFamily] = frozenset((ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT,))

ARTIFACT_FAMILY_DIRECTORY_TOKENS: tuple[
    tuple[ArtifactFamily, ArtifactFamilyDirectoryToken], ...
] = (
    (ArtifactFamily.RAW_DATASET_IDENTITY, ArtifactFamilyDirectoryToken.RAW_DATASET_IDENTITY),
    (ArtifactFamily.DATASET_MANIFEST, ArtifactFamilyDirectoryToken.DATASET_MANIFEST),
    (
        ArtifactFamily.ROLE_SPLIT_SAMPLE_MANIFEST,
        ArtifactFamilyDirectoryToken.ROLE_SPLIT_SAMPLE_MANIFEST,
    ),
    (ArtifactFamily.SCALER, ArtifactFamilyDirectoryToken.SCALER),
    (ArtifactFamily.PREPARED_ROLE_VIEW, ArtifactFamilyDirectoryToken.PREPARED_ROLE_VIEW),
    (ArtifactFamily.ANCHOR_CHECKPOINT, ArtifactFamilyDirectoryToken.ANCHOR_CHECKPOINT),
    (
        ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT,
        ArtifactFamilyDirectoryToken.SOURCE_CANDIDATE_CHECKPOINT,
    ),
    (ArtifactFamily.REPRODUCTION_CHECKPOINT, ArtifactFamilyDirectoryToken.REPRODUCTION_CHECKPOINT),
    (ArtifactFamily.BASELINE_CHECKPOINT, ArtifactFamilyDirectoryToken.BASELINE_CHECKPOINT),
    (ArtifactFamily.MODEL_SCORE_ARTIFACT, ArtifactFamilyDirectoryToken.MODEL_SCORE_ARTIFACT),
    (
        ArtifactFamily.SCREEN_MATCHING_ARTIFACT,
        ArtifactFamilyDirectoryToken.SCREEN_MATCHING_ARTIFACT,
    ),
    (
        ArtifactFamily.BASELINE_CALIBRATION_ARTIFACT,
        ArtifactFamilyDirectoryToken.BASELINE_CALIBRATION_ARTIFACT,
    ),
    (
        ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION,
        ArtifactFamilyDirectoryToken.FIXED_PROTOCOL_CONFIGURATION,
    ),
    (
        ArtifactFamily.VERIFIER_ASSIGNMENT_REPORT,
        ArtifactFamilyDirectoryToken.VERIFIER_ASSIGNMENT_REPORT,
    ),
    (
        ArtifactFamily.REPRODUCTION_CERTIFICATE,
        ArtifactFamilyDirectoryToken.REPRODUCTION_CERTIFICATE,
    ),
    (ArtifactFamily.KRUM_SYNTHESIZED_UPDATE, ArtifactFamilyDirectoryToken.KRUM_SYNTHESIZED_UPDATE),
    (ArtifactFamily.FINAL_GATE_DECISION, ArtifactFamilyDirectoryToken.FINAL_GATE_DECISION),
    (
        ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT,
        ArtifactFamilyDirectoryToken.DOMAIN_SEED_METRIC_ARTIFACT,
    ),
    (
        ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT,
        ArtifactFamilyDirectoryToken.STATISTICAL_COMPARISON_ARTIFACT,
    ),
    (
        ArtifactFamily.TABLE_FIGURE_SOURCE_DATA,
        ArtifactFamilyDirectoryToken.TABLE_FIGURE_SOURCE_DATA,
    ),
    (
        ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT,
        ArtifactFamilyDirectoryToken.TABLE_FIGURE_REPORT_EXPORT,
    ),
)


def artifact_family_directory_token(family: ArtifactFamily) -> ArtifactFamilyDirectoryToken:
    for candidate, token in ARTIFACT_FAMILY_DIRECTORY_TOKENS:
        if candidate is family:
            return token
    raise ValueError(f"artifact family has no directory token: {family}")


def preprocessing_root() -> Path:
    return execution_workspace_root() / WorkspaceDirectoryToken.PREPROCESSING


def preprocessing_metadata_root() -> Path:
    return preprocessing_root() / WorkspaceDirectoryToken.METADATA


def preprocessing_extraction_cache_root(execution_workspace: Path) -> Path:
    return (
        execution_workspace / WorkspaceDirectoryToken.CACHE / WorkspaceDirectoryToken.PREPROCESSING
    )


def artifact_staging_root() -> Path:
    return (
        execution_workspace_root() / WorkspaceDirectoryToken.CACHE / WorkspaceDirectoryToken.STAGING
    )


def artifact_publication_root() -> Path:
    return execution_workspace_root() / WorkspaceDirectoryToken.ARTIFACTS


def artifact_log_path() -> Path:
    return artifact_publication_root() / WorkspaceDirectoryToken.LOGS / ArtifactFileToken.LOG_FILE


def execution_outputs_root() -> Path:
    return execution_workspace_root() / WorkspaceDirectoryToken.EXPERIMENTS


def prepared_evidence_root(dataset: DatasetId) -> Path:
    return preprocessing_root() / WorkspaceDirectoryToken.PREPARED / dataset


def prepared_feature_root() -> Path:
    return preprocessing_root() / WorkspaceDirectoryToken.FEATURES


def preprocessing_log_path() -> Path:
    return (
        preprocessing_root() / WorkspaceDirectoryToken.LOGS / WorkspaceFileToken.PREPROCESSING_LOG
    )


def smoke_record_path() -> Path:
    return (
        preprocessing_root() / WorkspaceDirectoryToken.VALIDATION / WorkspaceFileToken.SMOKE_RECORD
    )


def experiment_execution_root(experiment: ExperimentName) -> Path:
    return execution_workspace_root() / WorkspaceDirectoryToken.EXPERIMENTS / experiment


def experiment_repetition_telemetry_root(
    experiment: ExperimentName,
    method: MethodName,
    master_seed: MasterSeed,
    repetition: RepetitionIndex,
) -> Path:
    return (
        experiment_execution_root(experiment)
        / WorkspaceDirectoryToken.TELEMETRY
        / WorkspaceDirectoryToken.REPETITIONS
        / method
        / str(master_seed)
        / str(repetition)
    )


def experiment_log_path(experiment: ExperimentName) -> Path:
    return (
        experiment_execution_root(experiment)
        / WorkspaceDirectoryToken.LOGS
        / WorkspaceFileToken.EXPERIMENT_LOG
    )


def experiment_result_root(experiment: ExperimentName) -> Path:
    return manuscript_results_root() / WorkspaceDirectoryToken.EXPERIMENTS / experiment


def manuscript_tables_root(root: Path) -> Path:
    return root / WorkspaceDirectoryToken.TABLES / WorkspaceDirectoryToken.MAIN


def manuscript_figures_root(root: Path) -> Path:
    return root / WorkspaceDirectoryToken.FIGURES / WorkspaceDirectoryToken.MAIN


def experiment_metrics_root(root: Path) -> Path:
    return root / WorkspaceDirectoryToken.METRICS / WorkspaceDirectoryToken.PRIMARY


def experiment_telemetry_root(root: Path) -> Path:
    return root / WorkspaceDirectoryToken.TELEMETRY


def project_summary_root() -> Path:
    return manuscript_results_root() / WorkspaceDirectoryToken.PROJECT_SUMMARY


def manuscript_reproducibility_root(root: Path) -> Path:
    return root / WorkspaceDirectoryToken.REPRODUCIBILITY / WorkspaceDirectoryToken.EXECUTION


def path_scope_for_family(family: ArtifactFamily) -> ArtifactPathScope:
    if family in PREPROCESSING_FAMILIES:
        return ArtifactPathScope.PREPROCESSING
    if family in PROJECT_ARTIFACT_FAMILIES:
        return ArtifactPathScope.PROJECT_ARTIFACT
    if family in EXPERIMENT_ARTIFACT_FAMILIES:
        return ArtifactPathScope.EXPERIMENT_ARTIFACT
    if family in RESULT_FAMILIES:
        return ArtifactPathScope.MANUSCRIPT_RESULT
    raise ValueError(f"unsupported artifact family: {family}")


def workspace_root_for_family(
    family: ArtifactFamily,
    experiment: ExperimentName | None = None,
) -> Path:
    scope = path_scope_for_family(family)
    if scope is ArtifactPathScope.PREPROCESSING:
        return preprocessing_root()
    if scope is ArtifactPathScope.PROJECT_ARTIFACT:
        return artifact_publication_root()
    if scope is ArtifactPathScope.EXPERIMENT_ARTIFACT:
        if experiment is None:
            raise ValueError(f"artifact family {family} requires an owning experiment name")
        return experiment_execution_root(experiment)
    if experiment is None:
        raise ValueError(f"artifact family {family} requires an owning experiment name")
    return manuscript_results_root() / WorkspaceDirectoryToken.EXPERIMENTS / experiment


def artifact_slot_directory(slot: ArtifactSlot) -> Path:
    return (
        workspace_root_for_family(slot.family, slot.experiment)
        / artifact_family_directory_token(slot.family)
        / slot.instance
    )


def artifact_instance_token(
    instance_name: ArtifactInstanceName, *fields: FramingField
) -> ArtifactInstanceToken:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", instance_name).strip("-").lower()[:80].strip("-")
    digest = hashlib.sha256(framed_bytes(instance_name, *fields)).hexdigest()[:12]
    return f"{slug}-{digest}"
