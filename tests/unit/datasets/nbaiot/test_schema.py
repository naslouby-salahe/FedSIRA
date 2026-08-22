from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_HASH_TOKEN,
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_TARGET_CLASS,
    NBaiotClass,
    NBaiotDomain,
    normalize_path_token,
    resolve_attack_class,
    resolve_domain,
)


def test_nine_domain_proxies_in_fixed_order() -> None:
    assert len(NBAIOT_DOMAIN_ORDER) == 9
    assert NBAIOT_DOMAIN_ORDER[0] is NBaiotDomain.DANMINI_DOORBELL
    assert NBAIOT_DOMAIN_ORDER[-1] is NBaiotDomain.SAMSUNG_WEBCAM
    assert len(set(NBAIOT_DOMAIN_ORDER)) == 9


def test_every_domain_has_a_fixed_hash_token() -> None:
    assert set(NBAIOT_DOMAIN_HASH_TOKEN.keys()) == set(NBaiotDomain)
    assert NBAIOT_DOMAIN_HASH_TOKEN[NBaiotDomain.PROVISION_PT737E_CAMERA] == (
        "PROVISION_PT737E_CAMERA"
    )


def test_resolve_domain_maps_official_directory_names() -> None:
    assert resolve_domain("Danmini_Doorbell") is NBaiotDomain.DANMINI_DOORBELL
    assert resolve_domain("Samsung_SNH_1011_N_Webcam") is NBaiotDomain.SAMSUNG_WEBCAM
    assert resolve_domain("Unknown_Device") is None


def test_eleven_classes_in_exact_roadmap_order() -> None:
    assert len(NBAIOT_CLASS_ORDER) == 11
    assert NBAIOT_CLASS_ORDER[0] is NBaiotClass.BENIGN
    assert NBAIOT_CLASS_ORDER[1] is NBaiotClass.GAFGYT_COMBO
    assert NBAIOT_CLASS_ORDER[-1] is NBaiotClass.MIRAI_UDPPLAIN
    assert set(NBAIOT_CLASS_ORDER) == set(NBaiotClass)


def test_target_class_is_gafgyt_combo() -> None:
    assert NBAIOT_TARGET_CLASS is NBaiotClass.GAFGYT_COMBO
    assert NBAIOT_TARGET_CLASS.value == "GAFGYT_COMBO"


def test_resolve_attack_class_maps_gafgyt_basenames() -> None:
    assert resolve_attack_class("gafgyt", "combo") is NBaiotClass.GAFGYT_COMBO
    assert resolve_attack_class("gafgyt", "junk") is NBaiotClass.GAFGYT_JUNK
    assert resolve_attack_class("GAFGYT", "COMBO") is NBaiotClass.GAFGYT_COMBO


def test_resolve_attack_class_maps_mirai_basenames() -> None:
    assert resolve_attack_class("mirai", "ack") is NBaiotClass.MIRAI_ACK
    assert resolve_attack_class("mirai", "udpplain") is NBaiotClass.MIRAI_UDPPLAIN


def test_resolve_attack_class_returns_none_for_unknown_family_or_basename() -> None:
    assert resolve_attack_class("unknown", "combo") is None
    assert resolve_attack_class("gafgyt", "nonexistent") is None


def test_normalize_path_token_ignores_case_and_normalizes_punctuation() -> None:
    assert normalize_path_token("gafgyt_attacks") == "GAFGYT_ATTACKS"
    assert normalize_path_token("Gafgyt-Attacks") == "GAFGYT_ATTACKS"
    assert normalize_path_token(" mirai attacks ") == "MIRAI_ATTACKS"
