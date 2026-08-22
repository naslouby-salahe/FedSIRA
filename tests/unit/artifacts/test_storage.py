from pathlib import Path

import pytest

from fedsira.artifacts.graph import ArtifactGraph
from fedsira.artifacts.records import ArtifactManifest
from fedsira.artifacts.storage import (
    compute_checksum,
    is_artifact_complete_and_valid,
    publish,
    publish_artifact_to_disk,
    read_published_manifest,
    replace,
    retire,
    stage_payload,
    verify_checksum,
)
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState


def staged_manifest(
    identity: str, payload: bytes, upstream: tuple[str, ...] = ()
) -> ArtifactManifest:
    return ArtifactManifest(
        family=ArtifactFamily.SCALER,
        identity=identity,
        checksum=compute_checksum(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        upstream_identities=upstream,
    )


def test_verify_checksum_accepts_matching_payload() -> None:
    payload = b"payload"
    manifest = staged_manifest("a" * 64, payload)
    verify_checksum(payload, manifest)


def test_verify_checksum_rejects_mismatched_payload() -> None:
    manifest = staged_manifest("a" * 64, b"payload")
    with pytest.raises(ValueError):
        verify_checksum(b"tampered", manifest)


def test_publish_promotes_staging_to_complete() -> None:
    graph = ArtifactGraph()
    payload = b"payload"
    manifest = staged_manifest("a" * 64, payload)
    published = publish(graph, manifest, payload)
    assert published.lifecycle_state is ArtifactLifecycleState.COMPLETE
    assert graph.is_active("a" * 64)


def test_publish_rejects_non_staging_manifest() -> None:
    graph = ArtifactGraph()
    payload = b"payload"
    manifest = staged_manifest("a" * 64, payload).model_copy(
        update={"lifecycle_state": ArtifactLifecycleState.COMPLETE}
    )
    with pytest.raises(ValueError):
        publish(graph, manifest, payload)


def test_publish_rejects_checksum_mismatch() -> None:
    graph = ArtifactGraph()
    manifest = staged_manifest("a" * 64, b"payload")
    with pytest.raises(ValueError):
        publish(graph, manifest, b"tampered")


def test_retire_moves_complete_artifact_to_retired() -> None:
    graph = ArtifactGraph()
    payload = b"payload"
    published = publish(graph, staged_manifest("a" * 64, payload), payload)
    retired = retire(graph, published.identity)
    assert retired.lifecycle_state is ArtifactLifecycleState.RETIRED
    assert not graph.is_active("a" * 64)


def test_replace_publishes_new_and_retires_old_without_dual_activity() -> None:
    graph = ArtifactGraph()
    old_payload = b"old"
    old = publish(graph, staged_manifest("a" * 64, old_payload), old_payload)

    new_payload = b"new"
    new_manifest = staged_manifest("b" * 64, new_payload)
    published = replace(graph, old.identity, new_manifest, new_payload)

    assert graph.is_active(published.identity)
    assert not graph.is_active(old.identity)


def test_stage_payload_writes_bytes_to_a_new_staged_file(tmp_path: Path) -> None:
    staged_path = stage_payload(tmp_path / "staging", b"payload")
    assert staged_path.read_bytes() == b"payload"
    assert staged_path.parent == tmp_path / "staging"


def test_stage_payload_gives_each_call_a_distinct_path(tmp_path: Path) -> None:
    first = stage_payload(tmp_path / "staging", b"payload")
    second = stage_payload(tmp_path / "staging", b"payload")
    assert first != second


def test_publish_artifact_to_disk_writes_payload_and_manifest(tmp_path: Path) -> None:
    payload = b"payload"
    manifest = staged_manifest("a" * 64, payload)
    staged_path = stage_payload(tmp_path / "staging", payload)
    canonical_directory = tmp_path / "canonical"

    published = publish_artifact_to_disk(staged_path, canonical_directory, manifest, payload)

    assert published.lifecycle_state is ArtifactLifecycleState.COMPLETE
    assert not staged_path.exists()
    read_back = read_published_manifest(canonical_directory, "a" * 64)
    assert read_back == published


def test_publish_artifact_to_disk_rejects_checksum_mismatch(tmp_path: Path) -> None:
    manifest = staged_manifest("a" * 64, b"payload")
    staged_path = stage_payload(tmp_path / "staging", b"tampered")
    with pytest.raises(ValueError):
        publish_artifact_to_disk(staged_path, tmp_path / "canonical", manifest, b"tampered")


def test_read_published_manifest_returns_none_when_absent(tmp_path: Path) -> None:
    assert read_published_manifest(tmp_path / "canonical", "a" * 64) is None


def test_is_artifact_complete_and_valid_true_after_publish(tmp_path: Path) -> None:
    payload = b"payload"
    manifest = staged_manifest("a" * 64, payload)
    staged_path = stage_payload(tmp_path / "staging", payload)
    canonical_directory = tmp_path / "canonical"
    publish_artifact_to_disk(staged_path, canonical_directory, manifest, payload)

    assert is_artifact_complete_and_valid(canonical_directory, "a" * 64)


def test_is_artifact_complete_and_valid_false_when_never_published(tmp_path: Path) -> None:
    assert not is_artifact_complete_and_valid(tmp_path / "canonical", "a" * 64)


def test_is_artifact_complete_and_valid_false_when_payload_corrupted(tmp_path: Path) -> None:
    payload = b"payload"
    manifest = staged_manifest("a" * 64, payload)
    staged_path = stage_payload(tmp_path / "staging", payload)
    canonical_directory = tmp_path / "canonical"
    publish_artifact_to_disk(staged_path, canonical_directory, manifest, payload)

    payload_path = canonical_directory / f"{'a' * 64}.artifact.bin"
    payload_path.write_bytes(b"corrupted")

    assert not is_artifact_complete_and_valid(canonical_directory, "a" * 64)
