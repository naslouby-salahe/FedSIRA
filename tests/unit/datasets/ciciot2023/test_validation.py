import pytest

from fedsira.datasets.ciciot2023.schema import TARGET_LABEL
from fedsira.datasets.ciciot2023.validation import (
    validate_label_collisions,
    validate_target_label_present,
)


def test_validate_label_collisions_accepts_case_and_whitespace_variants() -> None:
    validate_label_collisions(frozenset({"DDoS-SYN Flood", "ddos_syn_flood"}))


def test_validate_label_collisions_rejects_unrelated_collisions() -> None:
    with pytest.raises(ValueError, match="differ by more than"):
        validate_label_collisions(frozenset({"DDoS SYN Flood", "DDOS.SYN.FLOOD!!!"}))


def test_validate_target_label_present_accepts_when_observed() -> None:
    validate_target_label_present(frozenset({"BENIGN", TARGET_LABEL, "DDOS_SYN_FLOOD"}))


def test_validate_target_label_present_rejects_when_missing() -> None:
    with pytest.raises(ValueError, match="was not observed"):
        validate_target_label_present(frozenset({"BENIGN", "DDOS_SYN_FLOOD"}))
