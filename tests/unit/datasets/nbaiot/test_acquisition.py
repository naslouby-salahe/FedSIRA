from pathlib import Path

import pytest

from fedsira.datasets.nbaiot.acquisition import (
    compute_dataset_manifest_hash,
    compute_file_checksum,
    discover_primary_csv_files,
)
from fedsira.datasets.nbaiot.schema import NBaiotClass, NBaiotDomain


def _write_device(
    root: Path,
    directory_name: str,
    benign_rows: str = "a,b\n1,2\n",
    gafgyt_basenames: tuple[str, ...] = ("combo",),
    mirai_basenames: tuple[str, ...] = (),
) -> None:
    device_directory = root / directory_name
    device_directory.mkdir(parents=True)
    (device_directory / "benign_traffic.csv").write_text(benign_rows)
    if gafgyt_basenames:
        gafgyt_directory = device_directory / "gafgyt_attacks"
        gafgyt_directory.mkdir()
        for basename in gafgyt_basenames:
            (gafgyt_directory / f"{basename}.csv").write_text("a,b\n1,2\n")
    if mirai_basenames:
        mirai_directory = device_directory / "mirai_attacks"
        mirai_directory.mkdir()
        for basename in mirai_basenames:
            (mirai_directory / f"{basename}.csv").write_text("a,b\n1,2\n")


def test_discover_primary_csv_files_maps_benign_and_gafgyt(tmp_path: Path) -> None:
    _write_device(tmp_path, "Danmini_Doorbell", gafgyt_basenames=("combo", "junk"))
    discovered = discover_primary_csv_files(tmp_path, tmp_path / "cache")
    classes = {item.class_id for item in discovered}
    assert classes == {NBaiotClass.BENIGN, NBaiotClass.GAFGYT_COMBO, NBaiotClass.GAFGYT_JUNK}
    assert all(item.domain is NBaiotDomain.DANMINI_DOORBELL for item in discovered)


def test_discover_primary_csv_files_handles_missing_mirai_directory(tmp_path: Path) -> None:
    _write_device(tmp_path, "Ennio_Doorbell", mirai_basenames=())
    discovered = discover_primary_csv_files(tmp_path, tmp_path / "cache")
    assert not any(item.class_id.value.startswith("MIRAI") for item in discovered)


def test_discover_primary_csv_files_rejects_unrecognized_device_directory(tmp_path: Path) -> None:
    _write_device(tmp_path, "Unknown_Device")
    with pytest.raises(ValueError, match="unrecognized N-BaIoT device directory"):
        discover_primary_csv_files(tmp_path, tmp_path / "cache")


def test_discover_primary_csv_files_rejects_unrecognized_attack_basename(tmp_path: Path) -> None:
    device_directory = tmp_path / "Danmini_Doorbell"
    device_directory.mkdir()
    gafgyt_directory = device_directory / "gafgyt_attacks"
    gafgyt_directory.mkdir()
    (gafgyt_directory / "not_a_real_attack.csv").write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="unrecognized gafgyt attack basename"):
        discover_primary_csv_files(tmp_path, tmp_path / "cache")


def test_discover_primary_csv_files_ignores_non_directory_top_level_entries(tmp_path: Path) -> None:
    _write_device(tmp_path, "Danmini_Doorbell")
    (tmp_path / "N_BaIoT_dataset_description_v1.txt").write_text("description")
    (tmp_path / "demonstrate_structure.csv").write_text("a,b\n1,2\n")
    discovered = discover_primary_csv_files(tmp_path, tmp_path / "cache")
    assert len(discovered) == 2


def test_discover_primary_csv_files_is_ordered_deterministically(tmp_path: Path) -> None:
    _write_device(tmp_path, "Danmini_Doorbell", gafgyt_basenames=("combo", "junk"))
    _write_device(tmp_path, "Ennio_Doorbell", gafgyt_basenames=("combo",))
    first = discover_primary_csv_files(tmp_path, tmp_path / "cache")
    second = discover_primary_csv_files(tmp_path, tmp_path / "cache")
    assert [item.relative_path for item in first] == [item.relative_path for item in second]


def test_compute_file_checksum_is_a_sha256_hex_digest(tmp_path: Path) -> None:
    path = tmp_path / "file.csv"
    path.write_text("a,b\n1,2\n")
    digest = compute_file_checksum(path)
    assert len(digest) == 64
    bytes.fromhex(digest)


def test_compute_dataset_manifest_hash_is_deterministic_and_order_independent(
    tmp_path: Path,
) -> None:
    _write_device(tmp_path, "Danmini_Doorbell", gafgyt_basenames=("combo", "junk"))
    discovered = discover_primary_csv_files(tmp_path, tmp_path / "cache")
    reversed_discovered = tuple(reversed(discovered))
    assert compute_dataset_manifest_hash(discovered) == compute_dataset_manifest_hash(
        reversed_discovered
    )


def test_compute_dataset_manifest_hash_changes_when_a_file_changes(tmp_path: Path) -> None:
    _write_device(tmp_path, "Danmini_Doorbell")
    before = discover_primary_csv_files(tmp_path, tmp_path / "cache")
    (tmp_path / "Danmini_Doorbell" / "benign_traffic.csv").write_text("a,b\n9,9\n")
    after = discover_primary_csv_files(tmp_path, tmp_path / "cache")
    assert compute_dataset_manifest_hash(before) != compute_dataset_manifest_hash(after)


REAL_NBAIOT_ROOT = Path("/home/naslouby/Projects/datp-shared-data/raw/N-BaIoT")


@pytest.mark.skipif(not REAL_NBAIOT_ROOT.is_dir(), reason="real N-BaIoT raw data not available")
def test_discover_primary_csv_files_against_real_raw_data(tmp_path: Path) -> None:
    discovered = discover_primary_csv_files(REAL_NBAIOT_ROOT, tmp_path / "cache")
    domains_present = {item.domain for item in discovered}
    assert len(domains_present) == 9
    benign_files = [item for item in discovered if item.class_id is NBaiotClass.BENIGN]
    assert len(benign_files) == 9
    combo_domains = {
        item.domain for item in discovered if item.class_id is NBaiotClass.GAFGYT_COMBO
    }
    assert len(combo_domains) == 9
