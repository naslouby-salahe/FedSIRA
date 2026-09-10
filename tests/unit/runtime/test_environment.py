import os
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import torch

from fedsira.artifacts.provenance import collect_reconstruction_provenance
from fedsira.runtime import (
    REFERENCE_CUBLAS_WORKSPACE_CONFIG,
    REFERENCE_UNRAR_VERSION,
    check_hardware_resources,
    check_installed_package_versions,
    check_operating_system,
    check_python_version,
    check_unrar_availability,
    collect_environment_mismatches,
    configure_deterministic_backend,
)


def test_check_python_version_reports_the_running_interpreter() -> None:
    mismatches = check_python_version()
    assert isinstance(mismatches, tuple)


def test_check_installed_package_versions_reports_pydantic() -> None:
    mismatches = check_installed_package_versions()
    components = {mismatch.component for mismatch in mismatches}
    assert isinstance(components, set)


def test_collect_environment_mismatches_returns_a_tuple() -> None:
    mismatches = collect_environment_mismatches(rar_archives_present=False)
    assert isinstance(mismatches, tuple)
    for mismatch in mismatches:
        assert mismatch.component
        assert mismatch.expected
        assert mismatch.actual


def test_check_operating_system_reports_a_tuple() -> None:
    mismatches = check_operating_system()
    assert isinstance(mismatches, tuple)


def test_check_hardware_resources_reports_a_tuple() -> None:
    mismatches = check_hardware_resources()
    assert isinstance(mismatches, tuple)


def test_check_unrar_availability_is_a_no_op_when_no_rar_archives_present() -> None:
    assert check_unrar_availability(rar_archives_present=False) == ()


def test_check_unrar_availability_reports_a_mismatch_when_version_absent_or_wrong() -> None:
    mismatches = check_unrar_availability(rar_archives_present=True)
    assert isinstance(mismatches, tuple)
    for mismatch in mismatches:
        assert mismatch.expected == REFERENCE_UNRAR_VERSION


def test_collect_reconstruction_provenance_uses_current_commit_and_lock(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("lock-data", encoding="utf-8")
    completed = CompletedProcess(args=("git",), returncode=0, stdout="a" * 40 + "\n", stderr="")
    with patch("fedsira.runtime.subprocess.run", return_value=completed):
        provenance = collect_reconstruction_provenance(tmp_path)
    assert provenance.repository_commit == "a" * 40
    assert len(provenance.dependency_lock_digest) == 64
    assert len(provenance.environment_fingerprint) == 64


def test_configure_deterministic_backend_sets_cublas_workspace_config() -> None:
    configure_deterministic_backend()
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == REFERENCE_CUBLAS_WORKSPACE_CONFIG
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False
    torch.use_deterministic_algorithms(False)
