import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fedsira.datasets.nbaiot.schema import (
    NBAIOT_DOMAIN_HASH_TOKEN,
    NBaiotClass,
    NBaiotDomain,
    normalize_path_token,
    resolve_attack_class,
    resolve_domain,
)
from fedsira.domain.records import ArtifactDigest, CanonicalToken
from fedsira.runtime.determinism import canonical_bytes

GAFGYT_DIRECTORY_TOKEN = "GAFGYT_ATTACKS"
MIRAI_DIRECTORY_TOKEN = "MIRAI_ATTACKS"
BENIGN_FILENAME = "benign_traffic.csv"

_ATTACK_FAMILY_BY_DIRECTORY_TOKEN: dict[CanonicalToken, CanonicalToken] = {
    GAFGYT_DIRECTORY_TOKEN: "gafgyt",
    MIRAI_DIRECTORY_TOKEN: "mirai",
}


@dataclass(frozen=True)
class DiscoveredCsvFile:
    domain: NBaiotDomain
    class_id: NBaiotClass
    relative_path: CanonicalToken
    file_sha256: ArtifactDigest
    absolute_path: Path


def compute_file_checksum(path: Path) -> ArtifactDigest:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_rar_archive(archive_path: Path, destination_directory: Path) -> None:
    destination_directory.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["unrar", "x", "-o-", str(archive_path), f"{destination_directory}/"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            f"unrar failed to extract {archive_path} (exit {result.returncode}): {result.stderr}"
        )


def _discover_attack_csv_files(
    device_directory: Path,
    domain: NBaiotDomain,
    directory_token: CanonicalToken,
    extraction_cache_root: Path,
) -> tuple[DiscoveredCsvFile, ...]:
    family = _ATTACK_FAMILY_BY_DIRECTORY_TOKEN[directory_token]
    extracted_directory = device_directory / f"{family}_attacks"
    if not extracted_directory.is_dir():
        archive_path = device_directory / f"{family}_attacks.rar"
        if not archive_path.exists():
            return ()
        extracted_directory = extraction_cache_root / domain.value / f"{family}_attacks"
        extract_rar_archive(archive_path, extracted_directory)

    discovered: list[DiscoveredCsvFile] = []
    for csv_path in extracted_directory.glob("*.csv"):
        class_id = resolve_attack_class(family, csv_path.stem)
        if class_id is None:
            raise ValueError(
                f"unrecognized {family} attack basename {csv_path.stem!r} in {csv_path}"
            )
        discovered.append(
            DiscoveredCsvFile(
                domain=domain,
                class_id=class_id,
                relative_path=csv_path.relative_to(device_directory).as_posix(),
                file_sha256=compute_file_checksum(csv_path),
                absolute_path=csv_path,
            )
        )
    return tuple(discovered)


def discover_primary_csv_files(
    raw_root: Path, extraction_cache_root: Path
) -> tuple[DiscoveredCsvFile, ...]:
    discovered: list[DiscoveredCsvFile] = []
    for device_directory in sorted(raw_root.iterdir(), key=lambda entry: entry.name):
        if not device_directory.is_dir():
            continue
        domain = resolve_domain(device_directory.name)
        if domain is None:
            raise ValueError(f"unrecognized N-BaIoT device directory: {device_directory.name}")

        benign_csv = device_directory / BENIGN_FILENAME
        if benign_csv.exists():
            discovered.append(
                DiscoveredCsvFile(
                    domain=domain,
                    class_id=NBaiotClass.BENIGN,
                    relative_path=benign_csv.relative_to(device_directory).as_posix(),
                    file_sha256=compute_file_checksum(benign_csv),
                    absolute_path=benign_csv,
                )
            )

        for directory_token in (GAFGYT_DIRECTORY_TOKEN, MIRAI_DIRECTORY_TOKEN):
            discovered.extend(
                _discover_attack_csv_files(
                    device_directory, domain, directory_token, extraction_cache_root
                )
            )

    return tuple(
        sorted(
            discovered,
            key=lambda item: (item.domain.value, normalize_path_token(item.relative_path)),
        )
    )


def compute_dataset_manifest_hash(discovered: tuple[DiscoveredCsvFile, ...]) -> ArtifactDigest:
    ordered = sorted(discovered, key=lambda item: (item.domain.value, item.relative_path))
    hasher = hashlib.sha256()
    for item in ordered:
        hasher.update(
            canonical_bytes(
                NBAIOT_DOMAIN_HASH_TOKEN[item.domain], item.relative_path, item.file_sha256
            )
        )
    return hasher.hexdigest()
