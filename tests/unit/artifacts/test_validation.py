import pytest

from fedsira.artifacts.records import ArtifactManifest
from fedsira.artifacts.validation import validate_artifact_lifecycle_readable
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState
from fedsira.io.storage import compute_checksum


def test_only_complete_artifacts_are_readable() -> None:
    manifest = ArtifactManifest(
        family=ArtifactFamily.SCALER,
        identity="a" * 64,
        checksum=compute_checksum(b"payload"),
        lifecycle_state=ArtifactLifecycleState.COMPLETE,
        upstream_identities=(),
    )
    validate_artifact_lifecycle_readable(manifest)
    incomplete = manifest.model_copy(update={"lifecycle_state": ArtifactLifecycleState.STALE})
    with pytest.raises(ValueError):
        validate_artifact_lifecycle_readable(incomplete)
