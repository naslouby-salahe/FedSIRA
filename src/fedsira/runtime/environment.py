import importlib.metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Protocol, cast

import torch

from fedsira.domain.records import (
    BooleanValue,
    DeterministicExecutionReady,
    EnvironmentText,
    FrozenDomainModel,
    MasterSeed,
    PositiveInt,
)

REFERENCE_OS_NAME: EnvironmentText = "Ubuntu"
REFERENCE_OS_VERSION_ID: EnvironmentText = "24.04"
REFERENCE_PYTHON_VERSION: EnvironmentText = "3.11.9"
REFERENCE_CUDA_RUNTIME_VERSION: EnvironmentText = "12.8"
REFERENCE_GPU_NAME: EnvironmentText = "NVIDIA GeForce RTX 5060 Ti"
REFERENCE_GPU_VRAM_GIGABYTES: PositiveInt = 16
MINIMUM_CPU_RAM_GIGABYTES: PositiveInt = 32
MINIMUM_FREE_STORAGE_GIGABYTES: PositiveInt = 100
REQUIRED_GPU_COUNT: PositiveInt = 1
BYTES_PER_GIGABYTE: PositiveInt = 1_073_741_824
REFERENCE_UNRAR_VERSION: EnvironmentText = "1:7.0.7-1build1"
CUBLAS_WORKSPACE_CONFIG_VALUE: EnvironmentText = ":4096:8"
PREPROCESSING_OR_REPORT_ONLY_HASHSEED: EnvironmentText = "0"


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
    if actual != REFERENCE_PYTHON_VERSION:
        return (
            EnvironmentMismatch(
                component="python",
                expected=REFERENCE_PYTHON_VERSION,
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
    if not torch.cuda.is_available():
        return (
            EnvironmentMismatch(
                component="gpu_availability",
                expected="available",
                actual="unavailable",
            ),
        )
    device_count = torch.cuda.device_count()
    if device_count != REQUIRED_GPU_COUNT:
        mismatches.append(
            EnvironmentMismatch(
                component="gpu_count",
                expected=str(REQUIRED_GPU_COUNT),
                actual=str(device_count),
            )
        )
    cuda_version = torch.version.cuda
    if cuda_version != REFERENCE_CUDA_RUNTIME_VERSION:
        mismatches.append(
            EnvironmentMismatch(
                component="cuda_runtime_version",
                expected=REFERENCE_CUDA_RUNTIME_VERSION,
                actual=str(cuda_version),
            )
        )
    device_name = torch.cuda.get_device_name(0)
    if device_name != REFERENCE_GPU_NAME:
        mismatches.append(
            EnvironmentMismatch(
                component="gpu_name",
                expected=REFERENCE_GPU_NAME,
                actual=device_name,
            )
        )
    _, total_memory_bytes = torch.cuda.mem_get_info(0)
    vram_gigabytes = total_memory_bytes / BYTES_PER_GIGABYTE
    if round(vram_gigabytes) < REFERENCE_GPU_VRAM_GIGABYTES:
        mismatches.append(
            EnvironmentMismatch(
                component="gpu_vram_gigabytes",
                expected=f">={REFERENCE_GPU_VRAM_GIGABYTES}",
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
    expected: EnvironmentText = f"{REFERENCE_OS_NAME} {REFERENCE_OS_VERSION_ID}"
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
    if observed_name != REFERENCE_OS_NAME or observed_version != REFERENCE_OS_VERSION_ID:
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
    if total_ram_gigabytes < MINIMUM_CPU_RAM_GIGABYTES:
        mismatches.append(
            EnvironmentMismatch(
                component="cpu_ram_gigabytes",
                expected=f">={MINIMUM_CPU_RAM_GIGABYTES}",
                actual=f"{total_ram_gigabytes:.1f}",
            )
        )
    free_storage_gigabytes = shutil.disk_usage(workspace_path).free / BYTES_PER_GIGABYTE
    if free_storage_gigabytes < MINIMUM_FREE_STORAGE_GIGABYTES:
        mismatches.append(
            EnvironmentMismatch(
                component="free_storage_gigabytes",
                expected=f">={MINIMUM_FREE_STORAGE_GIGABYTES}",
                actual=f"{free_storage_gigabytes:.1f}",
            )
        )
    return tuple(mismatches)


def check_unrar_availability(
    rar_archives_present: BooleanValue,
) -> tuple[EnvironmentMismatch, ...]:
    if not rar_archives_present:
        return ()
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
                expected=REFERENCE_UNRAR_VERSION,
                actual="not installed",
            ),
        )
    actual_version: EnvironmentText = result.stdout.strip() or "not installed"
    if result.returncode != 0 or actual_version != REFERENCE_UNRAR_VERSION:
        return (
            EnvironmentMismatch(
                component="unrar_version",
                expected=REFERENCE_UNRAR_VERSION,
                actual=actual_version,
            ),
        )
    return ()


def configure_deterministic_backend() -> None:
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = CUBLAS_WORKSPACE_CONFIG_VALUE
    torch.use_deterministic_algorithms(True, warn_only=False)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    cudnn_conv = cast(_Fp32PrecisionController, torch.backends.cudnn.conv)
    cudnn_conv.fp32_precision = "ieee"


def collect_environment_mismatches(
    workspace_path: Path,
    rar_archives_present: BooleanValue,
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
    rar_archives_present: BooleanValue,
) -> DeterministicExecutionReady:
    return not collect_environment_mismatches(workspace_path, rar_archives_present)
