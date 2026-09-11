import pytest

from fedsira.artifacts.paths import (
    execution_workspace_root,
    manuscript_results_root,
    path_scope_for_family,
    workspace_root_for_family,
)
from fedsira.domain.enums import ArtifactFamily, ArtifactPathScope


def test_preprocessing_family_maps_to_execution_workspace_preprocessing() -> None:
    assert path_scope_for_family(ArtifactFamily.SCALER) is ArtifactPathScope.PREPROCESSING
    assert (
        workspace_root_for_family(ArtifactFamily.SCALER)
        == execution_workspace_root() / "preprocessing"
    )


def test_project_artifact_family_maps_to_execution_workspace_artifacts() -> None:
    assert (
        path_scope_for_family(ArtifactFamily.ANCHOR_CHECKPOINT)
        is ArtifactPathScope.PROJECT_ARTIFACT
    )
    assert (
        workspace_root_for_family(ArtifactFamily.ANCHOR_CHECKPOINT)
        == execution_workspace_root() / "artifacts"
    )


def test_experiment_artifact_family_requires_experiment_name() -> None:
    with pytest.raises(ValueError):
        workspace_root_for_family(ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT)


def test_experiment_artifact_family_maps_under_execution_workspace_experiments() -> None:
    root = workspace_root_for_family(ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT, "krum-baseline")
    assert root == execution_workspace_root() / "experiments" / "krum-baseline"


def test_manuscript_result_family_maps_under_manuscript_results_only() -> None:
    root = workspace_root_for_family(ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT, "krum-baseline")
    assert root == manuscript_results_root() / "experiments" / "krum-baseline"
    assert execution_workspace_root() not in root.parents
