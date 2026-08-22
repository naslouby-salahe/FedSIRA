import pytest
from pydantic import ValidationError

from fedsira.artifacts.records import ArtifactManifest
from fedsira.domain.enums import ArtifactFamily, ArtifactLifecycleState


def make_manifest(**overrides: object) -> ArtifactManifest:
    fields: dict[str, object] = {
        "family": ArtifactFamily.SCALER,
        "identity": "a" * 64,
        "checksum": "b" * 64,
        "lifecycle_state": ArtifactLifecycleState.COMPLETE,
        "upstream_identities": (),
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
        setattr(manifest, "lifecycle_state", ArtifactLifecycleState.STALE)


def test_manifest_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        make_manifest(unexpected_field="x")


def test_manifest_rejects_malformed_digest() -> None:
    with pytest.raises(ValidationError):
        make_manifest(identity="not-a-digest")
