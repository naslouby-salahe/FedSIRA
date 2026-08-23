import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from fedsira.domain.records import (
    ArtifactDigest,
    CanonicalToken,
    MasterSeed,
    NonNegativeInt,
    PositiveInt,
    RoundIndex,
)

COMMUNICATION_SCHEMA = "FEDSIRA_COMM_V1"
SERVER_TOKEN: CanonicalToken = "SERVER"
METADATA_LENGTH_PREFIX_BYTES = 8
TENSOR_METADATA_LENGTH_PREFIX_BYTES = 8
TENSOR_DTYPE = "float32"

CommunicationJsonValue = str | int | None | list[int]


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


@dataclass(frozen=True)
class CommunicationMessageMetadata:
    message_type: CommunicationMessageType
    dataset_manifest_hash: ArtifactDigest
    semantic_cell_key_hash: ArtifactDigest
    master_seed: MasterSeed
    round_index: RoundIndex | None
    sender: CanonicalToken
    receiver: CanonicalToken
    claim_contract_hash: ArtifactDigest | None
    payload_tensor_count: NonNegativeInt


@dataclass(frozen=True)
class TensorPayloadMetadata:
    name: CanonicalToken
    shape: tuple[PositiveInt, ...]
    nbytes: NonNegativeInt
    dtype: CanonicalToken = TENSOR_DTYPE


def canonical_parameter_tensor_name(
    kind: TensorParameterKind, canonical_parameter_name: CanonicalToken
) -> CanonicalToken:
    return f"{kind.value}.{canonical_parameter_name}"


def _canonical_json_bytes(payload: Mapping[str, CommunicationJsonValue]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _length_prefixed(payload: bytes, prefix_bytes: NonNegativeInt) -> bytes:
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
    return _length_prefixed(_canonical_json_bytes(payload), METADATA_LENGTH_PREFIX_BYTES)


def encode_tensor_metadata(tensor_metadata: TensorPayloadMetadata) -> bytes:
    payload: dict[str, CommunicationJsonValue] = {
        "name": tensor_metadata.name,
        "dtype": tensor_metadata.dtype,
        "shape": list(tensor_metadata.shape),
        "nbytes": tensor_metadata.nbytes,
    }
    return _length_prefixed(_canonical_json_bytes(payload), TENSOR_METADATA_LENGTH_PREFIX_BYTES)


def encode_message_envelope(
    metadata: CommunicationMessageMetadata,
    tensor_payloads: Mapping[CanonicalToken, bytes],
    tensor_metadata_by_name: Mapping[CanonicalToken, TensorPayloadMetadata],
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
