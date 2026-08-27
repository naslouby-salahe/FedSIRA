from __future__ import annotations

import csv
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from fedsira.datasets.ciciot2023.schema import canonicalize_token
from fedsira.domain.records import ArtifactDigest, CanonicalToken
from fedsira.runtime.determinism import canonical_bytes

_ASCII_HEADER_WHITESPACE = " \t\r\n\f\v"


@dataclass(frozen=True)
class SecondaryCsvFile:
    absolute_path: Path
    relative_path: CanonicalToken
    file_sha256: ArtifactDigest


def compute_file_checksum(path: Path) -> ArtifactDigest:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def discover_secondary_csv_files(csv_root: Path) -> tuple[SecondaryCsvFile, ...]:
    paths = sorted(csv_root.rglob("*.csv"), key=lambda path: path.relative_to(csv_root).as_posix())
    if not paths:
        raise ValueError(f"no CICIoT2023 CSV shards found beneath {csv_root}")
    return tuple(
        SecondaryCsvFile(
            absolute_path=path,
            relative_path=path.relative_to(csv_root).as_posix(),
            file_sha256=compute_file_checksum(path),
        )
        for path in paths
    )


def compute_dataset_manifest_hash(discovered: Sequence[SecondaryCsvFile]) -> ArtifactDigest:
    if not discovered:
        raise ValueError("secondary dataset manifest requires at least one CSV shard")
    canonical_manifest = tuple(
        (item.relative_path, item.file_sha256)
        for item in sorted(discovered, key=lambda item: item.relative_path)
    )
    return hashlib.sha256(
        canonical_bytes("CICIOT2023_DATASET_MANIFEST_V1", canonical_manifest)
    ).hexdigest()


def read_csv_header(path: Path) -> tuple[CanonicalToken, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            raw_header = next(reader)
        except StopIteration as error:
            raise ValueError(f"CICIoT2023 CSV shard is empty: {path}") from error
    return tuple(name.strip(_ASCII_HEADER_WHITESPACE) for name in raw_header)


def resolve_label_column(header: tuple[CanonicalToken, ...]) -> CanonicalToken:
    label_columns = [column for column in header if canonicalize_token(column) == "LABEL"]
    if len(label_columns) != 1:
        raise ValueError(
            "expected exactly one column named 'label' (case-insensitive), "
            f"found {len(label_columns)}: {label_columns}"
        )
    return label_columns[0]


def validate_consistent_header(
    reference_header: tuple[CanonicalToken, ...], observed_header: tuple[CanonicalToken, ...]
) -> None:
    if observed_header != reference_header:
        raise ValueError("secondary CSV header does not match the canonical reference schema")
