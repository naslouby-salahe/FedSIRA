import hashlib
import os
import uuid
from pathlib import Path

from fedsira.artifacts.graph import ArtifactGraph
from fedsira.artifacts.records import ArtifactManifest
from fedsira.domain.enums import ArtifactLifecycleState
from fedsira.domain.records import ArtifactDigest

ARTIFACT_PAYLOAD_SUFFIX = ".artifact.bin"
ARTIFACT_MANIFEST_SUFFIX = ".manifest.json"


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


def stage_payload(cache_staging_root: Path, payload: bytes) -> Path:
    cache_staging_root.mkdir(parents=True, exist_ok=True)
    staged_path = cache_staging_root / f"{uuid.uuid4().hex}.staged"
    staged_path.write_bytes(payload)
    return staged_path


def canonical_artifact_paths(
    canonical_directory: Path, identity: ArtifactDigest
) -> tuple[Path, Path]:
    payload_path = canonical_directory / f"{identity}{ARTIFACT_PAYLOAD_SUFFIX}"
    manifest_path = canonical_directory / f"{identity}{ARTIFACT_MANIFEST_SUFFIX}"
    return payload_path, manifest_path


def publish_artifact_to_disk(
    staged_path: Path, canonical_directory: Path, staged_manifest: ArtifactManifest, payload: bytes
) -> ArtifactManifest:
    if staged_manifest.lifecycle_state is not ArtifactLifecycleState.STAGING:
        raise ValueError("only a staged manifest may be published")
    verify_checksum(payload, staged_manifest)
    completed = staged_manifest.model_copy(
        update={"lifecycle_state": ArtifactLifecycleState.COMPLETE}
    )
    canonical_directory.mkdir(parents=True, exist_ok=True)
    payload_path, manifest_path = canonical_artifact_paths(
        canonical_directory, staged_manifest.identity
    )
    os.replace(staged_path, payload_path)
    manifest_path.write_text(completed.model_dump_json())
    return completed


def read_published_manifest(
    canonical_directory: Path, identity: ArtifactDigest
) -> ArtifactManifest | None:
    _, manifest_path = canonical_artifact_paths(canonical_directory, identity)
    if not manifest_path.exists():
        return None
    return ArtifactManifest.model_validate_json(manifest_path.read_text())


def is_artifact_complete_and_valid(canonical_directory: Path, identity: ArtifactDigest) -> bool:
    manifest = read_published_manifest(canonical_directory, identity)
    if manifest is None or manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        return False
    payload_path, _ = canonical_artifact_paths(canonical_directory, identity)
    if not payload_path.exists():
        return False
    try:
        verify_checksum(payload_path.read_bytes(), manifest)
    except ValueError:
        return False
    return True
