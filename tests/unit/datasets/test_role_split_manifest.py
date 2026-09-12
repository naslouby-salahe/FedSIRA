from collections.abc import Iterator
from pathlib import Path

import pytest

from fedsira.artifacts.paths import artifact_slot_directory
from fedsira.artifacts.store import ArtifactManifest, read_current_artifact
from fedsira.datasets.layout import raw_dataset_present, validate_repository_layout
from fedsira.datasets.role_split import (
    ROLE_SPLIT_MANIFEST_INSTANCE,
    RoleSplitSampleManifestPayload,
    RoleSplitViewCount,
    publish_role_split_sample_manifest,
    role_split_sample_manifest_slot,
)
from fedsira.domain.enums import ArtifactFamily, DatasetId, Role
from fedsira.runtime import (
    bound_application_context,
    current_application_context,
)


@pytest.fixture
def isolated_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    monkeypatch.setattr("fedsira.datasets.role_split.REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr("fedsira.datasets.layout.REPOSITORY_ROOT", tmp_path)
    context = current_application_context().model_copy(update={"repository_root": tmp_path})
    with bound_application_context(context):
        yield tmp_path


def _counts() -> tuple[RoleSplitViewCount, ...]:
    return (
        RoleSplitViewCount(
            domain="Danmini Doorbell",
            class_id="BENIGN",
            role=Role.ANCHOR_TRAIN,
            row_count=4000,
        ),
        RoleSplitViewCount(
            domain="Danmini Doorbell",
            class_id="GAFGYT_COMBO",
            role=Role.REPRODUCTION,
            row_count=4000,
        ),
    )


def _current(
    repository: Path, dataset: DatasetId
) -> tuple[ArtifactManifest, RoleSplitSampleManifestPayload]:
    slot = role_split_sample_manifest_slot(dataset)
    current = read_current_artifact(repository / artifact_slot_directory(slot))
    assert current is not None
    manifest, payload = current
    return manifest, RoleSplitSampleManifestPayload.model_validate_json(payload)


def test_role_split_manifest_records_governed_split_specification(
    isolated_repository: Path,
) -> None:
    publish_role_split_sample_manifest(DatasetId.N_BAIOT, "a" * 64, _counts())
    manifest, payload = _current(isolated_repository, DatasetId.N_BAIOT)
    assert manifest.family is ArtifactFamily.ROLE_SPLIT_SAMPLE_MANIFEST
    slot = role_split_sample_manifest_slot(DatasetId.N_BAIOT)
    assert slot.instance == f"{ROLE_SPLIT_MANIFEST_INSTANCE}-{DatasetId.N_BAIOT.value}"
    primary = current_application_context().scientific_config.datasets.primary
    assert payload.role_intervals == primary.role_intervals
    assert payload.sampling_caps_per_domain == primary.sampling_caps_per_domain
    assert payload.counts == tuple(sorted(_counts(), key=lambda item: item.role.value))
    assert payload.target_class == primary.target_class
    assert manifest.dependencies[0].digest == "a" * 64


def test_role_split_manifest_reuses_and_invalidates_on_dataset_identity(
    isolated_repository: Path,
) -> None:
    first_manifest, reused = publish_role_split_sample_manifest(
        DatasetId.N_BAIOT, "a" * 64, _counts()
    )
    assert reused is False
    repeated_manifest, reused_again = publish_role_split_sample_manifest(
        DatasetId.N_BAIOT, "a" * 64, _counts()
    )
    assert reused_again is True
    assert repeated_manifest.identity == first_manifest.identity
    changed_manifest, reused_after_change = publish_role_split_sample_manifest(
        DatasetId.N_BAIOT, "b" * 64, _counts()
    )
    assert reused_after_change is False
    assert changed_manifest.identity != first_manifest.identity


def test_role_split_manifest_is_per_dataset(isolated_repository: Path) -> None:
    assert role_split_sample_manifest_slot(DatasetId.N_BAIOT) != role_split_sample_manifest_slot(
        DatasetId.CICIOT2023
    )


def test_role_split_manifest_uses_the_secondary_target_class(
    isolated_repository: Path,
) -> None:
    publish_role_split_sample_manifest(DatasetId.CICIOT2023, "c" * 64, _counts())
    _manifest, payload = _current(isolated_repository, DatasetId.CICIOT2023)
    assert payload.target_class == (
        current_application_context().scientific_config.datasets.secondary.target_class
    )


def test_repository_layout_validation_reports_every_missing_root(
    isolated_repository: Path,
) -> None:
    failures = validate_repository_layout()
    assert len(failures) == 4
    for configured in ("src/fedsira", "tests", "data/raw", "results"):
        (isolated_repository / configured).mkdir(parents=True, exist_ok=True)
    assert validate_repository_layout() == ()


def test_raw_dataset_presence_follows_the_configured_primary_root(
    isolated_repository: Path,
) -> None:
    assert raw_dataset_present(DatasetId.N_BAIOT) is False
    layout = current_application_context().scientific_config.execution.repository_layout
    (isolated_repository / layout.raw_data / DatasetId.N_BAIOT.value).mkdir(parents=True)
    assert raw_dataset_present(DatasetId.N_BAIOT) is True
    assert raw_dataset_present(DatasetId.CICIOT2023) is False
