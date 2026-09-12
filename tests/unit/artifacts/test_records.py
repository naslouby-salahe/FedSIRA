import pytest
from pydantic import ValidationError

from fedsira.artifacts.store import ARTIFACT_SCHEMA_VERSION, ArtifactManifest, ArtifactSlot
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState, ArtifactProducer


def make_manifest(**overrides: object) -> ArtifactManifest:
    fields: dict[str, object] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "slot": ArtifactSlot(family=ArtifactFamily.SCALER, instance="test-scaler"),
        "producer": ArtifactProducer.PREPROCESSING,
        "identity": "a" * 64,
        "checksum": "b" * 64,
        "payload_bytes": 0,
        "lifecycle_state": ArtifactLifecycleState.COMPLETE,
        "dependencies": (),
        "procedure_identity": "fedsira|test_scaler|1",
        "configuration_digest": "c" * 64,
        "code_revision": None,
    }
    fields.update(overrides)
    return ArtifactManifest.model_validate(fields)


def test_manifest_round_trips_fields() -> None:
    manifest = make_manifest()
    assert manifest.family is ArtifactFamily.SCALER
    assert manifest.lifecycle_state is ArtifactLifecycleState.COMPLETE


def test_manifest_is_frozen() -> None:
    manifest = make_manifest()
    with pytest.raises(ValidationError):
        setattr(manifest, "lifecycle_state", ArtifactLifecycleState.STAGING)


def test_manifest_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        make_manifest(unexpected_field="x")


def test_manifest_family_follows_its_slot() -> None:
    manifest = make_manifest(
        slot=ArtifactSlot(
            family=ArtifactFamily.MODEL_SCORE_ARTIFACT,
            instance="seed-1103",
            experiment="Primary Confirmatory Evaluation",
        )
    )
    assert manifest.family is ArtifactFamily.MODEL_SCORE_ARTIFACT
    assert manifest.slot.experiment == "Primary Confirmatory Evaluation"


def test_manifest_requires_a_schema_version() -> None:
    with pytest.raises(ValidationError):
        make_manifest(schema_version=None)


def test_manifest_rejects_malformed_digest() -> None:
    with pytest.raises(ValidationError):
        make_manifest(identity="not-a-digest")
