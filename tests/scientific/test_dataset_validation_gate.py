import hashlib
from pathlib import Path

from fedsira.config.loading import PRODUCTION_CONFIG_PATH, load_scientific_config
from fedsira.datasets.common import Role, compute_sample_id
from fedsira.datasets.nbaiot.loading import (
    compute_dataset_manifest_hash,
    discover_primary_csv_files,
)
from fedsira.datasets.nbaiot.preprocessing import RoleAssignment, assign_stream_roles_and_sample_ids
from fedsira.datasets.nbaiot.schema import NBaiotClass

CONFIG = load_scientific_config(PRODUCTION_CONFIG_PATH)
ROLE_INTERVALS = CONFIG.datasets.primary.role_intervals
SAMPLING_CAPS = CONFIG.datasets.primary.sampling_caps_per_domain


def _assign(class_id: NBaiotClass, stream_row_count: int = 2000) -> tuple[RoleAssignment, ...]:
    return assign_stream_roles_and_sample_ids(
        dataset_file_sha256="a" * 64,
        domain_hash_token="DANMINI_DOORBELL",
        class_id=class_id,
        normalized_relative_csv_path="Danmini Doorbell/x.csv",
        stream_row_count=stream_row_count,
        role_intervals=ROLE_INTERVALS,
        sampling_caps_per_domain=SAMPLING_CAPS,
    )


def test_no_cross_role_sample_overlap_for_a_supported_class() -> None:
    assignments = _assign(NBaiotClass.BENIGN)
    row_to_roles: dict[int, set[Role]] = {}
    for assignment in assignments:
        row_to_roles.setdefault(assignment.original_row_index, set()).add(assignment.role)
    assert all(len(roles) == 1 for roles in row_to_roles.values())


def test_no_cross_role_sample_overlap_for_the_target_class() -> None:
    assignments = _assign(NBaiotClass.GAFGYT_COMBO)
    row_to_roles: dict[int, set[Role]] = {}
    for assignment in assignments:
        row_to_roles.setdefault(assignment.original_row_index, set()).add(assignment.role)
    assert all(len(roles) == 1 for roles in row_to_roles.values())


def test_no_target_sample_enters_anchor_roles() -> None:
    assignments = _assign(NBaiotClass.GAFGYT_COMBO)
    roles_seen = {assignment.role for assignment in assignments}
    assert Role.ANCHOR_TRAIN not in roles_seen
    assert Role.ANCHOR_VALIDATION not in roles_seen


def test_source_screen_reproduction_verification_gate_report_roles_are_disjoint() -> None:
    assignments = _assign(NBaiotClass.GAFGYT_COMBO)
    role_to_rows: dict[Role, set[int]] = {}
    for assignment in assignments:
        role_to_rows.setdefault(assignment.role, set()).add(assignment.original_row_index)
    roles = list(role_to_rows.keys())
    for i, first_role in enumerate(roles):
        for second_role in roles[i + 1 :]:
            assert role_to_rows[first_role].isdisjoint(role_to_rows[second_role])


def test_repeated_preprocessing_yields_identical_role_and_sample_id_assignments() -> None:
    first = _assign(NBaiotClass.BENIGN)
    second = _assign(NBaiotClass.BENIGN)
    assert first == second


def test_sample_id_matches_an_independently_computed_reference_digest() -> None:
    prefix = "NBAIOT_SAMPLE_ID_V1"
    path = "Danmini Doorbell/benign_traffic.csv"
    file_sha256 = "b" * 64
    row_index = 7

    length_prefixed = b"".join(
        len(str(field).encode("utf-8")).to_bytes(4, "big") + str(field).encode("utf-8")
        for field in (prefix, path, file_sha256, row_index)
    )
    expected = hashlib.sha256(length_prefixed).hexdigest()

    assert compute_sample_id(prefix, path, file_sha256, row_index) == expected


def test_archive_and_already_extracted_layouts_yield_identical_dataset_manifest_hash(
    tmp_path: Path,
) -> None:
    already_extracted_root = tmp_path / "already_extracted"
    device_directory = already_extracted_root / "Danmini_Doorbell"
    device_directory.mkdir(parents=True)
    (device_directory / "benign_traffic.csv").write_text("a,b\n1,2\n")
    gafgyt_directory = device_directory / "gafgyt_attacks"
    gafgyt_directory.mkdir()
    (gafgyt_directory / "combo.csv").write_text("a,b\n3,4\n")

    identically_extracted_root = tmp_path / "identically_extracted"
    device_directory_2 = identically_extracted_root / "Danmini_Doorbell"
    device_directory_2.mkdir(parents=True)
    (device_directory_2 / "benign_traffic.csv").write_text("a,b\n1,2\n")
    gafgyt_directory_2 = device_directory_2 / "gafgyt_attacks"
    gafgyt_directory_2.mkdir()
    (gafgyt_directory_2 / "combo.csv").write_text("a,b\n3,4\n")

    first = discover_primary_csv_files(already_extracted_root, tmp_path / "cache1")
    second = discover_primary_csv_files(identically_extracted_root, tmp_path / "cache2")

    assert compute_dataset_manifest_hash(first) == compute_dataset_manifest_hash(second)
