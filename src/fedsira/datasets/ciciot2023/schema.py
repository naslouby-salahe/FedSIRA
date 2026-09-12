import hashlib
import re
import unicodedata
from enum import IntEnum, StrEnum

from fedsira.datasets.common import DatasetSpecification
from fedsira.domain.enums import DatasetId
from fedsira.domain.types import (
    BooleanValue,
    ClassLabel,
    DatasetClassToken,
    DatasetManifestDigest,
    DomainCount,
    DomainId,
    FileCount,
    FrozenDomainModel,
    PartitionSalt,
    PredictorCount,
    PredictorCountMatchesOfficial,
    RowCount,
    SampleId,
    SeedDerivationLabel,
)
from fedsira.runtime import framed_bytes


class CICIoTSpecialLabel(StrEnum):
    BENIGN = "BENIGN"  # TODO: should be enum
    BACKDOOR_MALWARE = "BACKDOOR_MALWARE"  # TODO: should be enum


class _CICIoTBenignAlias(StrEnum):
    BENIGNTRAFFIC = "BENIGNTRAFFIC"  # TODO: should be enum
    BENIGN_TRAFFIC = "BENIGN_TRAFFIC"  # TODO: should be enum
    BENIGN_FINAL = "BENIGN_FINAL"  # TODO: should be enum


class CICIoT2023TargetFamilyMember(StrEnum):
    BACKDOOR_MALWARE = "BACKDOOR_MALWARE"  # TODO: should be enum
    MIRAI_GREETH_FLOOD = "MIRAI_GREETH_FLOOD"  # TODO: should be enum
    MIRAI_GREIP_FLOOD = "MIRAI_GREIP_FLOOD"  # TODO: should be enum
    MIRAI_UDPPLAIN = "MIRAI_UDPPLAIN"  # TODO: should be enum

    @property
    def raw_token(self) -> ClassLabel:
        return self.value


class CICIoTRowIdentifierToken(StrEnum):
    INDEX = "INDEX"  # TODO: should be enum
    ROW_ID = "ROW_ID"  # TODO: should be enum
    ROWID = "ROWID"  # TODO: should be enum
    UNNAMED_0 = "UNNAMED_0"  # TODO: should be enum


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
    target_family = tuple(member.value for member in CICIoT2023TargetFamilyMember)
    if normalized in target_family:
        return TARGET_LABEL
    try:
        _CICIoTBenignAlias[normalized]
    except KeyError:
        return normalized
    return BENIGN_LABEL


def target_family_collision_is_declared(first: ClassLabel, second: ClassLabel) -> BooleanValue:
    target_family = tuple(member.value for member in CICIoT2023TargetFamilyMember)
    return (
        normalize_label_token(first) in target_family
        and normalize_label_token(second) in target_family
    )


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


class CICIoT2023DatasetManifestPayload(FrozenDomainModel):
    dataset_file_manifest_hash: DatasetManifestDigest
    file_count: FileCount
    raw_row_count: RowCount
    retained_row_count: RowCount
    excluded_row_count: RowCount
    predictor_count: PredictorCount
    official_expected_predictor_count: PredictorCount
    predictor_count_matches_official: PredictorCountMatchesOfficial
    class_registry: tuple[DatasetClassToken, ...]
    target_family_members: tuple[ClassLabel, ...]
    pseudo_domain_count: DomainCount


def specification() -> DatasetSpecification:
    return DatasetSpecification(
        dataset=DatasetId.CICIOT2023,
        class_tokens=(),
        domain_ids=tuple(f"PSEUDO_DOMAIN_{index}" for index in range(1, PSEUDO_DOMAIN_COUNT + 1)),
        domain_hash_tokens=tuple(
            f"PSEUDO_DOMAIN_{index}" for index in range(1, PSEUDO_DOMAIN_COUNT + 1)
        ),
        attack_carrier_class=None,
        trigger_feature_names=(),
        target_class=TARGET_LABEL,
        benign_class=BENIGN_LABEL,
        supported_class_tokens=(),
        expected_predictor_count=OFFICIAL_EXPECTED_PREDICTOR_COUNT,
        domain_proxy_semantics="synthetic hash partition",
        raw_data_relative="CIC_IOT_Dataset2023/CSV",
    )
