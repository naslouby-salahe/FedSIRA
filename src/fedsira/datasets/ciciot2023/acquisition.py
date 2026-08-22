import hashlib
from pathlib import Path

import pandas

from fedsira.datasets.ciciot2023.schema import canonicalize_token
from fedsira.domain.records import ArtifactDigest, CanonicalToken


def compute_file_checksum(path: Path) -> ArtifactDigest:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def discover_secondary_csv_files(csv_root: Path) -> tuple[Path, ...]:
    discovered = sorted(
        csv_root.rglob("*.csv"), key=lambda path: path.relative_to(csv_root).as_posix()
    )
    return tuple(discovered)


def read_csv_header(path: Path) -> tuple[CanonicalToken, ...]:
    header_frame: pandas.DataFrame = pandas.read_csv(path, nrows=0)
    return tuple(str(name).strip() for name in header_frame.columns)


def resolve_label_column(header: tuple[CanonicalToken, ...]) -> CanonicalToken:
    label_columns = [column for column in header if canonicalize_token(column) == "LABEL"]
    if len(label_columns) != 1:
        raise ValueError(
            f"expected exactly one column named 'label' (case-insensitive), found "
            f"{len(label_columns)}: {label_columns}"
        )
    return label_columns[0]


def validate_consistent_header(
    reference_header: tuple[CanonicalToken, ...], observed_header: tuple[CanonicalToken, ...]
) -> None:
    if observed_header != reference_header:
        raise ValueError("secondary CSV header does not match the canonical reference schema")
