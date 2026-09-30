from pathlib import Path

import pytest

from fedsira.artifacts.paths import (
    execution_workspace_root,
    manuscript_results_root,
    path_scope_for_family,
    workspace_root_for_family,
)
from fedsira.domain.enums import ArtifactFamily, ArtifactPathScope, ExperimentName


def test_preprocessing_family_maps_to_execution_workspace_preprocessing() -> None:
    assert path_scope_for_family(ArtifactFamily.SCALER) is ArtifactPathScope.PREPROCESSING
    assert (
        workspace_root_for_family(ArtifactFamily.SCALER)
        == execution_workspace_root() / "preprocessing"
    )


def test_execution_workspace_is_repository_anchored_when_cwd_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = execution_workspace_root()
    expected_results = manuscript_results_root()

    monkeypatch.chdir(tmp_path)

    assert execution_workspace_root() == expected
    assert expected.is_absolute()
    assert manuscript_results_root() == expected_results
    assert expected_results.is_absolute()


def test_project_artifact_family_maps_to_execution_workspace_artifacts() -> None:
    assert (
        path_scope_for_family(ArtifactFamily.ANCHOR_CHECKPOINT)
        is ArtifactPathScope.PROJECT_ARTIFACT
    )
    assert (
        workspace_root_for_family(ArtifactFamily.ANCHOR_CHECKPOINT)
        == execution_workspace_root() / "artifacts"
    )


def test_claim_state_artifact_is_a_project_scoped_artifact() -> None:
    assert (
        path_scope_for_family(ArtifactFamily.CLAIM_STATE_ARTIFACT)
        is ArtifactPathScope.PROJECT_ARTIFACT
    )
    assert (
        workspace_root_for_family(ArtifactFamily.CLAIM_STATE_ARTIFACT)
        == execution_workspace_root() / "artifacts"
    )


def test_experiment_artifact_family_requires_experiment_name() -> None:
    with pytest.raises(ValueError):
        workspace_root_for_family(ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT)


def test_experiment_artifact_family_maps_under_execution_workspace_experiments() -> None:
    root = workspace_root_for_family(
        ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT, ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION
    )
    assert (
        root
        == execution_workspace_root()
        / "experiments"
        / ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION
    )


def test_manuscript_result_family_maps_under_manuscript_results_only() -> None:
    root = workspace_root_for_family(
        ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT, ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION
    )
    assert (
        root
        == manuscript_results_root()
        / "experiments"
        / ExperimentName.PRIMARY_CONFIRMATORY_EVALUATION
    )
    assert execution_workspace_root() not in root.parents
