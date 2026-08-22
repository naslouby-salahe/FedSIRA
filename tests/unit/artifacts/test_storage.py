import pytest

from fedsira.artifacts.graph import ArtifactGraph
from fedsira.artifacts.records import ArtifactManifest
from fedsira.artifacts.storage import compute_checksum, publish, replace, retire, verify_checksum
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
