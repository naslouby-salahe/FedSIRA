import hashlib
import re
import unicodedata
from enum import IntEnum

from fedsira.datasets.nbaiot.schema import NBAIOT_DOMAIN_ORDER
from fedsira.domain.records import (
    BooleanValue,
    ClassLabel,
    DatasetManifestDigest,
    DomainCount,
    DomainId,
    NonNegativeInt,
    PartitionSalt,
    PredictorCount,
    SampleId,
    SeedDerivationLabel,
)
from fedsira.runtime.determinism import framed_bytes

TARGET_LABEL: ClassLabel = "BACKDOOR_MALWARE"
BENIGN_LABEL: ClassLabel = "BENIGN"
BENIGN_LABEL_ALIASES: frozenset[ClassLabel] = frozenset(("BENIGNTRAFFIC", "BENIGN_TRAFFIC"))
OFFICIAL_EXPECTED_PREDICTOR_COUNT: PredictorCount = 46
ROW_IDENTIFIER_TOKENS: frozenset[ClassLabel] = frozenset(
    ("INDEX", "ROW_ID", "ROWID", "UNNAMED_0")
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
    def display_token(self) -> DomainId:
        return f"PSEUDO_DOMAIN_{int(self) + 1}"


PSEUDO_DOMAIN_COUNT: DomainCount = len(CICIoT2023PseudoDomain)
PSEUDO_DOMAIN_HASH_SEPARATOR: SeedDerivationLabel = "CIC_IOT_2023_PSEUDO_DOMAIN"

if len(NBAIOT_DOMAIN_ORDER) != PSEUDO_DOMAIN_COUNT:
    raise RuntimeError("CICIoT2023 pseudo-domain count must equal the primary device-proxy count")

_NON_ALPHANUMERIC_RUN = re.compile(r"[^0-9A-Za-z]+")


def normalize_label_token(raw_label: ClassLabel) -> ClassLabel:
    normalized = unicodedata.normalize("NFC", raw_label).strip().upper()
    normalized = _NON_ALPHANUMERIC_RUN.sub("_", normalized)
    return normalized.strip("_")


def normalize_label(raw_label: ClassLabel) -> ClassLabel:
    normalized = normalize_label_token(raw_label)
    if normalized in BENIGN_LABEL_ALIASES:
        return BENIGN_LABEL
    return normalized


def build_class_registry(observed_labels: frozenset[ClassLabel]) -> tuple[ClassLabel, ...]:
    remaining = sorted(observed_labels - frozenset((BENIGN_LABEL, TARGET_LABEL)))
    return (BENIGN_LABEL, TARGET_LABEL, *remaining)


def is_row_identifier_column(
    column_token: ClassLabel,
    values: tuple[NonNegativeInt, ...],
) -> BooleanValue:
    if column_token not in ROW_IDENTIFIER_TOKENS:
        return False
    if len(set(values)) != len(values):
        return False
    zero_based = tuple(range(len(values)))
    one_based = tuple(range(1, len(values) + 1))
    return values in (zero_based, one_based)


def hash_to_pseudo_domain(
    dataset_manifest_hash: DatasetManifestDigest,
    label: ClassLabel,
    stable_row_id: SampleId,
    pseudo_domain_partition_salt: PartitionSalt,
) -> CICIoT2023PseudoDomain:
    digest = hashlib.sha256(
        framed_bytes(
            PSEUDO_DOMAIN_HASH_SEPARATOR,
            dataset_manifest_hash,
            label,
            stable_row_id,
            pseudo_domain_partition_salt,
        )
    ).digest()
    index = int.from_bytes(digest[0:8], byteorder="big") % PSEUDO_DOMAIN_COUNT
    return CICIoT2023PseudoDomain(index)
