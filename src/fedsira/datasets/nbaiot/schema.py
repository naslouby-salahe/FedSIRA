import re
from enum import StrEnum

from fedsira.domain.types import (
    AttackBasename,
    AttackFamilyName,
    DomainId,
    FeatureName,
    NamespaceSeed,
    PathToken,
    PredictorCount,
    RelativePathText,
    SeedDerivationLabel,
)
from fedsira.runtime import deterministic_order


class NBaiotDomain(StrEnum):
    DANMINI_DOORBELL = "Danmini Doorbell"
    ENNIO_DOORBELL = "Ennio Doorbell"
    ECOBEE_THERMOSTAT = "Ecobee Thermostat"
    PHILIPS_BABY_MONITOR = "Philips Baby Monitor"
    PROVISION_PT737E_CAMERA = "Provision PT-737E Camera"
    PROVISION_PT838_CAMERA = "Provision PT-838 Camera"
    SIMPLEHOME_1002_CAMERA = "SimpleHome 1002 Camera"
    SIMPLEHOME_1003_CAMERA = "SimpleHome 1003 Camera"
    SAMSUNG_WEBCAM = "Samsung Webcam"


class _NBaiotDirectory(StrEnum):
    DANMINI_DOORBELL = "Danmini_Doorbell"
    ENNIO_DOORBELL = "Ennio_Doorbell"
    ECOBEE_THERMOSTAT = "Ecobee_Thermostat"
    PHILIPS_BABY_MONITOR = "Philips_B120N10_Baby_Monitor"
    PROVISION_PT737E_CAMERA = "Provision_PT_737E_Security_Camera"
    PROVISION_PT838_CAMERA = "Provision_PT_838_Security_Camera"
    SIMPLEHOME_1002_CAMERA = "SimpleHome_XCS7_1002_WHT_Security_Camera"
    SIMPLEHOME_1003_CAMERA = "SimpleHome_XCS7_1003_WHT_Security_Camera"
    SAMSUNG_WEBCAM = "Samsung_SNH_1011_N_Webcam"


class NBaiotAttackFamily(StrEnum):
    GAFGYT = "gafgyt"
    MIRAI = "mirai"


class NBaiotClass(StrEnum):
    BENIGN = "BENIGN"
    GAFGYT_COMBO = "GAFGYT_COMBO"
    GAFGYT_JUNK = "GAFGYT_JUNK"
    GAFGYT_SCAN = "GAFGYT_SCAN"
    GAFGYT_TCP = "GAFGYT_TCP"
    GAFGYT_UDP = "GAFGYT_UDP"
    MIRAI_ACK = "MIRAI_ACK"
    MIRAI_SCAN = "MIRAI_SCAN"
    MIRAI_SYN = "MIRAI_SYN"
    MIRAI_UDP = "MIRAI_UDP"
    MIRAI_UDPPLAIN = "MIRAI_UDPPLAIN"


NBAIOT_DOMAIN_ORDER: tuple[NBaiotDomain, ...] = tuple(NBaiotDomain)
NBAIOT_CLASS_ORDER: tuple[NBaiotClass, ...] = tuple(NBaiotClass)
NBAIOT_TARGET_CLASS = NBaiotClass.GAFGYT_COMBO
NBAIOT_PRIMARY_PREDICTOR_COUNT: PredictorCount = 115
NBAIOT_TRIGGER_FEATURES: tuple[FeatureName, ...] = (
    "MI_dir_L0.1_weight",
    "H_L0.1_weight",
    "HH_L0.1_magnitude",
    "HpHp_L0.1_mean",
)
_NON_ALPHANUMERIC = re.compile(r"[^0-9a-zA-Z]+")


def nbaiot_domain_hash_token(domain: NBaiotDomain) -> DomainId:
    return domain.name


def nbaiot_domain_from_hash_token(token: DomainId) -> NBaiotDomain:
    try:
        return NBaiotDomain[token]
    except KeyError as error:
        raise ValueError(f"unknown N-BaIoT domain hash token: {token}") from error


def normalize_path_token(raw_token: RelativePathText) -> PathToken:
    return _NON_ALPHANUMERIC.sub("_", raw_token).strip("_").upper()


def resolve_domain(directory_name: RelativePathText) -> NBaiotDomain | None:
    try:
        directory = _NBaiotDirectory(directory_name)
    except ValueError:
        return None
    return NBaiotDomain[directory.name]


def resolve_attack_class(
    attack_family_token: AttackFamilyName,
    basename_token: AttackBasename,
) -> NBaiotClass | None:
    try:
        family = NBaiotAttackFamily(attack_family_token.strip().lower())
    except ValueError:
        return None
    try:
        return NBaiotClass[f"{family.name}_{basename_token.strip().upper()}"]
    except KeyError:
        return None


def deterministic_domain_order(
    domains: tuple[NBaiotDomain, ...],
    domain_separator: SeedDerivationLabel,
    order_namespace_seed: NamespaceSeed,
) -> tuple[NBaiotDomain, ...]:
    tokens = tuple(nbaiot_domain_hash_token(domain) for domain in domains)
    ordered_tokens = deterministic_order(tokens, domain_separator, order_namespace_seed)
    return tuple(nbaiot_domain_from_hash_token(token) for token in ordered_tokens)
