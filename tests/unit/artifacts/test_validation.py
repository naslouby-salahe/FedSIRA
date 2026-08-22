import pytest

from fedsira.artifacts.records import ArtifactManifest
from fedsira.artifacts.storage import compute_checksum
from fedsira.artifacts.validation import (
    validate_artifact_for_scientific_read,
    validate_artifact_lifecycle_readable,
    validate_artifact_payload_integrity,
    validate_artifact_provenance_outcome,
)
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState, ProvenanceValidationOutcome


def manifest(lifecycle_state: ArtifactLifecycleState, payload: bytes) -> ArtifactManifest:
    return ArtifactManifest(
        family=ArtifactFamily.SCALER,
        identity="a" * 64,
        checksum=compute_checksum(payload),
        lifecycle_state=lifecycle_state,
        upstream_identities=(),
    )


def test_complete_artifact_with_matching_checksum_is_readable() -> None:
    payload = b"payload"
    complete = manifest(ArtifactLifecycleState.COMPLETE, payload)
    validate_artifact_lifecycle_readable(complete)
    validate_artifact_payload_integrity(complete, payload)


@pytest.mark.parametrize(
    "state",
    [
        ArtifactLifecycleState.STAGING,
        ArtifactLifecycleState.STALE,
        ArtifactLifecycleState.RETIRED,
    ],
)
def test_non_complete_artifact_is_rejected(state: ArtifactLifecycleState) -> None:
    payload = b"payload"
    with pytest.raises(ValueError):
        validate_artifact_lifecycle_readable(manifest(state, payload))


def test_checksum_mismatch_is_rejected() -> None:
    complete = manifest(ArtifactLifecycleState.COMPLETE, b"payload")
    with pytest.raises(ValueError):
        validate_artifact_payload_integrity(complete, b"tampered")


def test_non_material_provenance_outcome_is_accepted() -> None:
    validate_artifact_provenance_outcome(ProvenanceValidationOutcome.NON_MATERIAL_CHANGE)


@pytest.mark.parametrize(
    "outcome",
    [
        ProvenanceValidationOutcome.PARTIAL_OR_STALE_PAYLOAD,
        ProvenanceValidationOutcome.SCIENTIFIC_CONFIGURATION_MISMATCH,
        ProvenanceValidationOutcome.DATASET_SPLIT_UPSTREAM_MISMATCH,
        ProvenanceValidationOutcome.PRODUCER_CODE_RUNTIME_MISMATCH,
    ],
)
def test_material_provenance_outcomes_are_rejected(outcome: ProvenanceValidationOutcome) -> None:
    with pytest.raises(ValueError):
        validate_artifact_provenance_outcome(outcome)


def test_validate_artifact_for_scientific_read_composes_all_three_checks() -> None:
    payload = b"payload"
    complete = manifest(ArtifactLifecycleState.COMPLETE, payload)
    validate_artifact_for_scientific_read(
        complete, payload, ProvenanceValidationOutcome.NON_MATERIAL_CHANGE
    )
    with pytest.raises(ValueError):
        validate_artifact_for_scientific_read(
            complete, payload, ProvenanceValidationOutcome.PRODUCER_CODE_RUNTIME_MISMATCH
        )
