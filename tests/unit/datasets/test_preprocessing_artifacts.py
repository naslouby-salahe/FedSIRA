from pathlib import Path

import pytest

from fedsira.artifacts.store import read_current_artifact
from fedsira.datasets.common import (
    RawDatasetFileIdentity,
    RawDatasetIdentityPayload,
    ScalerMetadata,
)
from fedsira.datasets.preprocess import publish_raw_dataset_identity, publish_scaler
from fedsira.domain.enums import (
    ArtifactFamily,
    ArtifactFamilyDirectoryToken,
    DatasetId,
)


@pytest.fixture
def isolated_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr("fedsira.datasets.preprocess.REPOSITORY_ROOT", tmp_path)
    return tmp_path


def test_raw_dataset_identity_is_published_per_dataset(isolated_repository: Path) -> None:
    files = (
        RawDatasetFileIdentity(relative_path="DEVICE/part.csv", file_sha256="a" * 64),
        RawDatasetFileIdentity(relative_path="DEVICE/other.csv", file_sha256="b" * 64),
    )
    reused = publish_raw_dataset_identity(DatasetId.N_BAIOT, files, "c" * 64)
    assert reused is False

    current = read_current_artifact(
        isolated_repository
        / "outputs"
        / "preprocessing"
        / ArtifactFamilyDirectoryToken.RAW_DATASET_IDENTITY
        / str(DatasetId.N_BAIOT)
    )
    assert current is not None
    manifest, payload = current
    assert manifest.family is ArtifactFamily.RAW_DATASET_IDENTITY
    assert manifest.slot.instance == DatasetId.N_BAIOT
    restored = RawDatasetIdentityPayload.model_validate_json(payload)
    assert restored.dataset is DatasetId.N_BAIOT
    assert restored.files == files


def test_raw_dataset_identity_reuses_an_identical_publication(isolated_repository: Path) -> None:
    files = (RawDatasetFileIdentity(relative_path="DEVICE/part.csv", file_sha256="a" * 64),)
    assert publish_raw_dataset_identity(DatasetId.N_BAIOT, files, "c" * 64) is False
    assert publish_raw_dataset_identity(DatasetId.N_BAIOT, files, "c" * 64) is True
    assert publish_raw_dataset_identity(DatasetId.N_BAIOT, files, "d" * 64) is False


def test_scaler_is_published_with_its_metadata(isolated_repository: Path) -> None:
    scaler = ScalerMetadata(
        schema_version="fedsira|scaler_metadata|1",
        feature_names=("feature_a", "feature_b"),
        means=(1.0, 2.0),
        standard_deviations=(0.5, 0.25),
        training_row_count=10,
    )
    publish_scaler(DatasetId.CICIOT2023, scaler, "c" * 64)
    current = read_current_artifact(
        isolated_repository / "outputs" / "preprocessing" / "scaler" / str(DatasetId.CICIOT2023)
    )
    assert current is not None
    manifest, payload = current
    assert manifest.family is ArtifactFamily.SCALER
    assert ScalerMetadata.model_validate_json(payload) == scaler
