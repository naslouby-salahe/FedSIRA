import hashlib
import re
from pathlib import Path

from fedsira.artifacts.store import ArtifactSlot
from fedsira.domain.enums import ArtifactFamily, ArtifactPathScope, DatasetId
from fedsira.domain.types import (
    ArtifactInstanceToken,
    ExperimentName,
    FramingField,
    MasterSeed,
    MethodName,
    RepetitionIndex,
    TextValue,
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

ARTIFACT_FAMILY_DIRECTORY_TOKENS: tuple[tuple[ArtifactFamily, TextValue], ...] = (
    (ArtifactFamily.RAW_DATASET_IDENTITY, "raw-dataset-identity"),  # TODO: should be enum
    (ArtifactFamily.DATASET_MANIFEST, "dataset-manifest"),  # TODO: should be enum
    (ArtifactFamily.ROLE_SPLIT_SAMPLE_MANIFEST, "role-split-sample-manifest"),  # TODO: should be enum
    (ArtifactFamily.SCALER, "scaler"),  # TODO: should be enum
    (ArtifactFamily.PREPARED_ROLE_VIEW, "prepared-role-view"),  # TODO: should be enum
    (ArtifactFamily.ANCHOR_CHECKPOINT, "anchor-checkpoint"),  # TODO: should be enum
    (ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT, "source-candidate-checkpoint"),  # TODO: should be enum
    (ArtifactFamily.REPRODUCTION_CHECKPOINT, "reproduction-checkpoint"),  # TODO: should be enum
    (ArtifactFamily.BASELINE_CHECKPOINT, "baseline-checkpoint"),  # TODO: should be enum
    (ArtifactFamily.MODEL_SCORE_ARTIFACT, "model-score-artifact"),  # TODO: should be enum
    (ArtifactFamily.SCREEN_MATCHING_ARTIFACT, "screen-matching-artifact"),  # TODO: should be enum
    (ArtifactFamily.BASELINE_CALIBRATION_ARTIFACT, "baseline-calibration-artifact"),  # TODO: should be enum
    (ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION, "fixed-protocol-configuration"),  # TODO: should be enum
    (ArtifactFamily.VERIFIER_ASSIGNMENT_REPORT, "verifier-assignment-report"),  # TODO: should be enum
    (ArtifactFamily.REPRODUCTION_CERTIFICATE, "reproduction-certificate"),  # TODO: should be enum
    (ArtifactFamily.KRUM_SYNTHESIZED_UPDATE, "krum-synthesized-update"),  # TODO: should be enum
    (ArtifactFamily.FINAL_GATE_DECISION, "final-gate-decision"),  # TODO: should be enum
    (ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT, "domain-seed-metric-artifact"),  # TODO: should be enum
    (ArtifactFamily.STATISTICAL_COMPARISON_ARTIFACT, "statistical-comparison-artifact"),  # TODO: should be enum
    (ArtifactFamily.TABLE_FIGURE_SOURCE_DATA, "table-figure-source-data"),  # TODO: should be enum
    (ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT, "table-figure-report-export"),  # TODO: should be enum
)


def artifact_family_directory_token(family: ArtifactFamily) -> TextValue:
    for candidate, token in ARTIFACT_FAMILY_DIRECTORY_TOKENS:
        if candidate is family:
            return token
    raise ValueError(f"artifact family has no directory token: {family.value}")


def preprocessing_root() -> Path:
    return execution_workspace_root() / "preprocessing"


def preprocessing_metadata_root() -> Path:
    return preprocessing_root() / "metadata"


def preprocessing_extraction_cache_root(execution_workspace: Path) -> Path:
    return execution_workspace / "cache" / "preprocessing"


def artifact_staging_root() -> Path:
    return execution_workspace_root() / "cache" / "staging"


def artifact_publication_root() -> Path:
    return execution_workspace_root() / "artifacts"


def artifact_log_path() -> Path:
    return artifact_publication_root() / "logs" / "artifacts.log"


def execution_outputs_root() -> Path:
    return execution_workspace_root() / "experiments"


def prepared_evidence_root(dataset: DatasetId) -> Path:
    return preprocessing_root() / "prepared" / dataset


def prepared_feature_root() -> Path:
    return preprocessing_root() / "features"


def preprocessing_log_path() -> Path:
    return preprocessing_root() / "logs" / "preprocessing.log"


def smoke_record_path() -> Path:
    return preprocessing_root() / "validation" / "smoke_record.json"


def experiment_execution_root(experiment: ExperimentName) -> Path:
    return execution_workspace_root() / "experiments" / experiment


def experiment_repetition_telemetry_root(
    experiment: ExperimentName,
    method: MethodName,
    master_seed: MasterSeed,
    repetition: RepetitionIndex,
) -> Path:
    return (
        experiment_execution_root(experiment)
        / "telemetry"
        / "repetitions"
        / method
        / str(master_seed)
        / str(repetition)
    )


def experiment_log_path(experiment: ExperimentName) -> Path:
    return experiment_execution_root(experiment) / "logs" / "experiment.log"


def experiment_result_root(experiment: ExperimentName) -> Path:
    return manuscript_results_root() / "experiments" / experiment


def manuscript_tables_root(root: Path) -> Path:
    return root / "tables" / "main"


def manuscript_figures_root(root: Path) -> Path:
    return root / "figures" / "main"


def experiment_metrics_root(root: Path) -> Path:
    return root / "metrics" / "primary"


def experiment_telemetry_root(root: Path) -> Path:
    return root / "telemetry"


def project_summary_root() -> Path:
    return manuscript_results_root() / "project_summary"


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
        return artifact_publication_root()
    if scope is ArtifactPathScope.EXPERIMENT_ARTIFACT:
        if experiment is None:
            raise ValueError(f"artifact family {family.value} requires an owning experiment name")
        return experiment_execution_root(experiment)
    if experiment is None:
        raise ValueError(f"artifact family {family.value} requires an owning experiment name")
    return manuscript_results_root() / "experiments" / experiment


def artifact_slot_directory(slot: ArtifactSlot) -> Path:
    return (
        workspace_root_for_family(slot.family, slot.experiment)
        / artifact_family_directory_token(slot.family)
        / slot.instance
    )


def artifact_instance_token(label: TextValue, *fields: FramingField) -> ArtifactInstanceToken:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-").lower()[:80].strip("-")
    digest = hashlib.sha256(framed_bytes(label, *fields)).hexdigest()[:12]
    return f"{slug}-{digest}"
