import pytest

from fedsira.domain.enums import ArtifactFamily, ArtifactPathScope
from fedsira.io.paths import (
    OUTPUTS_ROOT,
    RESULTS_ROOT,
    path_scope_for_family,
    workspace_root_for_family,
)


def test_preprocessing_family_maps_to_outputs_preprocessing() -> None:
    assert path_scope_for_family(ArtifactFamily.SCALER) is ArtifactPathScope.PREPROCESSING
    assert workspace_root_for_family(ArtifactFamily.SCALER) == OUTPUTS_ROOT / "preprocessing"


def test_project_artifact_family_maps_to_outputs_artifacts() -> None:
    assert (
        path_scope_for_family(ArtifactFamily.ANCHOR_CHECKPOINT)
        is ArtifactPathScope.PROJECT_ARTIFACT
    )
    assert workspace_root_for_family(ArtifactFamily.ANCHOR_CHECKPOINT) == OUTPUTS_ROOT / "artifacts"


def test_experiment_artifact_family_requires_experiment_name() -> None:
    with pytest.raises(ValueError):
        workspace_root_for_family(ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT)


def test_experiment_artifact_family_maps_under_outputs_experiments() -> None:
    root = workspace_root_for_family(ArtifactFamily.DOMAIN_SEED_METRIC_ARTIFACT, "krum-baseline")
    assert root == OUTPUTS_ROOT / "experiments" / "krum-baseline"


def test_manuscript_result_family_maps_under_results_only() -> None:
    root = workspace_root_for_family(ArtifactFamily.TABLE_FIGURE_REPORT_EXPORT, "krum-baseline")
    assert root == RESULTS_ROOT / "experiments" / "krum-baseline"
    assert OUTPUTS_ROOT not in root.parents
