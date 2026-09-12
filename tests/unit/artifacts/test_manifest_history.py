import json
from pathlib import Path

from fedsira.artifacts.store import (
    ARTIFACT_CURRENT_FILE_NAME,
    ARTIFACT_MANIFEST_SUFFIX,
    ARTIFACT_SCHEMA_VERSION,
    ArtifactCurrentPointer,
    ArtifactSlot,
    load_published_manifests,
)
from fedsira.domain.enums import (
    ArtifactDependencyKind,
    ArtifactFamily,
    ArtifactLifecycleState,
    ArtifactProducer,
)

SLOT = ArtifactSlot(family=ArtifactFamily.SCALER, instance="history-probe")


def _manifest_text(identity: str) -> str:
    return json.dumps(
        {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "slot": SLOT.model_dump(),
            "producer": ArtifactProducer.PREPROCESSING.value,
            "identity": identity,
            "checksum": "b" * 64,
            "payload_bytes": 0,
            "lifecycle_state": ArtifactLifecycleState.COMPLETE.value,
            "dependencies": [
                {
                    "kind": ArtifactDependencyKind.CONTENT.value,
                    "dependency": "prepared-evidence",
                    "digest": "d" * 64,
                }
            ],
            "procedure_identity": "fedsira|history_probe|1",
            "configuration_digest": "c" * 64,
            "code_revision": None,
        }
    )


def _write_manifest(directory: Path, identity: str, text: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{identity}{ARTIFACT_MANIFEST_SUFFIX}"
    path.write_text(text)
    return path


def _point_current_at(directory: Path, identity: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ARTIFACT_CURRENT_FILE_NAME).write_text(
        ArtifactCurrentPointer(
            schema_version=ARTIFACT_SCHEMA_VERSION,
            slot=SLOT,
            identity=identity,
        ).model_dump_json()
    )


def test_current_publication_is_loaded(tmp_path: Path) -> None:
    identity = "1" * 64
    _write_manifest(tmp_path, identity, _manifest_text(identity))
    _point_current_at(tmp_path, identity)
    manifests, invalid = load_published_manifests((tmp_path,))
    assert tuple(manifest.identity for manifest in manifests) == (identity,)
    assert invalid == ()


def test_unreadable_historical_identity_does_not_block_the_gate(tmp_path: Path) -> None:
    current = "2" * 64
    _write_manifest(tmp_path, current, _manifest_text(current))
    _point_current_at(tmp_path, current)
    _write_manifest(tmp_path, "3" * 64, '{"schema_version": "fedsira|artifact_manifest|1"}')
    manifests, invalid = load_published_manifests((tmp_path,))
    assert tuple(manifest.identity for manifest in manifests) == (current,)
    assert invalid == ()


def test_unreadable_current_publication_is_invalid_evidence(tmp_path: Path) -> None:
    identity = "4" * 64
    _write_manifest(tmp_path, identity, '{"schema_version": "fedsira|artifact_manifest|1"}')
    _point_current_at(tmp_path, identity)
    manifests, invalid = load_published_manifests((tmp_path,))
    assert manifests == ()
    assert len(invalid) == 1
    assert identity in invalid[0].manifest_path


def test_unreadable_manifest_without_a_pointer_is_invalid_evidence(tmp_path: Path) -> None:
    identity = "5" * 64
    _write_manifest(tmp_path, identity, '{"schema_version": "fedsira|artifact_manifest|1"}')
    manifests, invalid = load_published_manifests((tmp_path,))
    assert manifests == ()
    assert len(invalid) == 1


def test_absent_root_yields_no_manifests(tmp_path: Path) -> None:
    assert load_published_manifests((tmp_path / "absent",)) == ((), ())
