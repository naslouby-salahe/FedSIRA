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
    ArtifactFamily,
    ArtifactLifecycleState,
    ArtifactProducer,
)
from fedsira.experiments.smoke_records import SmokeCheckResult


def artifact_invariants() -> tuple[SmokeCheckResult, ...]:
    manifest = ArtifactManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        slot=ArtifactSlot(family=ArtifactFamily.SCALER, instance="smoke-invariant"),  # TODO: should be enum
        producer=ArtifactProducer.PREPROCESSING,
        identity="a" * 64,
        checksum="b" * 64,
        payload_bytes=0,
        lifecycle_state=ArtifactLifecycleState.COMPLETE,
        dependencies=(),
        procedure_identity="fedsira|smoke_artifact|1",  # TODO: should be enum
        configuration_digest="c" * 64,
        code_revision=None,
    )
    try:
        validate_artifact_lifecycle_readable(manifest)
        lifecycle_is_readable = True
    except ValueError:
        lifecycle_is_readable = False
    parent_slot = ArtifactSlot(family=ArtifactFamily.SCALER, instance="smoke-parent")
    child_slot = ArtifactSlot(family=ArtifactFamily.PREPARED_ROLE_VIEW, instance="smoke-descendant")
    parent_identity = artifact_identity(
        parent_slot,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT, dependency="raw-dataset", digest="a" * 64  # TODO: should be enum
            ),
        ),
        "fedsira|smoke_parent|1",  # TODO: should be enum
    )
    changed_parent_identity = artifact_identity(
        parent_slot,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT, dependency="raw-dataset", digest="d" * 64  # TODO: should be enum
            ),
        ),
        "fedsira|smoke_parent|1",  # TODO: should be enum
    )
    child_identity = artifact_identity(
        child_slot,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT, dependency="parent", digest=parent_identity  # TODO: should be enum
            ),
        ),
        "fedsira|smoke_child|1",  # TODO: should be enum
    )
    changed_child_identity = artifact_identity(
        child_slot,
        (
            ArtifactDependency(
                kind=ArtifactDependencyKind.CONTENT,
                dependency="parent",  # TODO: should be enum
                digest=changed_parent_identity,
            ),
        ),
        "fedsira|smoke_child|1",  # TODO: should be enum
    )
    return (
        SmokeCheckResult(
            name="complete artifact manifest is readable",
            passed=lifecycle_is_readable,
        ),
        SmokeCheckResult(
            name="changing one parent identity marks transitive descendants stale",
            passed=(
                parent_identity != changed_parent_identity
                and child_identity != changed_child_identity
                and child_identity != parent_identity
            ),
        ),
    )
