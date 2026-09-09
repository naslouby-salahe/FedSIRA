from fedsira.artifacts.records import ArtifactManifest
from fedsira.domain.enums import ArtifactLifecycleState


def validate_artifact_lifecycle_readable(manifest: ArtifactManifest) -> None:
    if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        raise ValueError(
            f"artifact {manifest.identity} is not Complete ({manifest.lifecycle_state.value}); "
            "it is never a valid input to downstream science"
        )
