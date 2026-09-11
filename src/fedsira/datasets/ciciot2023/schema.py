import hashlib
import re
import unicodedata
from enum import IntEnum, StrEnum

from fedsira.domain.types import (
    ClassLabel,
    DatasetManifestDigest,
    DomainCount,
    DomainId,
    PartitionSalt,
    PredictorCount,
    SampleId,
    SeedDerivationLabel,
)
from fedsira.runtime import framed_bytes


class CICIoTSpecialLabel(StrEnum):
    BENIGN = "BENIGN"
    BACKDOOR_MALWARE = "BACKDOOR_MALWARE"


class _CICIoTBenignAlias(StrEnum):
    BENIGNTRAFFIC = "BENIGNTRAFFIC"
    BENIGN_TRAFFIC = "BENIGN_TRAFFIC"


class CICIoTRowIdentifierToken(StrEnum):
    INDEX = "INDEX"
    ROW_ID = "ROW_ID"
    ROWID = "ROWID"
    UNNAMED_0 = "UNNAMED_0"


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


TARGET_LABEL = CICIoTSpecialLabel.BACKDOOR_MALWARE
BENIGN_LABEL = CICIoTSpecialLabel.BENIGN
OFFICIAL_EXPECTED_PREDICTOR_COUNT: PredictorCount = 46
PSEUDO_DOMAIN_COUNT: DomainCount = len(CICIoT2023PseudoDomain)
PSEUDO_DOMAIN_HASH_SEPARATOR: SeedDerivationLabel = "CIC_IOT_2023_PSEUDO_DOMAIN"
_NON_ALPHANUMERIC_RUN = re.compile(r"[^0-9A-Za-z]+")


def normalize_label_token(raw_label: ClassLabel) -> ClassLabel:
    normalized = unicodedata.normalize("NFC", raw_label).strip().upper()
    normalized = _NON_ALPHANUMERIC_RUN.sub("_", normalized)
    return normalized.strip("_")


def normalize_label(raw_label: ClassLabel) -> ClassLabel:
    normalized = normalize_label_token(raw_label)
    try:
        _CICIoTBenignAlias[normalized]
    except KeyError:
        return normalized
    return BENIGN_LABEL


def build_class_registry(observed_labels: frozenset[ClassLabel]) -> tuple[ClassLabel, ...]:
    remaining = sorted(observed_labels - frozenset((BENIGN_LABEL, TARGET_LABEL)))
    return (BENIGN_LABEL, TARGET_LABEL, *remaining)


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
