from fedsira.datasets.ciciot2023.schema import (
    BENIGN_LABEL,
    TARGET_LABEL,
    build_class_registry,
    normalize_label,
    normalize_label_token,
)


def test_normalize_label_token_normalizes_case_and_punctuation() -> None:
    assert normalize_label_token("ddos-syn_flood") == "DDOS_SYN_FLOOD"
    assert normalize_label_token("  DDoS SYN Flood  ") == "DDOS_SYN_FLOOD"
    assert normalize_label_token("Backdoor_Malware") == "BACKDOOR_MALWARE"


def test_normalize_label_token_collapses_repeated_separators() -> None:
    assert normalize_label_token("a--b__c") == "A_B_C"


def test_normalize_label_token_uses_unicode_nfc_and_alphanumeric_rules() -> None:
    assert normalize_label_token("  Cafe\u0301—DDoS  ") == "CAFÉ_DDOS"


def test_normalize_label_maps_benign_aliases() -> None:
    assert normalize_label("BenignTraffic") == BENIGN_LABEL
    assert normalize_label("Benign_Traffic") == BENIGN_LABEL
    assert normalize_label("benign-traffic") == BENIGN_LABEL
    assert normalize_label("Suspicious_Traffic") != BENIGN_LABEL


def test_normalize_label_preserves_target_label() -> None:
    assert normalize_label("Backdoor_Malware") == TARGET_LABEL


def test_build_class_registry_orders_benign_then_target_then_lexicographic() -> None:
    registry = build_class_registry(frozenset({"ZEBRA", "APPLE", TARGET_LABEL, BENIGN_LABEL}))
    assert registry == (BENIGN_LABEL, TARGET_LABEL, "APPLE", "ZEBRA")
