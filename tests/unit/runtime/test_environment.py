import os
from pathlib import Path

import torch

from fedsira.runtime.environment import (
    PREPROCESSING_OR_REPORT_ONLY_HASHSEED,
    check_hardware_resources,
    check_installed_package_versions,
    check_operating_system,
    check_python_version,
    check_unrar_availability,
    collect_environment_mismatches,
    configure_deterministic_backend,
    pythonhashseed_for_master_seed_subprocess,
    pythonhashseed_for_preprocessing_or_report_subprocess,
    pythonhashseed_for_smoke_subprocess,
)
from fedsira.runtime.state import current_application_context


def test_pythonhashseed_for_master_seed_subprocess_is_decimal_of_the_seed() -> None:
    assert pythonhashseed_for_master_seed_subprocess(1103) == "1103"


def test_pythonhashseed_for_smoke_subprocess_tracks_the_configured_smoke_seed() -> None:
    assert pythonhashseed_for_smoke_subprocess(900001) == "900001"


def test_pythonhashseed_for_preprocessing_or_report_subprocess_is_zero() -> None:
    assert pythonhashseed_for_preprocessing_or_report_subprocess() == "0"
    assert PREPROCESSING_OR_REPORT_ONLY_HASHSEED == "0"


def test_check_python_version_reports_the_running_interpreter() -> None:
    mismatches = check_python_version()
    assert isinstance(mismatches, tuple)


def test_check_installed_package_versions_reports_pydantic() -> None:
    mismatches = check_installed_package_versions()
    components = {mismatch.component for mismatch in mismatches}
    assert isinstance(components, set)


def test_collect_environment_mismatches_returns_a_tuple() -> None:
    mismatches = collect_environment_mismatches(Path.cwd(), rar_archives_present=False)
    assert isinstance(mismatches, tuple)
    for mismatch in mismatches:
        assert mismatch.component
        assert mismatch.expected
        assert mismatch.actual


def test_check_operating_system_reports_a_tuple() -> None:
    mismatches = check_operating_system()
    assert isinstance(mismatches, tuple)


def test_check_hardware_resources_reports_a_tuple() -> None:
    mismatches = check_hardware_resources(Path.cwd())
    assert isinstance(mismatches, tuple)


def test_check_unrar_availability_is_a_no_op_when_no_rar_archives_present() -> None:
    assert check_unrar_availability(rar_archives_present=False) == ()


def test_check_unrar_availability_reports_a_mismatch_when_version_absent_or_wrong() -> None:
    mismatches = check_unrar_availability(rar_archives_present=True)
    assert isinstance(mismatches, tuple)
    for mismatch in mismatches:
        expected = (
            current_application_context().scientific_config.runtime.reference_environment.unrar_version
        )
        assert mismatch.expected == expected


def test_configure_deterministic_backend_sets_cublas_workspace_config() -> None:
    configure_deterministic_backend()
    expected_workspace = (
        current_application_context().scientific_config.runtime.reference_environment.cublas_workspace_config
    )
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == expected_workspace
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False
    torch.use_deterministic_algorithms(False)
