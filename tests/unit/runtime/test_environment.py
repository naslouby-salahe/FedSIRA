import os

import torch

from fedsira.domain.enums import (
    CublasWorkspaceConfig,
    EnvironmentVariableName,
)
from fedsira.runtime import (
    check_unrar_availability,
    collect_environment_mismatches,
    configure_deterministic_backend,
)


def test_collect_environment_mismatches_returns_capability_observations() -> None:
    mismatches = collect_environment_mismatches(rar_archives_present=False)
    assert isinstance(mismatches, tuple)
    for mismatch in mismatches:
        assert mismatch.component
        assert mismatch.expected
        assert mismatch.actual


def test_check_unrar_availability_is_not_required_without_archives() -> None:
    assert check_unrar_availability(rar_archives_present=False) == ()


def test_check_unrar_availability_reports_capability_when_archives_exist() -> None:
    assert isinstance(check_unrar_availability(rar_archives_present=True), tuple)


def test_configure_deterministic_backend_sets_cublas_workspace_config() -> None:
    configure_deterministic_backend()
    cublas_workspace_config = os.environ[EnvironmentVariableName.CUBLAS_WORKSPACE_CONFIG]
    assert cublas_workspace_config == CublasWorkspaceConfig.REFERENCE
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False
    torch.use_deterministic_algorithms(False)
