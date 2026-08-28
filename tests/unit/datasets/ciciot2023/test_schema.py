from fedsira.datasets.ciciot2023.schema import (
    BENIGN_LABEL,
    PSEUDO_DOMAIN_COUNT,
    TARGET_LABEL,
    build_class_registry,
    normalize_label,
    normalize_label_token,
    hash_to_pseudo_domain,
    is_row_identifier_column,
)


def test_normalize_label_token_normalizes_case_and_punctuation() -> None:
    assert normalize_label_token("ddos-syn_flood") == "DDOS_SYN_FLOOD"
    assert normalize_label_token("  DDoS SYN Flood  ") == "DDOS_SYN_FLOOD"
    assert normalize_label_token("Backdoor_Malware") == "BACKDOOR_MALWARE"


def test_normalize_label_token_collapses_repeated_separators() -> None:
    assert normalize_label_token("a--b__c") == "A_B_C"


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


def test_is_row_identifier_column_accepts_zero_based_sequence() -> None:
    assert is_row_identifier_column("INDEX", (0, 1, 2, 3))


def test_is_row_identifier_column_accepts_one_based_sequence() -> None:
    assert is_row_identifier_column("ROW_ID", (1, 2, 3, 4))


def test_is_row_identifier_column_rejects_non_identifier_names() -> None:
    assert not is_row_identifier_column("PROTOCOL", (0, 1, 2, 3))


def test_is_row_identifier_column_rejects_non_sequential_values() -> None:
    assert not is_row_identifier_column("INDEX", (0, 2, 1, 3))


def test_is_row_identifier_column_rejects_duplicate_values() -> None:
    assert not is_row_identifier_column("INDEX", (0, 1, 1, 2))


def test_hash_to_pseudo_domain_is_within_the_pseudo_domain_count() -> None:
    domain = hash_to_pseudo_domain("a" * 64, "BACKDOOR_MALWARE", "b" * 64, 730201)
    assert 0 <= domain < PSEUDO_DOMAIN_COUNT


def test_hash_to_pseudo_domain_is_deterministic() -> None:
    args = ("a" * 64, "BACKDOOR_MALWARE", "b" * 64, 730201)
    assert hash_to_pseudo_domain(*args) == hash_to_pseudo_domain(*args)


def test_hash_to_pseudo_domain_changes_with_stable_row_id() -> None:
    first = hash_to_pseudo_domain("a" * 64, "BACKDOOR_MALWARE", "b" * 64, 730201)
    second = hash_to_pseudo_domain("a" * 64, "BACKDOOR_MALWARE", "c" * 64, 730201)
    assert first != second
