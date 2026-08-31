from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from fedsira.datasets.ciciot2023.schema import normalize_label_token
from fedsira.domain.types import (
    DatasetColumnName,
    DatasetFileDigest,
    DatasetManifestDigest,
    FramingField,
    FrozenDomainModel,
    RelativePathText,
    SeedDerivationLabel,
)
from fedsira.runtime.determinism import framed_bytes

_ASCII_HEADER_WHITESPACE = " \t\r\n\f\v"
DATASET_MANIFEST_SEPARATOR: SeedDerivationLabel = "CICIOT2023_DATASET_MANIFEST_V1"


class SecondaryCsvFile(FrozenDomainModel):
    absolute_path: Path
    relative_path: RelativePathText
    file_sha256: DatasetFileDigest


def compute_file_checksum(path: Path) -> DatasetFileDigest:
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


def compute_dataset_manifest_hash(
    discovered: tuple[SecondaryCsvFile, ...],
) -> DatasetManifestDigest:
    if not discovered:
        raise ValueError("secondary dataset manifest requires at least one CSV shard")
    fields: list[FramingField] = []
    for item in sorted(discovered, key=lambda discovered_file: discovered_file.relative_path):
        fields.extend((item.relative_path, item.file_sha256))
    return hashlib.sha256(framed_bytes(DATASET_MANIFEST_SEPARATOR, *fields)).hexdigest()


def read_csv_header(path: Path) -> tuple[DatasetColumnName, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            raw_header = next(reader)
        except StopIteration as error:
            raise ValueError(f"CICIoT2023 CSV shard is empty: {path}") from error
    return tuple(name.strip(_ASCII_HEADER_WHITESPACE) for name in raw_header)


def resolve_label_column(header: tuple[DatasetColumnName, ...]) -> DatasetColumnName:
    label_columns = tuple(column for column in header if normalize_label_token(column) == "LABEL")
    if len(label_columns) != 1:
        raise ValueError(
            "expected exactly one column named 'label' (case-insensitive), "
            f"found {len(label_columns)}: {label_columns}"
        )
    return label_columns[0]


def validate_consistent_header(
    reference_header: tuple[DatasetColumnName, ...],
    observed_header: tuple[DatasetColumnName, ...],
) -> None:
    if observed_header != reference_header:
        raise ValueError("secondary CSV header does not match the fixed reference schema")
