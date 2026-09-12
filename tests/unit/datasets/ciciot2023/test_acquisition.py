from pathlib import Path

import pytest

from _repo import REPO_ROOT
from fedsira.datasets.ciciot2023.prepare import (
    compute_dataset_manifest_hash,
    compute_file_checksum,
    discover_secondary_csv_files,
    read_csv_header,
    resolve_label_column,
    validate_consistent_header,
)
from fedsira.domain.enums import CICIoT2023Acquisition


def test_discover_secondary_csv_files_models_nested_shards(tmp_path: Path) -> None:
    (tmp_path / "DDoS-SYN_Flood").mkdir()
    (tmp_path / "DDoS-SYN_Flood" / "part1.csv").write_text("a,Label\n1,BENIGN\n")
    (tmp_path / "Backdoor_Malware").mkdir()
    (tmp_path / "Backdoor_Malware" / "part1.csv").write_text("a,Label\n1,Backdoor_Malware\n")

    discovered = discover_secondary_csv_files(tmp_path, CICIoT2023Acquisition.LABELED_SHARDS)

    assert [item.relative_path for item in discovered] == [
        "Backdoor_Malware/part1.csv",
        "DDoS-SYN_Flood/part1.csv",
    ]
    assert all(item.absolute_path.is_file() for item in discovered)
    assert all(len(item.file_sha256) == 64 for item in discovered)


def test_discover_secondary_csv_files_rejects_empty_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no CICIoT2023 CSV shards"):
        discover_secondary_csv_files(tmp_path, CICIoT2023Acquisition.LABELED_SHARDS)


def test_dataset_manifest_hash_depends_on_all_ordered_file_identities(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = tmp_path / "a" / "x.csv"
    second = tmp_path / "b" / "x.csv"
    first.write_text("a\n1\n")
    second.write_text("a\n2\n")
    before = compute_dataset_manifest_hash(
        discover_secondary_csv_files(tmp_path, CICIoT2023Acquisition.PER_ATTACK_SHARDS)
    )

    second.write_text("a\n3\n")
    after = compute_dataset_manifest_hash(
        discover_secondary_csv_files(tmp_path, CICIoT2023Acquisition.PER_ATTACK_SHARDS)
    )

    assert before != after


def test_compute_file_checksum_is_a_sha256_hex_digest(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    path.write_text("a,b\n1,2\n")
    digest = compute_file_checksum(path)
    assert len(digest) == 64
    bytes.fromhex(digest)


def test_resolve_label_column_finds_the_unique_case_insensitive_match() -> None:
    assert resolve_label_column(("a", "Label", "b")) == "Label"
    assert resolve_label_column(("a", "LABEL", "b")) == "LABEL"


def test_resolve_label_column_returns_none_without_a_label_column() -> None:
    assert resolve_label_column(("a", "b")) is None


def test_resolve_label_column_rejects_multiple_matches() -> None:
    with pytest.raises(ValueError, match="found 2"):
        resolve_label_column(("Label", "label"))


def test_labeled_acquisition_selects_only_shards_with_an_in_file_label(tmp_path: Path) -> None:
    (tmp_path / "labeled").mkdir()
    (tmp_path / "labeled" / "part1.csv").write_text("a,Label\n1,BENIGN\n")
    (tmp_path / "per_attack").mkdir()
    (tmp_path / "per_attack" / "part1.csv").write_text("a\n1\n")

    discovered = discover_secondary_csv_files(tmp_path, CICIoT2023Acquisition.LABELED_SHARDS)

    assert [item.relative_path for item in discovered] == ["labeled/part1.csv"]
    assert discovered[0].label_column == "Label"
    assert discovered[0].shard_class is None


def test_per_attack_acquisition_derives_the_class_from_the_shard_directory(tmp_path: Path) -> None:
    (tmp_path / "labeled").mkdir()
    (tmp_path / "labeled" / "part1.csv").write_text("a,Label\n1,BENIGN\n")
    (tmp_path / "DDoS-SYN_Flood").mkdir()
    (tmp_path / "DDoS-SYN_Flood" / "part1.csv").write_text("a\n1\n")
    (tmp_path / "Benign_Final").mkdir()
    (tmp_path / "Benign_Final" / "part1.csv").write_text("a\n1\n")

    discovered = discover_secondary_csv_files(tmp_path, CICIoT2023Acquisition.PER_ATTACK_SHARDS)

    assert [item.relative_path for item in discovered] == [
        "Benign_Final/part1.csv",
        "DDoS-SYN_Flood/part1.csv",
    ]
    assert [item.shard_class for item in discovered] == ["BENIGN", "DDOS_SYN_FLOOD"]
    assert all(item.label_column is None for item in discovered)


def test_discovery_rejects_a_shard_with_more_than_one_label_column(tmp_path: Path) -> None:
    (tmp_path / "attack").mkdir()
    (tmp_path / "attack" / "part1.csv").write_text("a,Label,label\n1,BENIGN,BENIGN\n")

    with pytest.raises(ValueError, match="at most one column named 'label'"):
        discover_secondary_csv_files(tmp_path, CICIoT2023Acquisition.LABELED_SHARDS)


def test_discovery_rejects_an_acquisition_with_no_matching_shards(tmp_path: Path) -> None:
    (tmp_path / "attack").mkdir()
    (tmp_path / "attack" / "part1.csv").write_text("a\n1\n")

    with pytest.raises(ValueError, match="no CICIoT2023 CSV shards match"):
        discover_secondary_csv_files(tmp_path, CICIoT2023Acquisition.LABELED_SHARDS)


def test_validate_consistent_header_accepts_identical_headers() -> None:
    validate_consistent_header(("a", "b"), ("a", "b"))


def test_validate_consistent_header_rejects_mismatched_headers() -> None:
    with pytest.raises(ValueError, match="does not match"):
        validate_consistent_header(("a", "b"), ("b", "a"))


REAL_CICIOT2023_ROOT = REPO_ROOT / "data" / "raw" / "CIC_IOT_Dataset2023" / "CSV"


@pytest.mark.skipif(
    not REAL_CICIOT2023_ROOT.is_dir(), reason="real CICIoT2023 raw data not available"
)
def test_labeled_acquisition_against_real_raw_data() -> None:
    discovered = discover_secondary_csv_files(
        REAL_CICIOT2023_ROOT, CICIoT2023Acquisition.LABELED_SHARDS
    )
    reference_header = read_csv_header(discovered[0].absolute_path)
    label_column = resolve_label_column(reference_header)
    assert label_column
    for item in discovered[:5]:
        header = read_csv_header(item.absolute_path)
        validate_consistent_header(reference_header, header)


@pytest.mark.skipif(
    not REAL_CICIOT2023_ROOT.is_dir(), reason="real CICIoT2023 raw data not available"
)
def test_per_attack_acquisition_against_real_raw_data() -> None:
    discovered = discover_secondary_csv_files(
        REAL_CICIOT2023_ROOT, CICIoT2023Acquisition.PER_ATTACK_SHARDS
    )
    assert discovered
    assert all(item.label_column is None for item in discovered)
    assert all(item.shard_class for item in discovered)
    assert "BACKDOOR_MALWARE" in {item.shard_class for item in discovered}
    assert "BENIGN" in {item.shard_class for item in discovered}
    reference_header = read_csv_header(discovered[0].absolute_path)
    for item in discovered[:5]:
        validate_consistent_header(reference_header, read_csv_header(item.absolute_path))
