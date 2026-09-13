from fedsira.artifacts.store import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactDependency,
    ArtifactManifest,
    ArtifactSlot,
    artifact_identity,
    validate_artifact_lifecycle_readable,
)
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactDependencyLabel,
    ArtifactFamily,
    ArtifactInstanceLabel,
    ArtifactLifecycleState,
    ArtifactProducer,
    SmokeCheckName,
)
from fedsira.domain.types import ProcedureIdentity
from fedsira.experiments.smoke_records import SmokeCheckResult

SMOKE_ARTIFACT_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|smoke_artifact|1"
SMOKE_PARENT_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|smoke_parent|1"
SMOKE_CHILD_PROCEDURE_IDENTITY: ProcedureIdentity = "fedsira|smoke_child|1"


def artifact_invariants() -> tuple[SmokeCheckResult, ...]:
    manifest = ArtifactManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        slot=ArtifactSlot(
            family=ArtifactFamily.SCALER,
            instance=ArtifactInstanceLabel.SMOKE_INVARIANT,
        ),
        producer=ArtifactProducer.PREPROCESSING,
        identity="a" * 64,
        checksum="b" * 64,
        payload_bytes=0,
        lifecycle_state=ArtifactLifecycleState.COMPLETE,
        dependencies=(),
        procedure_identity=SMOKE_ARTIFACT_PROCEDURE_IDENTITY,
        configuration_digest="c" * 64,
        code_revision=None,
    )
    try:
        validate_artifact_lifecycle_readable(manifest)
        lifecycle_is_readable = True
    except ValueError:
        lifecycle_is_readable = False
    parent_slot = ArtifactSlot(
        family=ArtifactFamily.SCALER,
        instance=ArtifactInstanceLabel.SMOKE_PARENT,
    )
    child_slot = ArtifactSlot(
        family=ArtifactFamily.PREPARED_ROLE_VIEW,
        instance=ArtifactInstanceLabel.SMOKE_DESCENDANT,
    )
    parent_identity = artifact_identity(
        parent_slot,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.RAW_DATASET,
                digest="a" * 64,
            ),
        ),
        SMOKE_PARENT_PROCEDURE_IDENTITY,
    )
    changed_parent_identity = artifact_identity(
        parent_slot,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency=ArtifactDependencyLabel.RAW_DATASET,
                digest="d" * 64,
            ),
        ),
        SMOKE_PARENT_PROCEDURE_IDENTITY,
    )
    child_identity = artifact_identity(
        child_slot,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.ARTIFACT,
                dependency=ArtifactDependencyLabel.PARENT,
                digest=parent_identity,
            ),
        ),
        SMOKE_CHILD_PROCEDURE_IDENTITY,
    )
    changed_child_identity = artifact_identity(
        child_slot,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.ARTIFACT,
                dependency=ArtifactDependencyLabel.PARENT,
                digest=changed_parent_identity,
            ),
        ),
        SMOKE_CHILD_PROCEDURE_IDENTITY,
    )
    return (
        SmokeCheckResult(
            name=SmokeCheckName.COMPLETE_ARTIFACT_MANIFEST_IS_READABLE,
            passed=lifecycle_is_readable,
        ),
        SmokeCheckResult(
            name=SmokeCheckName.PARENT_IDENTITY_CHANGE_STALES_DESCENDANTS,
            passed=(
                parent_identity != changed_parent_identity
                and child_identity != changed_child_identity
                and child_identity != parent_identity
            ),
        ),
    )
