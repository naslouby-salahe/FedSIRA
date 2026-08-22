import hashlib

from fedsira.artifacts.graph import ArtifactGraph
from fedsira.artifacts.records import ArtifactManifest
from fedsira.domain.enums import ArtifactLifecycleState
from fedsira.domain.records import ArtifactDigest


def compute_checksum(payload: bytes) -> ArtifactDigest:
    return hashlib.sha256(payload).hexdigest()


def verify_checksum(payload: bytes, manifest: ArtifactManifest) -> None:
    if compute_checksum(payload) != manifest.checksum:
        raise ValueError(f"checksum mismatch for artifact {manifest.identity}")


def publish(
    graph: ArtifactGraph, staged_manifest: ArtifactManifest, payload: bytes
) -> ArtifactManifest:
    if staged_manifest.lifecycle_state is not ArtifactLifecycleState.STAGING:
        raise ValueError("only a staged manifest may be published")
    verify_checksum(payload, staged_manifest)
    completed = staged_manifest.model_copy(
        update={"lifecycle_state": ArtifactLifecycleState.COMPLETE}
    )
    graph.register(completed)
    return completed


def retire(graph: ArtifactGraph, identity: ArtifactDigest) -> ArtifactManifest:
    current = graph.get(identity)
    if current.lifecycle_state not in (
        ArtifactLifecycleState.COMPLETE,
        ArtifactLifecycleState.STALE,
    ):
        raise ValueError(f"artifact {identity} is not eligible for retirement")
    retired = current.model_copy(update={"lifecycle_state": ArtifactLifecycleState.RETIRED})
    graph.register(retired)
    return retired


def replace(
    graph: ArtifactGraph,
    superseded_identity: ArtifactDigest,
    new_manifest: ArtifactManifest,
    new_payload: bytes,
) -> ArtifactManifest:
    published = publish(graph, new_manifest, new_payload)
    retire(graph, superseded_identity)
    return published
