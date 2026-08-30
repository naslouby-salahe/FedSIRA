import hashlib
import os
import uuid
from pathlib import Path

from fedsira.artifacts.graph import ArtifactGraph
from fedsira.artifacts.records import ArtifactManifest, ArtifactPayloadBytes
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState
from fedsira.domain.records import ArtifactDigest, ArtifactReuseDecision, BooleanValue

ARTIFACT_PAYLOAD_SUFFIX = ".artifact.bin"
ARTIFACT_MANIFEST_SUFFIX = ".manifest.json"


def compute_checksum(payload: ArtifactPayloadBytes) -> ArtifactDigest:
    return hashlib.sha256(payload).hexdigest()


def verify_checksum(payload: ArtifactPayloadBytes, manifest: ArtifactManifest) -> None:
    if compute_checksum(payload) != manifest.checksum:
        raise ValueError(f"checksum mismatch for artifact {manifest.identity}")


def publish(
    graph: ArtifactGraph,
    staged_manifest: ArtifactManifest,
    payload: ArtifactPayloadBytes,
) -> ArtifactManifest:
    if staged_manifest.lifecycle_state is not ArtifactLifecycleState.STAGING:
        raise ValueError("only a staged manifest may be published")
    verify_checksum(payload, staged_manifest)
    completed = staged_manifest.with_lifecycle_state(ArtifactLifecycleState.COMPLETE)
    graph.register(completed)
    return completed


def retire(graph: ArtifactGraph, identity: ArtifactDigest) -> ArtifactManifest:
    current = graph.get(identity)
    if current.lifecycle_state not in (
        ArtifactLifecycleState.COMPLETE,
        ArtifactLifecycleState.STALE,
    ):
        raise ValueError(f"artifact {identity} is not eligible for retirement")
    retired = current.with_lifecycle_state(ArtifactLifecycleState.RETIRED)
    graph.register(retired)
    return retired


def replace(
    graph: ArtifactGraph,
    superseded_identity: ArtifactDigest,
    new_manifest: ArtifactManifest,
    new_payload: ArtifactPayloadBytes,
) -> ArtifactManifest:
    published = publish(graph, new_manifest, new_payload)
    retire(graph, superseded_identity)
    return published


def stage_payload(cache_staging_root: Path, payload: ArtifactPayloadBytes) -> Path:
    cache_staging_root.mkdir(parents=True, exist_ok=True)
    staged_path = cache_staging_root / f"{uuid.uuid4().hex}.staged"
    staged_path.write_bytes(payload)
    return staged_path


def published_artifact_paths(
    published_directory: Path,
    identity: ArtifactDigest,
) -> tuple[Path, Path]:
    payload_path = published_directory / f"{identity}{ARTIFACT_PAYLOAD_SUFFIX}"
    manifest_path = published_directory / f"{identity}{ARTIFACT_MANIFEST_SUFFIX}"
    return payload_path, manifest_path


def publish_artifact_to_disk(
    staged_path: Path,
    published_directory: Path,
    staged_manifest: ArtifactManifest,
    payload: ArtifactPayloadBytes,
) -> ArtifactManifest:
    if staged_manifest.lifecycle_state is not ArtifactLifecycleState.STAGING:
        raise ValueError("only a staged manifest may be published")
    verify_checksum(payload, staged_manifest)
    completed = staged_manifest.with_lifecycle_state(ArtifactLifecycleState.COMPLETE)
    published_directory.mkdir(parents=True, exist_ok=True)
    payload_path, manifest_path = published_artifact_paths(
        published_directory,
        staged_manifest.identity,
    )
    os.replace(staged_path, payload_path)
    manifest_path.write_text(completed.model_dump_json(), encoding="utf-8")
    return completed


def read_published_manifest(
    published_directory: Path,
    identity: ArtifactDigest,
) -> ArtifactManifest | None:
    _, manifest_path = published_artifact_paths(published_directory, identity)
    if not manifest_path.exists():
        return None
    return ArtifactManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def is_artifact_complete_and_valid(
    published_directory: Path,
    identity: ArtifactDigest,
) -> BooleanValue:
    manifest = read_published_manifest(published_directory, identity)
    if manifest is None or manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        return False
    payload_path, _ = published_artifact_paths(published_directory, identity)
    if not payload_path.exists():
        return False
    try:
        verify_checksum(payload_path.read_bytes(), manifest)
    except ValueError:
        return False
    return True


def publish_or_reuse_artifact_payload(
    *,
    family: ArtifactFamily,
    identity: ArtifactDigest,
    payload: ArtifactPayloadBytes,
    published_directory: Path,
    staging_root: Path,
    upstream_identities: tuple[ArtifactDigest, ...] = (),
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    if is_artifact_complete_and_valid(published_directory, identity):
        existing = read_published_manifest(published_directory, identity)
        if existing is not None:
            return existing, True

    staged_manifest = ArtifactManifest(
        family=family,
        identity=identity,
        checksum=compute_checksum(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        upstream_identities=upstream_identities,
    )
    staged_path = stage_payload(staging_root, payload)
    return (
        publish_artifact_to_disk(
            staged_path,
            published_directory,
            staged_manifest,
            payload,
        ),
        False,
    )