from fedsira.domain.enums import ProvenanceValidationOutcome
from fedsira.domain.records import (
    ArtifactDigest,
    ArtifactInvalidated,
    CreationContext,
    DatasetSplitUpstreamChanged,
    EnvironmentRecord,
    FrozenDomainModel,
    GitCommit,
    ProducerCodeOrRuntimeChanged,
    ProvenancePayloadStale,
    ScientificConfigurationChanged,
    ScientificConfigurationSubset,
)


class ProvenanceRecord(FrozenDomainModel):
    scientific_configuration_subset: ScientificConfigurationSubset
    dataset_split_upstream_identities: tuple[ArtifactDigest, ...]
    producer_component_fingerprint: ArtifactDigest
    external_dependency_fingerprint: ArtifactDigest
    repository_commit: GitCommit
    dependency_lock_identity: ArtifactDigest
    environment_record: EnvironmentRecord
    creation_context: CreationContext


def classify_provenance_change(
    payload_partial_or_stale: ProvenancePayloadStale,
    scientific_configuration_changed: ScientificConfigurationChanged,
    dataset_split_upstream_changed: DatasetSplitUpstreamChanged,
    producer_code_or_runtime_changed: ProducerCodeOrRuntimeChanged,
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


def outcome_invalidates_artifact(
    outcome: ProvenanceValidationOutcome,
) -> ArtifactInvalidated:
    return outcome is not ProvenanceValidationOutcome.NON_MATERIAL_CHANGE
