from pydantic import BaseModel, ConfigDict

from fedsira.domain.enums import ProvenanceValidationOutcome
from fedsira.domain.records import ArtifactDigest, CanonicalToken


class ProvenanceRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scientific_configuration_subset: CanonicalToken
    dataset_split_upstream_identities: tuple[ArtifactDigest, ...]
    producer_component_fingerprint: ArtifactDigest
    external_dependency_fingerprint: ArtifactDigest
    repository_commit: CanonicalToken
    dependency_lock_identity: ArtifactDigest
    environment_record: CanonicalToken
    creation_context: CanonicalToken


def classify_provenance_change(
    payload_partial_or_stale: bool,
    scientific_configuration_changed: bool,
    dataset_split_upstream_changed: bool,
    producer_code_or_runtime_changed: bool,
) -> ProvenanceValidationOutcome:
    if payload_partial_or_stale:
        return ProvenanceValidationOutcome.PARTIAL_OR_STALE_PAYLOAD
    if scientific_configuration_changed:
        return ProvenanceValidationOutcome.SCIENTIFIC_CONFIGURATION_MISMATCH
    if dataset_split_upstream_changed:
        return ProvenanceValidationOutcome.DATASET_SPLIT_UPSTREAM_MISMATCH
    if producer_code_or_runtime_changed:
        return ProvenanceValidationOutcome.PRODUCER_CODE_RUNTIME_MISMATCH
    return ProvenanceValidationOutcome.NON_MATERIAL_CHANGE


def outcome_invalidates_artifact(outcome: ProvenanceValidationOutcome) -> bool:
    return outcome is not ProvenanceValidationOutcome.NON_MATERIAL_CHANGE
