import json
import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

from fedsira.artifacts import store
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


def test_obsolete_current_schema_is_rejected_as_invalid_evidence(tmp_path: Path) -> None:
    identity = "6" * 64
    obsolete = _manifest_text(identity).replace(
        ARTIFACT_SCHEMA_VERSION,
        "fedsira|artifact_manifest|3",
    )
    _write_manifest(tmp_path, identity, obsolete)
    _point_current_at(tmp_path, identity)

    manifests, invalid = load_published_manifests((tmp_path,))

    assert manifests == ()
    assert len(invalid) == 1
    assert "obsolete" in invalid[0].failure


def test_unreadable_historical_identity_is_informational_and_does_not_block_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = "2" * 64
    _write_manifest(tmp_path, current, _manifest_text(current))
    _point_current_at(tmp_path, current)
    obsolete_identity = "3" * 64
    _write_manifest(
        tmp_path,
        obsolete_identity,
        _manifest_text(obsolete_identity).replace(
            ARTIFACT_SCHEMA_VERSION,
            "fedsira|artifact_manifest|2",
        ),
    )
    logger = Mock(spec=logging.Logger)
    monkeypatch.setattr(store, "ARTIFACT_LOGGER", logger)
    manifests, invalid = load_published_manifests((tmp_path,))
    assert tuple(manifest.identity for manifest in manifests) == (current,)
    assert invalid == ()
    logger.info.assert_called_once()
    assert logger.info.call_args.args[0] == "artifact.manifest.superseded_history %s: %s"
    logger.warning.assert_not_called()


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
