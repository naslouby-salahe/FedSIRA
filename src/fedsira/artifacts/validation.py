from fedsira.artifacts.records import ArtifactManifest, ArtifactPayloadBytes
from fedsira.domain.enums import ArtifactLifecycleState, ProvenanceValidationOutcome
from fedsira.io.storage import verify_checksum


def validate_artifact_lifecycle_readable(manifest: ArtifactManifest) -> None:
    if manifest.lifecycle_state is not ArtifactLifecycleState.COMPLETE:
        raise ValueError(
            f"artifact {manifest.identity} is not Complete ({manifest.lifecycle_state.value}); "
            "it is never a valid input to downstream science"
        )


def validate_artifact_payload_integrity(
    manifest: ArtifactManifest,
    payload: ArtifactPayloadBytes,
) -> None:
    verify_checksum(payload, manifest)


def validate_artifact_provenance_outcome(outcome: ProvenanceValidationOutcome) -> None:
    if outcome is not ProvenanceValidationOutcome.NON_MATERIAL_CHANGE:
        raise ValueError(f"artifact invalidated by provenance outcome: {outcome.value}")


def validate_artifact_for_scientific_read(
    manifest: ArtifactManifest,
    payload: ArtifactPayloadBytes,
    provenance_outcome: ProvenanceValidationOutcome,
) -> None:
    validate_artifact_lifecycle_readable(manifest)
    validate_artifact_payload_integrity(manifest, payload)
    validate_artifact_provenance_outcome(provenance_outcome)
