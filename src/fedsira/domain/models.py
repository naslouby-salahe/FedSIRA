from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from fedsira.domain.types import (
    AdequateFinalGateDomainCount,
    ArtifactDigest,
    ByteCount,
    ConditionName,
    ConfusionCount,
    ExampleCount,
    ExperimentName,
    FrozenDomainModel,
    LengthPrefixBytes,
    LogicalEvidenceCycleCount,
    MasterSeed,
    MessageEndpoint,
    MethodName,
    MetricValue,
    ModelTransmissionCount,
    ModelTransmissionPresent,
    ParameterName,
    PreparedReproductionTargetCount,
    PreparedScreenTargetCount,
    PreparedSupportedReplayCount,
    RepetitionIndex,
    RoundIndex,
    SchemaVersion,
    ScientificCellSemanticKey,
    TensorAxisSize,
    TensorName,
    TensorPayloadCount,
    WallClockSeconds,
)

COMMUNICATION_SCHEMA: SchemaVersion = "FEDSIRA_COMM_V1"  # TODO: should be enum
SERVER_ID: MessageEndpoint = "SERVER"  # TODO: should be enum
METADATA_LENGTH_PREFIX_BYTES: LengthPrefixBytes = 8
TENSOR_METADATA_LENGTH_PREFIX_BYTES: LengthPrefixBytes = 8
TENSOR_DTYPE: SchemaVersion = "float32"  # TODO: should be enum

EncodedBytes = Annotated[bytes, Field()]


class MetricResult(FrozenDomainModel):
    value: MetricValue | None
    denominator: ExampleCount


class ConfusionCounts(FrozenDomainModel):
    true_positive: ConfusionCount
    false_positive: ConfusionCount
    false_negative: ConfusionCount
    true_negative: ConfusionCount


class ProposalOracleLabel(StrEnum):
    ORACLE_VALID = "ORACLE_VALID"  # TODO: should be enum
    ORACLE_INVALID = "ORACLE_INVALID"  # TODO: should be enum
    NA = "NA"  # TODO: should be enum


class FalseSameCapabilityReason(StrEnum):
    NO_CROSS_ROOT_CAUSE_EQUIVALENCE_ASSERTION = "No Cross-Root-Cause Equivalence Assertion"  # TODO: should be enum


class AdmissionDelayDecomposition(FrozenDomainModel):
    logical_information_arrival_cycles: LogicalEvidenceCycleCount
    assignment_seconds: WallClockSeconds
    reproduce_seconds: WallClockSeconds
    verify_seconds: WallClockSeconds
    synthesize_seconds: WallClockSeconds

    @property
    def post_evidence_wall_clock_seconds(self) -> WallClockSeconds:
        return (
            self.assignment_seconds
            + self.reproduce_seconds
            + self.verify_seconds
            + self.synthesize_seconds
        )


class CommunicationMessageType(StrEnum):
    SOURCE_COMMITMENT = "SOURCE_COMMITMENT"  # TODO: should be enum
    MODEL_DISTRIBUTION = "MODEL_DISTRIBUTION"  # TODO: should be enum
    UPDATE_SUBMISSION = "UPDATE_SUBMISSION"  # TODO: should be enum
    CAPABILITY_CONTRACT = "CAPABILITY_CONTRACT"  # TODO: should be enum
    REVIEW_ASSIGNMENT = "REVIEW_ASSIGNMENT"  # TODO: should be enum
    REVIEW_REPORT = "REVIEW_REPORT"  # TODO: should be enum
    VERIFIER_ASSIGNMENT = "VERIFIER_ASSIGNMENT"  # TODO: should be enum
    VERIFIER_REPORT = "VERIFIER_REPORT"  # TODO: should be enum
    FINAL_GATE_ASSIGNMENT = "FINAL_GATE_ASSIGNMENT"  # TODO: should be enum
    FINAL_GATE_REPORT = "FINAL_GATE_REPORT"  # TODO: should be enum
    DECISION = "DECISION"  # TODO: should be enum


class TensorParameterKind(StrEnum):
    MODEL = "model"  # TODO: should be enum
    UPDATE = "update"  # TODO: should be enum


class CommunicationMessageMetadata(FrozenDomainModel):
    message_type: CommunicationMessageType
    dataset_manifest_hash: ArtifactDigest
    semantic_cell_key_hash: ArtifactDigest
    master_seed: MasterSeed
    round_index: RoundIndex | None
    sender: MessageEndpoint
    receiver: MessageEndpoint
    capability_contract_hash: ArtifactDigest | None
    payload_tensor_count: TensorPayloadCount


class TensorPayloadMetadata(FrozenDomainModel):
    name: TensorName
    shape: tuple[TensorAxisSize, ...]
    nbytes: ByteCount
    dtype: SchemaVersion = TENSOR_DTYPE


class TensorEnvelopePayload(FrozenDomainModel):
    metadata: TensorPayloadMetadata
    payload: EncodedBytes


class _CommunicationMetadataWire(FrozenDomainModel):
    capability_contract_hash: ArtifactDigest | None
    dataset_manifest_hash: ArtifactDigest
    master_seed: MasterSeed
    message_type: CommunicationMessageType
    payload_tensor_count: TensorPayloadCount
    receiver: MessageEndpoint
    round_index: RoundIndex | None
    schema_version: SchemaVersion
    semantic_cell_key_hash: ArtifactDigest
    sender: MessageEndpoint


class _TensorMetadataWire(FrozenDomainModel):
    dtype: SchemaVersion
    name: TensorName
    nbytes: ByteCount
    shape: tuple[TensorAxisSize, ...]


def parameter_tensor_name(kind: TensorParameterKind, parameter_name: ParameterName) -> TensorName:
    return f"{kind.value}.{parameter_name}"


def _wire_bytes(model: FrozenDomainModel) -> EncodedBytes:
    return model.model_dump_json().encode("utf-8")


def length_prefixed_bytes(payload: EncodedBytes, prefix_bytes: LengthPrefixBytes) -> EncodedBytes:
    return len(payload).to_bytes(prefix_bytes, byteorder="big", signed=False) + payload


def encode_message_metadata(metadata: CommunicationMessageMetadata) -> EncodedBytes:
    wire = _CommunicationMetadataWire(
        capability_contract_hash=metadata.capability_contract_hash,
        dataset_manifest_hash=metadata.dataset_manifest_hash,
        master_seed=metadata.master_seed,
        message_type=metadata.message_type,
        payload_tensor_count=metadata.payload_tensor_count,
        receiver=metadata.receiver,
        round_index=metadata.round_index,
        schema_version=COMMUNICATION_SCHEMA,
        semantic_cell_key_hash=metadata.semantic_cell_key_hash,
        sender=metadata.sender,
    )
    return length_prefixed_bytes(_wire_bytes(wire), METADATA_LENGTH_PREFIX_BYTES)


def encode_tensor_metadata(tensor_metadata: TensorPayloadMetadata) -> EncodedBytes:
    wire = _TensorMetadataWire(
        dtype=tensor_metadata.dtype,
        name=tensor_metadata.name,
        nbytes=tensor_metadata.nbytes,
        shape=tensor_metadata.shape,
    )
    return length_prefixed_bytes(_wire_bytes(wire), TENSOR_METADATA_LENGTH_PREFIX_BYTES)


def encode_message_envelope(
    metadata: CommunicationMessageMetadata,
    tensor_payloads: tuple[TensorEnvelopePayload, ...],
) -> EncodedBytes:
    if metadata.payload_tensor_count != len(tensor_payloads):
        raise ValueError("message metadata tensor count does not match envelope payloads")
    ordered_payloads = tuple(sorted(tensor_payloads, key=lambda item: item.metadata.name))
    if len(frozenset(item.metadata.name for item in ordered_payloads)) != len(ordered_payloads):
        raise ValueError("tensor envelope payload names must be unique")
    envelope = bytearray(encode_message_metadata(metadata))
    for tensor_payload in ordered_payloads:
        if tensor_payload.metadata.nbytes != len(tensor_payload.payload):
            raise ValueError(
                f"tensor payload byte count mismatch for {tensor_payload.metadata.name}"
            )
        envelope += encode_tensor_metadata(tensor_payload.metadata)
        envelope += tensor_payload.payload
    return bytes(envelope)


def is_model_transmission(metadata: CommunicationMessageMetadata) -> ModelTransmissionPresent:
    return metadata.payload_tensor_count > 0


def communication_bytes(envelopes: tuple[EncodedBytes, ...]) -> ByteCount:
    return sum(len(envelope) for envelope in envelopes)


def model_transmission_count(
    metadata_records: tuple[CommunicationMessageMetadata, ...],
) -> ModelTransmissionCount:
    return sum(1 for metadata in metadata_records if is_model_transmission(metadata))


class ScientificCell(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ConditionName
    master_seed: MasterSeed
    repetition: RepetitionIndex | None = None

    @property
    def semantic_key(self) -> ScientificCellSemanticKey:
        repetition = "" if self.repetition is None else str(self.repetition)
        return "|".join(
            (self.experiment, self.method, self.condition, str(self.master_seed), repetition)
        )


class PreparedEvidenceCounts(FrozenDomainModel):
    screen_target_count: PreparedScreenTargetCount
    reproduction_target_count: PreparedReproductionTargetCount
    reproduction_supported_count: PreparedSupportedReplayCount
    final_gate_adequate_domain_count: AdequateFinalGateDomainCount
