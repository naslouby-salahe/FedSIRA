import hashlib
import os
import uuid
from pathlib import Path

from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactLifecycleState,
    ArtifactProducer,
)
from fedsira.domain.types import (
    ArtifactComplete,
    ArtifactDependencyName,
    ArtifactDigest,
    ArtifactInstanceToken,
    ArtifactPayloadBytes,
    ArtifactReuseDecision,
    ByteCount,
    ExperimentName,
    FailureMessage,
    FrozenDomainModel,
    LogRecordText,
    ProcedureIdentity,
    RelativePathText,
    SchemaVersion,
    SupersededPublication,
    TextValue,
)
from fedsira.runtime import (
    REPOSITORY_ROOT,
    configure_structured_file_logging,
    current_application_context,
    framed_bytes,
    get_structured_logger,
)

ARTIFACT_SCHEMA_VERSION: SchemaVersion = "fedsira|artifact_manifest|2"  # TODO: should be enum

ARTIFACT_LOGGER = get_structured_logger("artifacts")

ARTIFACT_PAYLOAD_SUFFIX = ".artifact.bin"
ARTIFACT_MANIFEST_SUFFIX = ".manifest.json"
ARTIFACT_CURRENT_FILE_NAME = "current.json"

ARTIFACT_LOG_NAME = "artifacts.log"


class ArtifactDependency(FrozenDomainModel):
    kind: ArtifactDependencyKind
    dependency: ArtifactDependencyName
    digest: ArtifactDigest


class ArtifactSlot(FrozenDomainModel):
    family: ArtifactFamily
    instance: ArtifactInstanceToken
    experiment: ExperimentName | None = None


class ArtifactManifest(FrozenDomainModel):
    schema_version: SchemaVersion
    slot: ArtifactSlot
    producer: ArtifactProducer
    identity: ArtifactDigest
    checksum: ArtifactDigest
    payload_bytes: ByteCount
    lifecycle_state: ArtifactLifecycleState
    dependencies: tuple[ArtifactDependency, ...]
    procedure_identity: ProcedureIdentity
    configuration_digest: ArtifactDigest
    code_revision: TextValue | None

    @property
    def family(self) -> ArtifactFamily:
        return self.slot.family

    def with_lifecycle_state(self, lifecycle_state: ArtifactLifecycleState) -> "ArtifactManifest":
        return ArtifactManifest(
            schema_version=self.schema_version,
            slot=self.slot,
            producer=self.producer,
            identity=self.identity,
            checksum=self.checksum,
            payload_bytes=self.payload_bytes,
            lifecycle_state=lifecycle_state,
            dependencies=self.dependencies,
            procedure_identity=self.procedure_identity,
            configuration_digest=self.configuration_digest,
            code_revision=self.code_revision,
        )


class ArtifactCurrentPointer(FrozenDomainModel):
    schema_version: SchemaVersion
    slot: ArtifactSlot
    identity: ArtifactDigest


class InvalidArtifactReport(FrozenDomainModel):
    manifest_path: RelativePathText
    failure: FailureMessage


def configure_artifact_logging(log_path: Path) -> None:
    configure_structured_file_logging(ARTIFACT_LOGGER, log_path)


def repository_revision() -> TextValue | None:
    git_root = REPOSITORY_ROOT / ".git"
    head_path = git_root / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref: "):
        return head
    try:
        return (git_root / head.removeprefix("ref: ")).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def configuration_digest() -> ArtifactDigest:
    config = current_application_context().scientific_config
    payload = config.model_dump_json().encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def artifact_identity(
    slot: ArtifactSlot,
    dependencies: tuple[ArtifactDependency, ...],
    procedure_identity: ProcedureIdentity,
) -> ArtifactDigest:
    labelled = tuple(
        field
        for dependency in sorted(dependencies, key=lambda item: item.dependency)
        for field in (dependency.dependency, dependency.digest)
    )
    return hashlib.sha256(
        framed_bytes(
            slot.family.value,
            slot.instance,
            slot.experiment or "",
            ARTIFACT_SCHEMA_VERSION,
            procedure_identity,
            *labelled,
        )
    ).hexdigest()


def compute_checksum(payload: ArtifactPayloadBytes) -> ArtifactDigest:
    return hashlib.sha256(payload).hexdigest()


def verify_checksum(payload: ArtifactPayloadBytes, manifest: ArtifactManifest) -> None:
    if compute_checksum(payload) != manifest.checksum:
        raise ValueError(f"checksum mismatch for artifact {manifest.identity}")


def _write_text_atomically(path: Path, text: TextValue) -> None:
    temporary_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.partial")
    temporary_path.write_text(text, encoding="utf-8")
    os.replace(temporary_path, path)


def reported_manifest_path(path: Path) -> RelativePathText:
    try:
        return str(path.relative_to(REPOSITORY_ROOT))
    except ValueError:
        return str(path)


def _manifest_identity_from_path(path: Path) -> ArtifactDigest:
    return path.name.removesuffix(ARTIFACT_MANIFEST_SUFFIX)


def _is_superseded_history(path: Path) -> SupersededPublication:
    pointer_path = current_pointer_path(path.parent)
    if not pointer_path.exists():
        return False
    try:
        pointer = ArtifactCurrentPointer.model_validate_json(
            pointer_path.read_text(encoding="utf-8")
        )
    except ValueError:
        return False
    return pointer.identity != _manifest_identity_from_path(path)


def load_published_manifests(
    roots: tuple[Path, ...],
) -> tuple[tuple[ArtifactManifest, ...], tuple[InvalidArtifactReport, ...]]:
    manifests: list[ArtifactManifest] = []
    invalid: list[InvalidArtifactReport] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob(f"*{ARTIFACT_MANIFEST_SUFFIX}")):
            try:
                manifests.append(
                    ArtifactManifest.model_validate_json(path.read_text(encoding="utf-8"))
                )
            except ValueError as error:
                if _is_superseded_history(path):
                    _log_unreadable_manifest(path, error)
                    continue
                invalid.append(
                    InvalidArtifactReport(
                        manifest_path=reported_manifest_path(path),
                        failure=str(error),
                    )
                )
    return tuple(manifests), tuple(invalid)


def validate_artifact_lifecycle_readable(manifest: ArtifactManifest) -> None:
    if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        raise ValueError(
            f"artifact {manifest.identity} is not Complete ({manifest.lifecycle_state.value}); "
            "it is never a valid input to downstream science"
        )


def published_artifact_paths(
    slot_directory: Path,
    identity: ArtifactDigest,
) -> tuple[Path, Path]:
    payload_path = slot_directory / f"{identity}{ARTIFACT_PAYLOAD_SUFFIX}"
    manifest_path = slot_directory / f"{identity}{ARTIFACT_MANIFEST_SUFFIX}"
    return payload_path, manifest_path


def current_pointer_path(slot_directory: Path) -> Path:
    return slot_directory / ARTIFACT_CURRENT_FILE_NAME


def stage_payload(staging_root: Path, payload: ArtifactPayloadBytes) -> Path:
    staging_root.mkdir(parents=True, exist_ok=True)
    staged_path = staging_root / f"{uuid.uuid4().hex}.staged"
    staged_path.write_bytes(payload)
    return staged_path


def publish_artifact_to_disk(
    staged_path: Path,
    slot_directory: Path,
    staged_manifest: ArtifactManifest,
    payload: ArtifactPayloadBytes,
) -> ArtifactManifest:
    if staged_manifest.lifecycle_state is not ArtifactLifecycleState.STAGING:
        raise ValueError("only a staged manifest may be published")
    verify_checksum(payload, staged_manifest)
    completed = staged_manifest.with_lifecycle_state(ArtifactLifecycleState.COMPLETE)
    slot_directory.mkdir(parents=True, exist_ok=True)
    payload_path, manifest_path = published_artifact_paths(
        slot_directory,
        staged_manifest.identity,
    )
    os.replace(staged_path, payload_path)
    _write_text_atomically(manifest_path, completed.model_dump_json())
    _write_text_atomically(
        current_pointer_path(slot_directory),
        ArtifactCurrentPointer(
            schema_version=ARTIFACT_SCHEMA_VERSION,
            slot=completed.slot,
            identity=completed.identity,
        ).model_dump_json(),
    )
    return completed


def read_published_manifest(
    slot_directory: Path,
    identity: ArtifactDigest,
) -> ArtifactManifest | None:
    _, manifest_path = published_artifact_paths(slot_directory, identity)
    if not manifest_path.exists():
        return None
    try:
        return ArtifactManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except ValueError as error:
        _log_unreadable_manifest(manifest_path, error)
        return None


def is_artifact_complete_and_valid(
    slot_directory: Path,
    identity: ArtifactDigest,
) -> ArtifactComplete:
    manifest = read_published_manifest(slot_directory, identity)
    if manifest is None or manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        return False
    payload_path, _ = published_artifact_paths(slot_directory, identity)
    if not payload_path.exists():
        return False
    try:
        verify_checksum(payload_path.read_bytes(), manifest)
    except ValueError:
        return False
    return True


def read_validated_artifact_payload(
    slot_directory: Path,
    identity: ArtifactDigest,
) -> ArtifactPayloadBytes:
    manifest = read_published_manifest(slot_directory, identity)
    if manifest is None:
        raise ValueError(f"artifact {identity} has no published manifest")
    if manifest.schema_version != ARTIFACT_SCHEMA_VERSION:
        raise ValueError(
            f"artifact {identity} uses schema {manifest.schema_version}, "
            f"expected {ARTIFACT_SCHEMA_VERSION}"
        )
    validate_artifact_lifecycle_readable(manifest)
    payload_path, _ = published_artifact_paths(slot_directory, identity)
    if not payload_path.exists():
        raise ValueError(f"artifact {identity} is Complete but its payload is absent")
    payload = payload_path.read_bytes()
    verify_checksum(payload, manifest)
    if len(payload) != manifest.payload_bytes:
        raise ValueError(f"artifact {identity} payload length does not match its manifest")
    return payload


def read_current_artifact(
    slot_directory: Path,
) -> tuple[ArtifactManifest, ArtifactPayloadBytes] | None:
    pointer_path = current_pointer_path(slot_directory)
    if not pointer_path.exists():
        return None
    pointer = ArtifactCurrentPointer.model_validate_json(pointer_path.read_text(encoding="utf-8"))
    manifest = read_published_manifest(slot_directory, pointer.identity)
    if manifest is None or manifest.slot != pointer.slot:
        return None
    return manifest, read_validated_artifact_payload(slot_directory, pointer.identity)


class ArtifactLogFields(FrozenDomainModel):
    artifact_family: ArtifactFamily
    artifact_instance: ArtifactInstanceToken
    artifact_identity: ArtifactDigest


def _log_artifact_event(event: LogRecordText, slot: ArtifactSlot, identity: ArtifactDigest) -> None:
    ARTIFACT_LOGGER.info(
        event,
        extra=ArtifactLogFields(
            artifact_family=slot.family,
            artifact_instance=slot.instance,
            artifact_identity=identity,
        ).model_dump(),
    )


def _log_unreadable_manifest(manifest_path: Path, error: ValueError) -> None:
    ARTIFACT_LOGGER.warning("artifact.manifest.unreadable %s: %s", manifest_path, error)


def publish_artifact(
    *,
    slot: ArtifactSlot,
    producer: ArtifactProducer,
    payload: ArtifactPayloadBytes,
    dependencies: tuple[ArtifactDependency, ...],
    procedure_identity: ProcedureIdentity,
    slot_directory: Path,
    staging_root: Path,
) -> tuple[ArtifactManifest, ArtifactReuseDecision]:
    identity = artifact_identity(slot, dependencies, procedure_identity)
    if is_artifact_complete_and_valid(slot_directory, identity):
        existing = read_published_manifest(slot_directory, identity)
        if existing is not None:
            _write_text_atomically(
                current_pointer_path(slot_directory),
                ArtifactCurrentPointer(
                    schema_version=ARTIFACT_SCHEMA_VERSION,
                    slot=slot,
                    identity=identity,
                ).model_dump_json(),
            )
            _log_artifact_event("artifact.reused", slot, identity)
            return existing, True
    staged_manifest = ArtifactManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        slot=slot,
        producer=producer,
        identity=identity,
        checksum=compute_checksum(payload),
        payload_bytes=len(payload),
        lifecycle_state=ArtifactLifecycleState.STAGING,
        dependencies=dependencies,
        procedure_identity=procedure_identity,
        configuration_digest=configuration_digest(),
        code_revision=repository_revision(),
    )
    staged_path = stage_payload(staging_root, payload)
    published = publish_artifact_to_disk(
        staged_path,
        slot_directory,
        staged_manifest,
        payload,
    )
    _log_artifact_event("artifact.published", slot, identity)
    return (published, False)
