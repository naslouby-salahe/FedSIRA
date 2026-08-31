import importlib.metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Protocol, cast

import torch

from fedsira.config.models import ReferenceEnvironmentConfig
from fedsira.domain.types import (
    ByteCount,
    DeterministicExecutionReady,
    EnvironmentText,
    FrozenDomainModel,
    MasterSeed,
    RarArchivesPresent,
)
from fedsira.runtime.state import current_application_context

BYTES_PER_GIGABYTE: ByteCount = 1_073_741_824
PREPROCESSING_OR_REPORT_ONLY_HASHSEED: EnvironmentText = "0"


def _reference_environment() -> ReferenceEnvironmentConfig:
    return current_application_context().scientific_config.runtime.reference_environment


class PackageVersionRequirement(FrozenDomainModel):
    package: EnvironmentText
    version: EnvironmentText


REFERENCE_PACKAGE_REQUIREMENTS: tuple[PackageVersionRequirement, ...] = (
    PackageVersionRequirement(package="torch", version="2.9.0"),
    PackageVersionRequirement(package="numpy", version="2.1.3"),
    PackageVersionRequirement(package="pandas", version="2.2.3"),
    PackageVersionRequirement(package="scipy", version="1.14.1"),
    PackageVersionRequirement(package="scikit-learn", version="1.5.2"),
    PackageVersionRequirement(package="pyarrow", version="17.0.0"),
    PackageVersionRequirement(package="pydantic", version="2.9.2"),
    PackageVersionRequirement(package="typer", version="0.12.5"),
    PackageVersionRequirement(package="rich", version="13.9.4"),
    PackageVersionRequirement(package="matplotlib", version="3.9.2"),
    PackageVersionRequirement(package="statsmodels", version="0.14.4"),
    PackageVersionRequirement(package="pytest", version="8.3.3"),
)


class EnvironmentMismatch(FrozenDomainModel):
    component: EnvironmentText
    expected: EnvironmentText
    actual: EnvironmentText


class _Fp32PrecisionController(Protocol):
    fp32_precision: EnvironmentText


def pythonhashseed_for_master_seed_subprocess(master_seed: MasterSeed) -> EnvironmentText:
    return str(master_seed)


def pythonhashseed_for_smoke_subprocess(smoke_seed: MasterSeed) -> EnvironmentText:
    return str(smoke_seed)


def pythonhashseed_for_preprocessing_or_report_subprocess() -> EnvironmentText:
    return PREPROCESSING_OR_REPORT_ONLY_HASHSEED


def check_python_version() -> tuple[EnvironmentMismatch, ...]:
    actual: EnvironmentText = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    expected = _reference_environment().python_version
    if actual != expected:
        return (
            EnvironmentMismatch(
                component="python",
                expected=expected,
                actual=actual,
            ),
        )
    return ()


def check_installed_package_versions() -> tuple[EnvironmentMismatch, ...]:
    mismatches: list[EnvironmentMismatch] = []
    for requirement in REFERENCE_PACKAGE_REQUIREMENTS:
        try:
            actual_version = importlib.metadata.version(requirement.package)
        except importlib.metadata.PackageNotFoundError:
            mismatches.append(
                EnvironmentMismatch(
                    component=requirement.package,
                    expected=requirement.version,
                    actual="not installed",
                )
            )
            continue
        if actual_version != requirement.version:
            mismatches.append(
                EnvironmentMismatch(
                    component=requirement.package,
                    expected=requirement.version,
                    actual=actual_version,
                )
            )
    return tuple(mismatches)


def check_gpu_requirements() -> tuple[EnvironmentMismatch, ...]:
    mismatches: list[EnvironmentMismatch] = []
    reference = _reference_environment()
    if not torch.cuda.is_available():
        return (
            EnvironmentMismatch(
                component="gpu_availability",
                expected="available",
                actual="unavailable",
            ),
        )
    device_count = torch.cuda.device_count()
    if device_count != reference.required_gpu_count:
        mismatches.append(
            EnvironmentMismatch(
                component="gpu_count",
                expected=str(reference.required_gpu_count),
                actual=str(device_count),
            )
        )
    cuda_version = torch.version.cuda
    if cuda_version != reference.cuda_runtime_version:
        mismatches.append(
            EnvironmentMismatch(
                component="cuda_runtime_version",
                expected=reference.cuda_runtime_version,
                actual=str(cuda_version),
            )
        )
    device_name = torch.cuda.get_device_name(0)
    if device_name != reference.gpu_name:
        mismatches.append(
            EnvironmentMismatch(
                component="gpu_name",
                expected=reference.gpu_name,
                actual=device_name,
            )
        )
    _, total_memory_bytes = torch.cuda.mem_get_info(0)
    vram_gigabytes = total_memory_bytes / BYTES_PER_GIGABYTE
    if round(vram_gigabytes) < reference.gpu_vram_gigabytes:
        mismatches.append(
            EnvironmentMismatch(
                component="gpu_vram_gigabytes",
                expected=f">={reference.gpu_vram_gigabytes}",
                actual=f"{vram_gigabytes:.1f}",
            )
        )
    return tuple(mismatches)


def _os_release_field(
    lines: tuple[EnvironmentText, ...],
    field_name: EnvironmentText,
) -> EnvironmentText | None:
    prefix = f"{field_name}="
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip('"')
    return None


def check_operating_system() -> tuple[EnvironmentMismatch, ...]:
    os_release_path = Path("/etc/os-release")
    reference = _reference_environment()
    expected: EnvironmentText = f"{reference.os_name} {reference.os_version_id}"
    if not os_release_path.exists():
        return (
            EnvironmentMismatch(
                component="operating_system",
                expected=expected,
                actual="unknown",
            ),
        )
    lines = tuple(os_release_path.read_text(encoding="utf-8").splitlines())
    observed_name = _os_release_field(lines, "NAME")
    observed_version = _os_release_field(lines, "VERSION_ID")
    actual: EnvironmentText = f"{observed_name or ''} {observed_version or ''}".strip()
    if observed_name != reference.os_name or observed_version != reference.os_version_id:
        return (
            EnvironmentMismatch(
                component="operating_system",
                expected=expected,
                actual=actual or "unknown",
            ),
        )
    return ()


def check_hardware_resources(workspace_path: Path) -> tuple[EnvironmentMismatch, ...]:
    mismatches: list[EnvironmentMismatch] = []
    total_ram_gigabytes = (
        os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    ) / BYTES_PER_GIGABYTE
    reference = _reference_environment()
    if total_ram_gigabytes < reference.minimum_cpu_ram_gigabytes:
        mismatches.append(
            EnvironmentMismatch(
                component="cpu_ram_gigabytes",
                expected=f">={reference.minimum_cpu_ram_gigabytes}",
                actual=f"{total_ram_gigabytes:.1f}",
            )
        )
    free_storage_gigabytes = shutil.disk_usage(workspace_path).free / BYTES_PER_GIGABYTE
    if free_storage_gigabytes < reference.minimum_free_storage_gigabytes:
        mismatches.append(
            EnvironmentMismatch(
                component="free_storage_gigabytes",
                expected=f">={reference.minimum_free_storage_gigabytes}",
                actual=f"{free_storage_gigabytes:.1f}",
            )
        )
    return tuple(mismatches)


def check_unrar_availability(
    rar_archives_present: RarArchivesPresent,
) -> tuple[EnvironmentMismatch, ...]:
    if not rar_archives_present:
        return ()
    expected = _reference_environment().unrar_version
    try:
        result = subprocess.run(
            ["dpkg-query", "--showformat=${Version}", "--show", "unrar"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return (
            EnvironmentMismatch(
                component="unrar_version",
                expected=expected,
                actual="not installed",
            ),
        )
    actual_version: EnvironmentText = result.stdout.strip() or "not installed"
    if result.returncode != 0 or actual_version != expected:
        return (
            EnvironmentMismatch(
                component="unrar_version",
                expected=expected,
                actual=actual_version,
            ),
        )
    return ()


def configure_deterministic_backend() -> None:
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = _reference_environment().cublas_workspace_config
    torch.use_deterministic_algorithms(True, warn_only=False)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    cudnn_conv = cast(_Fp32PrecisionController, getattr(torch.backends.cudnn, "conv"))
    cudnn_conv.fp32_precision = "ieee"


def collect_environment_mismatches(
    workspace_path: Path,
    rar_archives_present: RarArchivesPresent,
) -> tuple[EnvironmentMismatch, ...]:
    return (
        check_operating_system()
        + check_python_version()
        + check_installed_package_versions()
        + check_gpu_requirements()
        + check_hardware_resources(workspace_path)
        + check_unrar_availability(rar_archives_present)
    )


def deterministic_execution_available(
    workspace_path: Path,
    rar_archives_present: RarArchivesPresent,
) -> DeterministicExecutionReady:
    return not collect_environment_mismatches(workspace_path, rar_archives_present)
