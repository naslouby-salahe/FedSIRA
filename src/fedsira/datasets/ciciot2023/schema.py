import hashlib
import re
import unicodedata
from enum import IntEnum

from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.records import ArtifactDigest, CanonicalToken, PositiveInt
from fedsira.runtime.determinism import canonical_bytes

TARGET_LABEL = "BACKDOOR_MALWARE"
BENIGN_LABEL = "BENIGN"
BENIGN_CANONICAL_ALIASES: frozenset[CanonicalToken] = frozenset({"BENIGNTRAFFIC", "BENIGN_TRAFFIC"})
OFFICIAL_EXPECTED_PREDICTOR_COUNT = 46

ROW_IDENTIFIER_CANONICAL_TOKENS: frozenset[CanonicalToken] = frozenset(
    {"INDEX", "ROW_ID", "ROWID", "UNNAMED_0"}
)


class CICIoT2023PseudoDomain(IntEnum):
    PSEUDO_DOMAIN_1 = 0
    PSEUDO_DOMAIN_2 = 1
    PSEUDO_DOMAIN_3 = 2
    PSEUDO_DOMAIN_4 = 3
    PSEUDO_DOMAIN_5 = 4
    PSEUDO_DOMAIN_6 = 5
    PSEUDO_DOMAIN_7 = 6
    PSEUDO_DOMAIN_8 = 7
    PSEUDO_DOMAIN_9 = 8

    @property
    def display_token(self) -> CanonicalToken:
        return f"PSEUDO_DOMAIN_{int(self) + 1}"


PSEUDO_DOMAIN_COUNT = len(CICIoT2023PseudoDomain)
PSEUDO_DOMAIN_HASH_SEPARATOR = "CIC_IOT_2023_PSEUDO_DOMAIN"

if PSEUDO_DOMAIN_COUNT != len(NBAIOT_DOMAIN_ORDER):
    raise RuntimeError("CICIoT2023 pseudo-domain count must equal the primary device-proxy count")

_NON_ALPHANUMERIC_RUN = re.compile(r"[^0-9A-Za-z]+")


def canonicalize_token(raw: str) -> CanonicalToken:
    normalized = unicodedata.normalize("NFC", raw).strip().upper()
    normalized = _NON_ALPHANUMERIC_RUN.sub("_", normalized)
    return normalized.strip("_")


def canonicalize_label(raw: str) -> CanonicalToken:
    canonical = canonicalize_token(raw)
    if canonical in BENIGN_CANONICAL_ALIASES:
        return BENIGN_LABEL
    return canonical


def canonical_class_registry(
    observed_labels: frozenset[CanonicalToken],
) -> tuple[CanonicalToken, ...]:
    remaining = sorted(observed_labels - {BENIGN_LABEL, TARGET_LABEL})
    return (BENIGN_LABEL, TARGET_LABEL, *remaining)


def is_row_identifier_column(
    canonical_column_token: CanonicalToken, values: tuple[int, ...]
) -> bool:
    if canonical_column_token not in ROW_IDENTIFIER_CANONICAL_TOKENS:
        return False
    if len(set(values)) != len(values):
        return False
    zero_based = tuple(range(len(values)))
    one_based = tuple(range(1, len(values) + 1))
    return tuple(values) in (zero_based, one_based)


def hash_to_pseudo_domain(
    dataset_manifest_hash: ArtifactDigest,
    canonical_label: CanonicalToken,
    stable_row_id: ArtifactDigest,
    pseudo_domain_partition_salt: PositiveInt,
) -> CICIoT2023PseudoDomain:
    digest = hashlib.sha256(
        canonical_bytes(
            PSEUDO_DOMAIN_HASH_SEPARATOR,
            dataset_manifest_hash,
            canonical_label,
            stable_row_id,
            pseudo_domain_partition_salt,
        )
    ).digest()
    index = int.from_bytes(digest[0:8], byteorder="big") % PSEUDO_DOMAIN_COUNT
    return CICIoT2023PseudoDomain(index)
