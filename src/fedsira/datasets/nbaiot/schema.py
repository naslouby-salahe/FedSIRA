import re
from enum import StrEnum

from fedsira.domain.records import CanonicalToken


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


NBAIOT_DOMAIN_ORDER: tuple[NBaiotDomain, ...] = (
    NBaiotDomain.DANMINI_DOORBELL,
    NBaiotDomain.ENNIO_DOORBELL,
    NBaiotDomain.ECOBEE_THERMOSTAT,
    NBaiotDomain.PHILIPS_BABY_MONITOR,
    NBaiotDomain.PROVISION_PT737E_CAMERA,
    NBaiotDomain.PROVISION_PT838_CAMERA,
    NBaiotDomain.SIMPLEHOME_1002_CAMERA,
    NBaiotDomain.SIMPLEHOME_1003_CAMERA,
    NBaiotDomain.SAMSUNG_WEBCAM,
)

NBAIOT_DOMAIN_HASH_TOKEN: dict[NBaiotDomain, CanonicalToken] = {
    NBaiotDomain.DANMINI_DOORBELL: "DANMINI_DOORBELL",
    NBaiotDomain.ENNIO_DOORBELL: "ENNIO_DOORBELL",
    NBaiotDomain.ECOBEE_THERMOSTAT: "ECOBEE_THERMOSTAT",
    NBaiotDomain.PHILIPS_BABY_MONITOR: "PHILIPS_BABY_MONITOR",
    NBaiotDomain.PROVISION_PT737E_CAMERA: "PROVISION_PT737E_CAMERA",
    NBaiotDomain.PROVISION_PT838_CAMERA: "PROVISION_PT838_CAMERA",
    NBaiotDomain.SIMPLEHOME_1002_CAMERA: "SIMPLEHOME_1002_CAMERA",
    NBaiotDomain.SIMPLEHOME_1003_CAMERA: "SIMPLEHOME_1003_CAMERA",
    NBaiotDomain.SAMSUNG_WEBCAM: "SAMSUNG_WEBCAM",
}

NBAIOT_DIRECTORY_TO_DOMAIN: dict[CanonicalToken, NBaiotDomain] = {
    "Danmini_Doorbell": NBaiotDomain.DANMINI_DOORBELL,
    "Ennio_Doorbell": NBaiotDomain.ENNIO_DOORBELL,
    "Ecobee_Thermostat": NBaiotDomain.ECOBEE_THERMOSTAT,
    "Philips_B120N10_Baby_Monitor": NBaiotDomain.PHILIPS_BABY_MONITOR,
    "Provision_PT_737E_Security_Camera": NBaiotDomain.PROVISION_PT737E_CAMERA,
    "Provision_PT_838_Security_Camera": NBaiotDomain.PROVISION_PT838_CAMERA,
    "SimpleHome_XCS7_1002_WHT_Security_Camera": NBaiotDomain.SIMPLEHOME_1002_CAMERA,
    "SimpleHome_XCS7_1003_WHT_Security_Camera": NBaiotDomain.SIMPLEHOME_1003_CAMERA,
    "Samsung_SNH_1011_N_Webcam": NBaiotDomain.SAMSUNG_WEBCAM,
}


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


NBAIOT_CLASS_ORDER: tuple[NBaiotClass, ...] = (
    NBaiotClass.BENIGN,
    NBaiotClass.GAFGYT_COMBO,
    NBaiotClass.GAFGYT_JUNK,
    NBaiotClass.GAFGYT_SCAN,
    NBaiotClass.GAFGYT_TCP,
    NBaiotClass.GAFGYT_UDP,
    NBaiotClass.MIRAI_ACK,
    NBaiotClass.MIRAI_SCAN,
    NBaiotClass.MIRAI_SYN,
    NBaiotClass.MIRAI_UDP,
    NBaiotClass.MIRAI_UDPPLAIN,
)

NBAIOT_TARGET_CLASS = NBaiotClass.GAFGYT_COMBO

NBAIOT_GAFGYT_BASENAME_CLASS: dict[CanonicalToken, NBaiotClass] = {
    "combo": NBaiotClass.GAFGYT_COMBO,
    "junk": NBaiotClass.GAFGYT_JUNK,
    "scan": NBaiotClass.GAFGYT_SCAN,
    "tcp": NBaiotClass.GAFGYT_TCP,
    "udp": NBaiotClass.GAFGYT_UDP,
}

NBAIOT_MIRAI_BASENAME_CLASS: dict[CanonicalToken, NBaiotClass] = {
    "ack": NBaiotClass.MIRAI_ACK,
    "scan": NBaiotClass.MIRAI_SCAN,
    "syn": NBaiotClass.MIRAI_SYN,
    "udp": NBaiotClass.MIRAI_UDP,
    "udpplain": NBaiotClass.MIRAI_UDPPLAIN,
}

_NON_ALPHANUMERIC = re.compile(r"[^0-9a-zA-Z]+")


def normalize_path_token(raw_token: CanonicalToken) -> CanonicalToken:
    return _NON_ALPHANUMERIC.sub("_", raw_token).strip("_").upper()


def resolve_domain(directory_name: CanonicalToken) -> NBaiotDomain | None:
    return NBAIOT_DIRECTORY_TO_DOMAIN.get(directory_name)


def resolve_attack_class(
    attack_family_token: CanonicalToken, basename_token: CanonicalToken
) -> NBaiotClass | None:
    family = attack_family_token.strip().lower()
    basename = basename_token.strip().lower()
    if family == "gafgyt":
        return NBAIOT_GAFGYT_BASENAME_CLASS.get(basename)
    if family == "mirai":
        return NBAIOT_MIRAI_BASENAME_CLASS.get(basename)
    return None
