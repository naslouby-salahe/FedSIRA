from pathlib import Path

import pytest

from fedsira.artifacts.store import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactManifest,
    ArtifactSlot,
    compute_checksum,
    is_artifact_complete_and_valid,
    publish_artifact_to_disk,
    read_current_artifact,
    read_published_manifest,
    stage_payload,
    verify_checksum,
)
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState, ArtifactProducer


def staged_manifest(identity: str, payload: bytes) -> ArtifactManifest:
    return ArtifactManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        slot=ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler"),
        producer=ArtifactProducer.PREPROCESSING,
        identity=identity,
        checksum=compute_checksum(payload),
        payload_bytes=len(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        dependencies=(),
        procedure_identity="fedsira|test_scaler|1",
        configuration_digest="d" * 64,
        code_revision=None,
    )


def test_verify_checksum_accepts_matching_payload() -> None:
    payload = b"payload"
    verify_checksum(payload, staged_manifest("a" * 64, payload))


def test_verify_checksum_rejects_mismatched_payload() -> None:
    with pytest.raises(ValueError):
        verify_checksum(b"tampered", staged_manifest("a" * 64, b"payload"))


def test_stage_payload_gives_each_call_a_distinct_path(tmp_path: Path) -> None:
    first = stage_payload(tmp_path / "staging", b"payload")
    second = stage_payload(tmp_path / "staging", b"payload")
    assert first != second


def test_publish_artifact_to_disk_writes_complete_manifest(tmp_path: Path) -> None:
    payload = b"payload"
    manifest = staged_manifest("a" * 64, payload)
    staged_path = stage_payload(tmp_path / "staging", payload)
    published = publish_artifact_to_disk(staged_path, tmp_path / "canonical", manifest, payload)
    assert published.lifecycle_state is ArtifactLifecycleState.COMPLETE
    assert read_published_manifest(tmp_path / "canonical", "a" * 64) == published


def test_complete_artifact_is_reusable_only_when_payload_matches(tmp_path: Path) -> None:
    payload = b"payload"
    directory = tmp_path / "canonical"
    publish_artifact_to_disk(
        stage_payload(tmp_path / "staging", payload),
        directory,
        staged_manifest("a" * 64, payload),
        payload,
    )
    assert is_artifact_complete_and_valid(directory, "a" * 64)
    (directory / f"{'a' * 64}.artifact.bin").write_bytes(b"corrupted")
    assert not is_artifact_complete_and_valid(directory, "a" * 64)


def test_publishing_moves_the_current_pointer_to_the_published_identity(tmp_path: Path) -> None:
    payload = b"payload"
    directory = tmp_path / "canonical"
    published = publish_artifact_to_disk(
        stage_payload(tmp_path / "staging", payload),
        directory,
        staged_manifest("a" * 64, payload),
        payload,
    )
    current = read_current_artifact(directory)
    assert current is not None
    manifest, current_payload = current
    assert manifest == published
    assert current_payload == payload


def test_current_artifact_reports_nothing_before_any_publish(tmp_path: Path) -> None:
    assert read_current_artifact(tmp_path / "canonical") is None
