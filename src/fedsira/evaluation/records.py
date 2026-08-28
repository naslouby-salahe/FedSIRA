from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from fedsira.domain.records import (
    ArtifactDigest,
    FrozenDomainModel,
    MasterSeed,
    NonEmptyString,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    RoundIndex,
)

COMMUNICATION_SCHEMA = "FEDSIRA_COMM_V1"
SERVER_ID: NonEmptyString = "SERVER"
METADATA_LENGTH_PREFIX_BYTES = 8
TENSOR_METADATA_LENGTH_PREFIX_BYTES = 8
TENSOR_DTYPE: NonEmptyString = "float32"

CommunicationJsonValue = str | int | None | list[int]


@dataclass(frozen=True)
class MetricResult:
    value: float | None
    denominator: NonNegativeInt


@dataclass(frozen=True)
class ConfusionCounts:
    true_positive: NonNegativeInt
    false_positive: NonNegativeInt
    false_negative: NonNegativeInt
    true_negative: NonNegativeInt


class ProposalOracleLabel(StrEnum):
    ORACLE_VALID = "ORACLE_VALID"
    ORACLE_INVALID = "ORACLE_INVALID"
    NA = "NA"


class FalseSameCapabilityReason(StrEnum):
    NO_CROSS_ROOT_CAUSE_EQUIVALENCE_ASSERTION = "No Cross-Root-Cause Equivalence Assertion"


@dataclass(frozen=True)
class AdmissionDelayDecomposition:
    logical_information_arrival_cycles: NonNegativeInt
    assignment_seconds: NonNegativeFloat
    reproduce_seconds: NonNegativeFloat
    verify_seconds: NonNegativeFloat
    synthesize_seconds: NonNegativeFloat

    @property
    def post_evidence_wall_clock_seconds(self) -> NonNegativeFloat:
        return (
            self.assignment_seconds
            + self.reproduce_seconds
            + self.verify_seconds
            + self.synthesize_seconds
        )


class CommunicationMessageType(StrEnum):
    SOURCE_COMMITMENT = "SOURCE_COMMITMENT"
    MODEL_DISTRIBUTION = "MODEL_DISTRIBUTION"
    UPDATE_SUBMISSION = "UPDATE_SUBMISSION"
    CLAIM_CONTRACT = "CLAIM_CONTRACT"
    REVIEW_ASSIGNMENT = "REVIEW_ASSIGNMENT"
    REVIEW_REPORT = "REVIEW_REPORT"
    VERIFIER_ASSIGNMENT = "VERIFIER_ASSIGNMENT"
    VERIFIER_REPORT = "VERIFIER_REPORT"
    FINAL_GATE_ASSIGNMENT = "FINAL_GATE_ASSIGNMENT"
    FINAL_GATE_REPORT = "FINAL_GATE_REPORT"
    DECISION = "DECISION"


class TensorParameterKind(StrEnum):
    MODEL = "model"
    UPDATE = "update"


class CommunicationMessageMetadata(FrozenDomainModel):
    message_type: CommunicationMessageType
    dataset_manifest_hash: ArtifactDigest
    semantic_cell_key_hash: ArtifactDigest
    master_seed: MasterSeed
    round_index: RoundIndex | None
    sender: NonEmptyString
    receiver: NonEmptyString
    claim_contract_hash: ArtifactDigest | None
    payload_tensor_count: NonNegativeInt


class TensorPayloadMetadata(FrozenDomainModel):
    name: NonEmptyString
    shape: tuple[PositiveInt, ...]
    nbytes: NonNegativeInt
    dtype: NonEmptyString = TENSOR_DTYPE


def parameter_tensor_name(
    kind: TensorParameterKind, parameter_name: NonEmptyString
) -> NonEmptyString:
    return f"{kind.value}.{parameter_name}"


def stable_json_bytes(payload: Mapping[str, CommunicationJsonValue]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def length_prefixed_bytes(payload: bytes, prefix_bytes: PositiveInt) -> bytes:
    return len(payload).to_bytes(prefix_bytes, byteorder="big", signed=False) + payload


def encode_message_metadata(metadata: CommunicationMessageMetadata) -> bytes:
    payload: dict[str, CommunicationJsonValue] = {
        "schema": COMMUNICATION_SCHEMA,
        "message_type": metadata.message_type.value,
        "dataset_manifest_hash": metadata.dataset_manifest_hash,
        "semantic_cell_key_hash": metadata.semantic_cell_key_hash,
        "master_seed": metadata.master_seed,
        "round_index": metadata.round_index,
        "sender": metadata.sender,
        "receiver": metadata.receiver,
        "claim_contract_hash": metadata.claim_contract_hash,
        "payload_tensor_count": metadata.payload_tensor_count,
    }
    return length_prefixed_bytes(stable_json_bytes(payload), METADATA_LENGTH_PREFIX_BYTES)


def encode_tensor_metadata(tensor_metadata: TensorPayloadMetadata) -> bytes:
    payload: dict[str, CommunicationJsonValue] = {
        "name": tensor_metadata.name,
        "dtype": tensor_metadata.dtype,
        "shape": list(tensor_metadata.shape),
        "nbytes": tensor_metadata.nbytes,
    }
    return length_prefixed_bytes(stable_json_bytes(payload), TENSOR_METADATA_LENGTH_PREFIX_BYTES)


def encode_message_envelope(
    metadata: CommunicationMessageMetadata,
    tensor_payloads: Mapping[NonEmptyString, bytes],
    tensor_metadata_by_name: Mapping[NonEmptyString, TensorPayloadMetadata],
) -> bytes:
    envelope = bytearray(encode_message_metadata(metadata))
    for tensor_name in sorted(tensor_payloads):
        envelope += encode_tensor_metadata(tensor_metadata_by_name[tensor_name])
        envelope += tensor_payloads[tensor_name]
    return bytes(envelope)


def is_model_transmission(metadata: CommunicationMessageMetadata) -> bool:
    return metadata.payload_tensor_count > 0


def communication_bytes(envelopes: Sequence[bytes]) -> NonNegativeInt:
    return sum(len(envelope) for envelope in envelopes)


def model_transmission_count(
    metadata_records: Sequence[CommunicationMessageMetadata],
) -> NonNegativeInt:
    return sum(1 for metadata in metadata_records if is_model_transmission(metadata))
