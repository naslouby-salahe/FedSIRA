import pytest

from fedsira.artifacts.store import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactManifest,
    ArtifactSlot,
    compute_checksum,
    validate_artifact_lifecycle_readable,
)
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState, ArtifactProducer


def test_only_complete_artifacts_are_readable() -> None:
    manifest = ArtifactManifest(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        slot=ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler"),
        producer=ArtifactProducer.PREPROCESSING,
        identity="a" * 64,
        checksum=compute_checksum(b"payload"),
        payload_bytes=7,
        lifecycle_state=ArtifactLifecycleState.COMPLETE,
        dependencies=(),
        procedure_identity="fedsira|test_scaler|1",
        configuration_digest="d" * 64,
        code_revision=None,
    )
    validate_artifact_lifecycle_readable(manifest)
    incomplete = manifest.model_copy(update={"lifecycle_state": ArtifactLifecycleState.STAGING})
    with pytest.raises(ValueError):
        validate_artifact_lifecycle_readable(incomplete)
