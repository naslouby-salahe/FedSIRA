import hashlib
from collections import OrderedDict
from pathlib import Path

from fedsira.artifacts.paths import artifact_slot_directory
from fedsira.artifacts.store import ArtifactSlot, read_current_artifact
from fedsira.datasets.common import (
    PreparedRoleViewManifest,
    PreparedViewSidecar,
    view_parquet_path,
)
from fedsira.domain.enums import ArtifactFamily
from fedsira.domain.types import (
    ArtifactDigest,
    ByteCount,
    FailureMessage,
    ModificationTimestamp,
    PreparedViewKey,
    RowCount,
    ValidatedPreparedViewsLimit,
)
from fedsira.runtime import REPOSITORY_ROOT

VALIDATED_PREPARED_VIEWS_LIMIT: ValidatedPreparedViewsLimit = 512

_VALIDATED_PREPARED_VIEWS: OrderedDict[
    Path, tuple[ArtifactDigest, ByteCount, ModificationTimestamp]
] = OrderedDict()


def prepared_view_publication_failures(prepared_root: Path) -> tuple[FailureMessage, ...]:
    if not prepared_root.exists():
        return ()
    failures: list[FailureMessage] = []
    for metadata_path in sorted(prepared_root.glob("*.json")):
        try:
            sidecar = PreparedViewSidecar.model_validate_json(metadata_path.read_text())
        except ValueError:
            failures.append(f"prepared role view sidecar is unreadable: {metadata_path.name}")
            continue
        failures.extend(
            _view_failures(
                metadata_path.stem,
                view_parquet_path(prepared_root, metadata_path.stem),
                sidecar.row_count,
            )
        )
    return tuple(failures)


def _view_failures(
    view_key: PreparedViewKey,
    parquet_path: Path,
    sidecar_row_count: RowCount,
) -> tuple[FailureMessage, ...]:
    if not parquet_path.is_file():
        return (f"prepared role view {view_key} has no parquet payload",)
    slot = ArtifactSlot(family=ArtifactFamily.PREPARED_ROLE_VIEW, instance=view_key)
    current = read_current_artifact(REPOSITORY_ROOT / artifact_slot_directory(slot))
    if current is None:
        return (
            f"prepared role view {view_key} has no published Complete artifact; "
            "its provenance must be published before it can be consumed",
        )
    manifest, payload = current
    restored = PreparedRoleViewManifest.model_validate_json(payload)
    observed_bytes = parquet_path.stat().st_size
    failures: list[FailureMessage] = []
    if restored.parquet_bytes != observed_bytes:
        failures.append(
            f"prepared role view {view_key} payload is {observed_bytes} bytes but its "
            f"published artifact declares {restored.parquet_bytes}"
        )
    if restored.row_count != sidecar_row_count:
        failures.append(
            f"prepared role view {view_key} publishes {restored.row_count} rows but its "
            f"sidecar declares {sidecar_row_count}"
        )
    if failures:
        return tuple(failures)
    stat = parquet_path.stat()
    memo = _VALIDATED_PREPARED_VIEWS.get(parquet_path)
    if memo is not None and memo == (manifest.identity, stat.st_size, stat.st_mtime_ns):
        _VALIDATED_PREPARED_VIEWS.move_to_end(parquet_path)
        return ()
    observed_digest = _parquet_checksum(parquet_path)
    if observed_digest != restored.parquet_sha256:
        return (
            f"prepared role view {view_key} payload digest {observed_digest} does not match "
            f"its published artifact ({restored.parquet_sha256})",
        )
    _VALIDATED_PREPARED_VIEWS[parquet_path] = (
        manifest.identity,
        stat.st_size,
        stat.st_mtime_ns,
    )
    _VALIDATED_PREPARED_VIEWS.move_to_end(parquet_path)
    while len(_VALIDATED_PREPARED_VIEWS) > VALIDATED_PREPARED_VIEWS_LIMIT:
        _VALIDATED_PREPARED_VIEWS.popitem(last=False)
    return ()


def _parquet_checksum(path: Path) -> ArtifactDigest:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
