from pathlib import Path

from fedsira.artifacts.paths import (
    artifact_publication_root,
    execution_outputs_root,
    manuscript_results_root,
    preprocessing_root,
    workspace_root_for_family,
)
from fedsira.domain.enums import ArtifactFamily, ExperimentName

PROBE_EXPERIMENT = ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION


def _report_gate_roots() -> tuple[Path, ...]:
    return (
        preprocessing_root(),
        artifact_publication_root(),
        execution_outputs_root(),
        manuscript_results_root(),
    )


def test_every_artifact_family_is_visible_to_the_report_gate() -> None:
    roots = _report_gate_roots()
    invisible: list[str] = []
    for family in ArtifactFamily:
        workspace = workspace_root_for_family(family, PROBE_EXPERIMENT)
        if not any(workspace.is_relative_to(root) for root in roots):
            invisible.append(f"{family.value} -> {workspace}")
    assert not invisible, f"artifact families outside every verified root: {invisible}"


def test_report_gate_roots_are_distinct_and_ordered_by_scope() -> None:
    roots = _report_gate_roots()
    assert len(set(roots)) == len(roots)


def test_preprocessing_family_workspaces_stay_inside_the_preprocessing_root() -> None:
    root = preprocessing_root()
    for family in (
        ArtifactFamily.RAW_DATASET_IDENTITY,
        ArtifactFamily.DATASET_MANIFEST,
        ArtifactFamily.ROLE_SPLIT_SAMPLE_MANIFEST,
        ArtifactFamily.SCALER,
        ArtifactFamily.PREPARED_ROLE_VIEW,
    ):
        assert workspace_root_for_family(family, PROBE_EXPERIMENT) == root


def test_project_family_workspaces_stay_inside_the_artifact_publication_root() -> None:
    root = artifact_publication_root()
    for family in (
        ArtifactFamily.ANCHOR_CHECKPOINT,
        ArtifactFamily.SOURCE_CANDIDATE_CHECKPOINT,
        ArtifactFamily.REPRODUCTION_CHECKPOINT,
        ArtifactFamily.BASELINE_CHECKPOINT,
        ArtifactFamily.MODEL_SCORE_ARTIFACT,
        ArtifactFamily.SCREEN_MATCHING_ARTIFACT,
        ArtifactFamily.BASELINE_CALIBRATION_ARTIFACT,
        ArtifactFamily.FIXED_PROTOCOL_CONFIGURATION,
    ):
        assert workspace_root_for_family(family, PROBE_EXPERIMENT) == root


def test_result_family_workspaces_stay_inside_the_manuscript_results_root() -> None:
    root = manuscript_results_root()
    assert workspace_root_for_family(
        ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT, PROBE_EXPERIMENT
    ).is_relative_to(root)
