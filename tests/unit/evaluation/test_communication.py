import json

from fedsira.evaluation.records import (
    COMMUNICATION_SCHEMA,
    CommunicationMessageMetadata,
    CommunicationMessageType,
    TensorParameterKind,
    TensorPayloadMetadata,
    communication_bytes,
    encode_message_envelope,
    encode_message_metadata,
    encode_tensor_metadata,
    is_model_transmission,
    model_transmission_count,
    parameter_tensor_name,
)

DIGEST = "a" * 64


def make_metadata(payload_tensor_count: int = 0) -> CommunicationMessageMetadata:
    return CommunicationMessageMetadata(
        message_type=CommunicationMessageType.MODEL_DISTRIBUTION,
        dataset_manifest_hash=DIGEST,
        semantic_cell_key_hash=DIGEST,
        master_seed=1,
        round_index=0,
        sender="SERVER",
        receiver="DANMINI_DOORBELL",
        claim_contract_hash=None,
        payload_tensor_count=payload_tensor_count,
    )


def test_parameter_tensor_name_prefixes_kind() -> None:
    assert parameter_tensor_name(TensorParameterKind.MODEL, "hidden_1.weight") == (
        "model.hidden_1.weight"
    )
    assert parameter_tensor_name(TensorParameterKind.UPDATE, "hidden_1.weight") == (
        "update.hidden_1.weight"
    )


def test_encode_message_metadata_has_length_prefix_and_stable_json() -> None:
    metadata = make_metadata()
    envelope = encode_message_metadata(metadata)
    length = int.from_bytes(envelope[:8], byteorder="big")
    payload = envelope[8:]
    assert length == len(payload)
    decoded = json.loads(payload)
    assert decoded["schema"] == COMMUNICATION_SCHEMA
    assert decoded["claim_contract_hash"] is None
    assert list(payload).count(ord(" ")) == 0


def test_encode_tensor_metadata_round_trips() -> None:
    tensor_metadata = TensorPayloadMetadata(
        name="model.hidden_1.weight", shape=(256, 4), nbytes=4096
    )
    envelope = encode_tensor_metadata(tensor_metadata)
    length = int.from_bytes(envelope[:8], byteorder="big")
    payload = json.loads(envelope[8:])
    assert length == len(envelope) - 8
    assert payload["shape"] == [256, 4]
    assert payload["dtype"] == "float32"


def test_encode_message_envelope_orders_tensors_lexicographically() -> None:
    metadata = make_metadata(payload_tensor_count=2)
    tensor_metadata_by_name = {
        "model.b": TensorPayloadMetadata(name="model.b", shape=(1,), nbytes=4),
        "model.a": TensorPayloadMetadata(name="model.a", shape=(1,), nbytes=4),
    }
    tensor_payloads = {"model.b": b"\x02\x00\x00\x00", "model.a": b"\x01\x00\x00\x00"}
    envelope = encode_message_envelope(metadata, tensor_payloads, tensor_metadata_by_name)
    assert envelope.index(b"model.a") < envelope.index(b"model.b")


def test_is_model_transmission_and_counts() -> None:
    metadata_only = make_metadata(payload_tensor_count=0)
    with_tensor = make_metadata(payload_tensor_count=1)
    assert is_model_transmission(metadata_only) is False
    assert is_model_transmission(with_tensor) is True
    assert model_transmission_count([metadata_only, with_tensor, with_tensor]) == 2


def test_communication_bytes_sums_envelope_lengths() -> None:
    envelopes = [b"1234", b"12"]
    assert communication_bytes(envelopes) == 6
