import pytest

from fedsira.artifacts.provenance import ArtifactManifest, validate_artifact_lifecycle_readable
from fedsira.artifacts.storage import compute_checksum
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState


def test_only_complete_artifacts_are_readable() -> None:
    manifest = ArtifactManifest(
        family=ArtifactFamily.SCALER,
        identity="a" * 64,
        checksum=compute_checksum(b"payload"),
        lifecycle_state=ArtifactLifecycleState.COMPLETE,
        upstream_identities=(),
    )
    validate_artifact_lifecycle_readable(manifest)
    incomplete = manifest.model_copy(update={"lifecycle_state": ArtifactLifecycleState.STAGING})
    with pytest.raises(ValueError):
        validate_artifact_lifecycle_readable(incomplete)
