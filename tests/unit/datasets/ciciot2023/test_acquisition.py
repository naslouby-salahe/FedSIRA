from pathlib import Path

import pytest

from fedsira.datasets.ciciot2023.loading import (
    compute_dataset_manifest_hash,
    compute_file_checksum,
    discover_secondary_csv_files,
    read_csv_header,
    resolve_label_column,
    validate_consistent_header,
)


def test_discover_secondary_csv_files_models_nested_shards(tmp_path: Path) -> None:
    (tmp_path / "DDoS-SYN_Flood").mkdir()
    (tmp_path / "DDoS-SYN_Flood" / "part1.csv").write_text("a,Label\n1,BENIGN\n")
    (tmp_path / "Backdoor_Malware").mkdir()
    (tmp_path / "Backdoor_Malware" / "part1.csv").write_text("a,Label\n1,Backdoor_Malware\n")

    discovered = discover_secondary_csv_files(tmp_path)

    assert [item.relative_path for item in discovered] == [
        "Backdoor_Malware/part1.csv",
        "DDoS-SYN_Flood/part1.csv",
    ]
    assert all(item.absolute_path.is_file() for item in discovered)
    assert all(len(item.file_sha256) == 64 for item in discovered)


def test_discover_secondary_csv_files_rejects_empty_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no CICIoT2023 CSV shards"):
        discover_secondary_csv_files(tmp_path)


def test_dataset_manifest_hash_depends_on_all_ordered_file_identities(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = tmp_path / "a" / "x.csv"
    second = tmp_path / "b" / "x.csv"
    first.write_text("a\n1\n")
    second.write_text("a\n2\n")
    before = compute_dataset_manifest_hash(discover_secondary_csv_files(tmp_path))

    second.write_text("a\n3\n")
    after = compute_dataset_manifest_hash(discover_secondary_csv_files(tmp_path))

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


def test_resolve_label_column_rejects_zero_matches() -> None:
    with pytest.raises(ValueError, match="found 0"):
        resolve_label_column(("a", "b"))


def test_resolve_label_column_rejects_multiple_matches() -> None:
    with pytest.raises(ValueError, match="found 2"):
        resolve_label_column(("Label", "label"))


def test_validate_consistent_header_accepts_identical_headers() -> None:
    validate_consistent_header(("a", "b"), ("a", "b"))


def test_validate_consistent_header_rejects_mismatched_headers() -> None:
    with pytest.raises(ValueError, match="does not match"):
        validate_consistent_header(("a", "b"), ("b", "a"))


REAL_CICIOT2023_ROOT = Path(
    "/home/naslouby/Projects/datp-shared-data/raw/CIC_IOT_Dataset2023/CSV/MERGED_CSV"
)


@pytest.mark.skipif(
    not REAL_CICIOT2023_ROOT.is_dir(), reason="real CICIoT2023 raw data not available"
)
def test_discover_and_read_headers_against_real_raw_data() -> None:
    discovered = discover_secondary_csv_files(REAL_CICIOT2023_ROOT)
    reference_header = read_csv_header(discovered[0].absolute_path)
    label_column = resolve_label_column(reference_header)
    assert label_column
    for item in discovered[:5]:
        header = read_csv_header(item.absolute_path)
        validate_consistent_header(reference_header, header)
