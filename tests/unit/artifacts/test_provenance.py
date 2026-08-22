import pytest
from pydantic import ValidationError

from fedsira.artifacts.provenance import (
    ProvenanceRecord,
    classify_provenance_change,
    outcome_invalidates_artifact,
)
from fedsira.domain.enums import ProvenanceValidationOutcome


def make_record(**overrides: object) -> ProvenanceRecord:
    fields: dict[str, object] = {
        "scientific_configuration_subset": "config-a",
        "dataset_split_upstream_identities": ("a" * 64,),
        "producer_component_fingerprint": "b" * 64,
        "external_dependency_fingerprint": "c" * 64,
        "repository_commit": "d" * 40,
        "dependency_lock_identity": "e" * 64,
        "environment_record": "ubuntu-24.04",
        "creation_context": "run-1",
    }
    fields.update(overrides)
    return ProvenanceRecord.model_validate(fields)


def test_provenance_record_is_frozen() -> None:
    record = make_record()
    with pytest.raises(ValidationError):
        setattr(record, "repository_commit", "f" * 40)


def test_partial_or_stale_payload_is_rejected_regardless_of_other_flags() -> None:
    outcome = classify_provenance_change(
        payload_partial_or_stale=True,
        scientific_configuration_changed=False,
        dataset_split_upstream_changed=False,
        producer_code_or_runtime_changed=False,
    )
    assert outcome is ProvenanceValidationOutcome.PARTIAL_OR_STALE_PAYLOAD
    assert outcome_invalidates_artifact(outcome)


def test_scientific_configuration_mismatch_invalidates() -> None:
    outcome = classify_provenance_change(False, True, False, False)
    assert outcome is ProvenanceValidationOutcome.SCIENTIFIC_CONFIGURATION_MISMATCH
    assert outcome_invalidates_artifact(outcome)


def test_dataset_split_upstream_mismatch_invalidates() -> None:
    outcome = classify_provenance_change(False, False, True, False)
    assert outcome is ProvenanceValidationOutcome.DATASET_SPLIT_UPSTREAM_MISMATCH
    assert outcome_invalidates_artifact(outcome)


def test_producer_code_runtime_mismatch_invalidates() -> None:
    outcome = classify_provenance_change(False, False, False, True)
    assert outcome is ProvenanceValidationOutcome.PRODUCER_CODE_RUNTIME_MISMATCH
    assert outcome_invalidates_artifact(outcome)


def test_non_material_change_is_preserved() -> None:
    outcome = classify_provenance_change(False, False, False, False)
    assert outcome is ProvenanceValidationOutcome.NON_MATERIAL_CHANGE
    assert not outcome_invalidates_artifact(outcome)
