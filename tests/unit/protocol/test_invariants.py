import dataclasses
import inspect
import json

import pytest

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.domain.enums import DatasetId, TernaryOutcome
from fedsira.evaluation.communication import (
    CommunicationMessageMetadata,
    CommunicationMessageType,
    encode_message_metadata,
)
from fedsira.evaluation.records import AdmissionDelayDecomposition
from fedsira.learning.post_reference import run_post_reference_training
from fedsira.protocol.claim_contract import build_capability_claim_contract
from fedsira.protocol.verification import reproduction_row_is_certified

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
CAPABILITY_CLAIM_CONFIG = CONFIG.capability_claim


def test_honest_reproduction_constructor_has_no_source_artifact_parameter() -> None:
    parameter_names = set(inspect.signature(run_post_reference_training).parameters)
    assert not any("source" in name for name in parameter_names)


def test_capability_claim_contract_mutation_after_construction_is_rejected() -> None:
    contract = build_capability_claim_contract(
        "a" * 64, "POST_REFERENCE_REPLAY", DatasetId.N_BAIOT, 9, "b" * 64, CAPABILITY_CLAIM_CONFIG
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        contract.__setattr__("target_f1_minimum", 0.99)


def test_abstain_is_never_treated_as_a_positive_or_negative_vote() -> None:
    all_abstain_panel = [TernaryOutcome.ABSTAIN, TernaryOutcome.ABSTAIN, TernaryOutcome.ABSTAIN]
    assert not reproduction_row_is_certified(all_abstain_panel, 3, 2)
    mixed_panel = [TernaryOutcome.ABSTAIN, TernaryOutcome.POSITIVE, TernaryOutcome.POSITIVE]
    assert reproduction_row_is_certified(mixed_panel, 3, 2)
    truthy_but_not_positive = [
        TernaryOutcome.NEGATIVE,
        TernaryOutcome.ABSTAIN,
        TernaryOutcome.ABSTAIN,
    ]
    assert all(bool(report) for report in truthy_but_not_positive)
    assert not reproduction_row_is_certified(truthy_but_not_positive, 3, 2)


def _metadata() -> CommunicationMessageMetadata:
    return CommunicationMessageMetadata(
        message_type=CommunicationMessageType.MODEL_DISTRIBUTION,
        dataset_manifest_hash="a" * 64,
        semantic_cell_key_hash="b" * 64,
        master_seed=1,
        round_index=3,
        sender="SERVER",
        receiver="DANMINI_DOORBELL",
        claim_contract_hash="c" * 64,
        payload_tensor_count=1,
    )


def test_communication_serializer_is_independent_of_dict_construction_order() -> None:
    metadata = _metadata()
    envelope = encode_message_metadata(metadata)
    payload = json.loads(envelope[8:])
    reordered_payload = dict(reversed(list(payload.items())))
    assert json.dumps(payload, sort_keys=True, separators=(",", ":")) == json.dumps(
        reordered_payload, sort_keys=True, separators=(",", ":")
    )
    assert (
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8") == envelope[8:]
    )


def test_admission_delay_timer_fixture_satisfies_post_evidence_sum_within_tolerance() -> None:
    decomposition = AdmissionDelayDecomposition(
        logical_information_arrival_cycles=7,
        assignment_seconds=1.123456789,
        reproduce_seconds=2.987654321,
        verify_seconds=0.5,
        synthesize_seconds=3.25,
    )
    expected_total = (
        decomposition.assignment_seconds
        + decomposition.reproduce_seconds
        + decomposition.verify_seconds
        + decomposition.synthesize_seconds
    )
    assert abs(decomposition.post_evidence_wall_clock_seconds - expected_total) < 1e-9
    assert decomposition.logical_information_arrival_cycles == 7
