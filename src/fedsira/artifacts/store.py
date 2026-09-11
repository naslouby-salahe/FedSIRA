import hashlib
import os
import uuid
from pathlib import Path
from typing import TypeAlias

from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState
from fedsira.domain.types import (
    ArtifactComplete,
    ArtifactDigest,
    ArtifactReuseDecision,
    FrozenDomainModel,
    LogRecordText,
)
from fedsira.runtime import get_structured_logger

ArtifactPayloadBytes: TypeAlias = bytes

ARTIFACT_LOGGER = get_structured_logger("artifacts")

ARTIFACT_PAYLOAD_SUFFIX = ".artifact.bin"
ARTIFACT_MANIFEST_SUFFIX = ".manifest.json"


class ArtifactManifest(FrozenDomainModel):
    family: ArtifactFamily
    identity: ArtifactDigest
    checksum: ArtifactDigest
    lifecycle_state: ArtifactLifecycleState
    upstream_identities: tuple[ArtifactDigest, ...]

    def with_lifecycle_state(
        self,
        lifecycle_state: ArtifactLifecycleState,
    ) -> "ArtifactManifest":
        return ArtifactManifest(
            family=self.family,
            identity=self.identity,
            checksum=self.checksum,
            lifecycle_state=lifecycle_state,
            upstream_identities=self.upstream_identities,
        )


def load_published_manifests(roots: tuple[Path, ...]) -> tuple[ArtifactManifest, ...]:
    manifests: list[ArtifactManifest] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob(f"*{ARTIFACT_MANIFEST_SUFFIX}")):
            manifests.append(ArtifactManifest.model_validate_json(path.read_text(encoding="utf-8")))
    return tuple(manifests)


def validate_artifact_lifecycle_readable(manifest: ArtifactManifest) -> None:
    if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        raise ValueError(
            f"artifact {manifest.identity} is not Complete ({manifest.lifecycle_state.value}); "
            "it is never a valid input to downstream science"
        )


def compute_checksum(payload: ArtifactPayloadBytes) -> ArtifactDigest:
    return hashlib.sha256(payload).hexdigest()


def verify_checksum(payload: ArtifactPayloadBytes, manifest: ArtifactManifest) -> None:
    if compute_checksum(payload) != manifest.checksum:
        raise ValueError(f"checksum mismatch for artifact {manifest.identity}")


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
) -> ArtifactComplete:
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


class ArtifactLogFields(FrozenDomainModel):
    artifact_family: ArtifactFamily
    artifact_identity: ArtifactDigest


def _log_artifact_event(
    event: LogRecordText, family: ArtifactFamily, identity: ArtifactDigest
) -> None:
    ARTIFACT_LOGGER.info(
        event,
        extra=ArtifactLogFields(artifact_family=family, artifact_identity=identity).model_dump(),
    )


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
            _log_artifact_event("artifact.reused", family, identity)
            return existing, True

    staged_manifest = ArtifactManifest(
        family=family,
        identity=identity,
        checksum=compute_checksum(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        upstream_identities=upstream_identities,
    )
    staged_path = stage_payload(staging_root, payload)
    published = publish_artifact_to_disk(
        staged_path,
        published_directory,
        staged_manifest,
        payload,
    )
    _log_artifact_event("artifact.published", family, identity)
    return (published, False)
