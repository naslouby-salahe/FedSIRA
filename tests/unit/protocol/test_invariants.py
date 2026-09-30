import hashlib
import inspect
import json
from pathlib import Path
from typing import Protocol, cast

import pytest
import torch
from pydantic import ValidationError

from fedsira.config import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import DatasetAdapter, HeterogeneityScope, RealAnchor
from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBaiotClass,
    nbaiot_adapter,
)
from fedsira.domain.enums import (
    AdmissionState,
    CoreMethodIdentity,
    DatasetId,
    ExperimentName,
    PluralityCondition,
    TernaryOutcome,
)
from fedsira.domain.models import (
    AdmissionDelayDecomposition,
    CommunicationMessageMetadata,
    CommunicationMessageType,
    PreparedEvidenceCounts,
    ScientificCell,
    encode_message_metadata,
)
from fedsira.domain.types import ArtifactDigest, DomainId, MasterSeed
from fedsira.experiments import reproduction_progression as reproduction_progression_module
from fedsira.learning.post_reference import run_post_reference_training
from fedsira.protocol.capability_contract import (
    CapabilityContract,
    build_capability_contract,
)
from fedsira.protocol.synthesis import (
    CertifiedReproductionRow,
    krum_input_excludes_source,
    select_krum_update,
)
from fedsira.protocol.verification import reproduction_row_is_certified

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
CAPABILITY_CONTRACT_CONFIG = CONFIG.capability_contract


class _ByteProducer(Protocol):
    def tobytes(self) -> bytes: ...


class _TensorBytes(Protocol):
    def numpy(self) -> _ByteProducer: ...


def _parameter_bytes(tensor: torch.Tensor) -> bytes:
    return cast(_TensorBytes, tensor).numpy().tobytes()


def test_honest_reproduction_constructor_has_no_source_artifact_parameter() -> None:
    parameter_names = set(inspect.signature(run_post_reference_training).parameters)
    assert not any("source" in name for name in parameter_names)


def test_source_delta_does_not_change_honest_reproduction_or_source_excluded_krum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_domain, *honest_domains = NBAIOT_DOMAIN_ORDER[:6]
    prepared_view_identity = tuple(f"prepared-view:{domain}" for domain in NBAIOT_DOMAIN_ORDER)
    adapter = nbaiot_adapter(Path("unused-prepared-root"))
    cell = ScientificCell(
        experiment=ExperimentName.SINGLE_REPRODUCTION_NECESSITY,
        method=CoreMethodIdentity.FULL_PLURALITY_PATH,
        condition=PluralityCondition.LEGITIMATE_TRANSFERABLE_CAPABILITY.value,
        master_seed=1,
    )
    anchor_parameters = torch.tensor([1.0, 2.0], dtype=torch.float64)
    anchor = RealAnchor(
        input_width=2,
        output_width=1,
        flat_parameters=anchor_parameters,
        dataset_manifest_hash="a" * 64,
        round_start_flat_parameters=(anchor_parameters.clone(),),
    )
    evidence = PreparedEvidenceCounts(
        screen_target_count=0,
        reproduction_target_count=0,
        reproduction_supported_count=0,
        final_gate_adequate_domain_count=0,
    )
    fixed_contract = build_capability_contract(
        dataset_manifest_hash="a" * 64,
        supported_control_role="POST_REFERENCE_REPLAY",
        dataset_id=DatasetId.N_BAIOT,
        domain_count=len(NBAIOT_DOMAIN_ORDER),
        feature_schema_hash="b" * 64,
        target_class=NBaiotClass.GAFGYT_COMBO.value,
        supported_class_count=len(NBAIOT_CLASS_ORDER) - 1,
        capability_contract_config=CAPABILITY_CONTRACT_CONFIG,
    )
    training_transcript: list[tuple[str, int, str, tuple[str, ...]]] = []

    def train_honest_domain(
        _adapter: DatasetAdapter,
        _master_seed: MasterSeed,
        _anchor: RealAnchor,
        domain: DomainId,
        *,
        heterogeneity_scope: HeterogeneityScope | None = None,
    ) -> torch.Tensor:
        del _adapter, heterogeneity_scope
        domain_index = NBAIOT_DOMAIN_ORDER.index(domain)
        training_transcript.append(
            (
                str(domain),
                _master_seed,
                hashlib.sha256(_parameter_bytes(_anchor.flat_parameters)).hexdigest(),
                prepared_view_identity,
            )
        )
        return torch.tensor([domain_index * 0.01, domain_index * -0.02], dtype=torch.float64)

    def fixed_reproducer_order(
        _adapter: DatasetAdapter, _cell: ScientificCell
    ) -> tuple[DomainId, ...]:
        return tuple(honest_domains)

    def fixed_source_domain(_adapter: DatasetAdapter, _cell: ScientificCell) -> DomainId:
        return source_domain

    def fixed_domain_adequacy(_adapter: DatasetAdapter, _domain: DomainId) -> bool:
        return True

    def fixed_contract_for_digest(
        _adapter: DatasetAdapter, _digest: ArtifactDigest
    ) -> CapabilityContract:
        return fixed_contract

    def discard_published_update(*_args: object) -> None:
        return None

    monkeypatch.setattr(
        reproduction_progression_module, "reproducer_order_for_cell", fixed_reproducer_order
    )
    monkeypatch.setattr(
        reproduction_progression_module, "source_domain_for_cell", fixed_source_domain
    )
    monkeypatch.setattr(
        reproduction_progression_module, "domain_is_reproduction_adequate", fixed_domain_adequacy
    )
    monkeypatch.setattr(
        reproduction_progression_module, "capability_contract_for_digest", fixed_contract_for_digest
    )
    monkeypatch.setattr(
        reproduction_progression_module,
        "train_domain_reproduction_delta",
        train_honest_domain,
    )
    monkeypatch.setattr(
        reproduction_progression_module,
        "publish_trained_update",
        discard_published_update,
    )

    def run(
        source_delta: torch.Tensor,
    ) -> tuple[
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        str,
        torch.Tensor,
        str,
    ]:
        _state, attempts, commitment_hashes, updates = (
            reproduction_progression_module.reproduction_progression(
                cell=cell,
                evidence=evidence,
                external_verification_active=False,
                row_requirement=6,
                compromised_reproducers=frozenset(),
                adapter=adapter,
                anchor=anchor,
                source_delta=source_delta,
                include_source_as_first_reproducer=True,
            )
        )
        assert _state is AdmissionState.SYNTHESIS_PENDING
        ordered_domains = tuple(str(attempt.domain) for attempt in attempts)
        source_commitment_hash = commitment_hashes[0]
        ordered_hashes = tuple(commitment_hashes[1:])
        update_hashes = tuple(
            hashlib.sha256(_parameter_bytes(updates[domain])).hexdigest()
            for domain in honest_domains
        )
        committee = tuple(
            CertifiedReproductionRow(reproducer_domain=domain, update_vector=updates[domain])
            for domain in honest_domains
        )
        assert krum_input_excludes_source(
            tuple(row.reproducer_domain for row in committee), source_domain
        )
        selected = select_krum_update(committee, maximum_byzantine_rows=1)
        return (
            ordered_domains,
            ordered_hashes,
            update_hashes,
            str(selected.reproducer_domain),
            selected.update_vector,
            source_commitment_hash,
        )

    zero_source_delta = torch.zeros_like(anchor_parameters)
    changed_source_delta = torch.tensor([0.0, 0.001], dtype=torch.float64)
    zero_result = run(zero_source_delta)
    zero_training_transcript = tuple(training_transcript)
    changed_result = run(changed_source_delta)
    changed_training_transcript = tuple(training_transcript[len(zero_training_transcript) :])

    assert (
        hashlib.sha256(_parameter_bytes(zero_source_delta)).digest()
        != hashlib.sha256(_parameter_bytes(changed_source_delta)).digest()
    )
    assert zero_training_transcript == changed_training_transcript
    assert zero_result[:4] == changed_result[:4]
    assert zero_result[5] != changed_result[5]
    assert zero_result[0][0] == str(source_domain)
    assert torch.equal(zero_result[4], changed_result[4])


def test_capability_contract_contract_mutation_after_construction_is_rejected() -> None:
    contract = build_capability_contract(
        dataset_manifest_hash="a" * 64,
        supported_control_role="POST_REFERENCE_REPLAY",
        dataset_id=DatasetId.N_BAIOT,
        domain_count=9,
        feature_schema_hash="b" * 64,
        target_class=NBaiotClass.GAFGYT_COMBO.value,
        supported_class_count=len(NBAIOT_CLASS_ORDER) - 1,
        capability_contract_config=CAPABILITY_CONTRACT_CONFIG,
    )
    with pytest.raises(ValidationError):
        contract.target_f1_minimum = 0.99


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
        capability_contract_hash="c" * 64,
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
