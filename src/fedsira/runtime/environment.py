import importlib.metadata
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import torch

from fedsira.domain.records import EnvironmentText, MasterSeed

REFERENCE_OS_NAME = "Ubuntu"
REFERENCE_OS_VERSION_ID = "24.04"
REFERENCE_PYTHON_VERSION = "3.11.9"
REFERENCE_PACKAGE_VERSIONS: dict[str, str] = {
    "torch": "2.9.0",
    "numpy": "2.1.3",
    "pandas": "2.2.3",
    "scipy": "1.14.1",
    "scikit-learn": "1.5.2",
    "pyarrow": "17.0.0",
    "pydantic": "2.9.2",
    "typer": "0.12.5",
    "rich": "13.9.4",
    "matplotlib": "3.9.2",
    "statsmodels": "0.14.4",
    "pytest": "8.3.3",
}
REFERENCE_CUDA_RUNTIME_VERSION = "12.8"
REFERENCE_GPU_NAME = "NVIDIA GeForce RTX 5060 Ti"
REFERENCE_GPU_VRAM_GIGABYTES = 16
MINIMUM_CPU_RAM_GIGABYTES = 32
MINIMUM_FREE_STORAGE_GIGABYTES = 100
REQUIRED_GPU_COUNT = 1
BYTES_PER_GIGABYTE = 1_073_741_824
REFERENCE_UNRAR_VERSION = "1:7.0.7-1build1"

CUBLAS_WORKSPACE_CONFIG_VALUE = ":4096:8"
PREPROCESSING_OR_REPORT_ONLY_HASHSEED = "0"


@dataclass(frozen=True)
class EnvironmentMismatch:
    component: EnvironmentText
    expected: EnvironmentText
    actual: EnvironmentText


def pythonhashseed_for_master_seed_subprocess(master_seed: MasterSeed) -> str:
    return str(master_seed)


def pythonhashseed_for_smoke_subprocess(smoke_seed: MasterSeed) -> str:
    return str(smoke_seed)


def pythonhashseed_for_preprocessing_or_report_subprocess() -> str:
    return PREPROCESSING_OR_REPORT_ONLY_HASHSEED


def check_python_version() -> tuple[EnvironmentMismatch, ...]:
    actual = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if actual != REFERENCE_PYTHON_VERSION:
        return (EnvironmentMismatch("python", REFERENCE_PYTHON_VERSION, actual),)
    return ()


def check_installed_package_versions() -> tuple[EnvironmentMismatch, ...]:
    mismatches: list[EnvironmentMismatch] = []
    for package, expected_version in REFERENCE_PACKAGE_VERSIONS.items():
        try:
            actual_version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            mismatches.append(EnvironmentMismatch(package, expected_version, "not installed"))
            continue
        if actual_version != expected_version:
            mismatches.append(EnvironmentMismatch(package, expected_version, actual_version))
    return tuple(mismatches)


def check_gpu_requirements() -> tuple[EnvironmentMismatch, ...]:
    mismatches: list[EnvironmentMismatch] = []
    if not torch.cuda.is_available():
        mismatches.append(EnvironmentMismatch("gpu_availability", "available", "unavailable"))
        return tuple(mismatches)
    device_count = torch.cuda.device_count()
    if device_count != REQUIRED_GPU_COUNT:
        mismatches.append(
            EnvironmentMismatch("gpu_count", str(REQUIRED_GPU_COUNT), str(device_count))
        )
    cuda_version = torch.version.cuda
    if cuda_version != REFERENCE_CUDA_RUNTIME_VERSION:
        mismatches.append(
            EnvironmentMismatch(
                "cuda_runtime_version", REFERENCE_CUDA_RUNTIME_VERSION, str(cuda_version)
            )
        )
    device_name = torch.cuda.get_device_name(0)
    if device_name != REFERENCE_GPU_NAME:
        mismatches.append(EnvironmentMismatch("gpu_name", REFERENCE_GPU_NAME, device_name))
    _, total_memory_bytes = torch.cuda.mem_get_info(0)
    vram_gigabytes = total_memory_bytes / BYTES_PER_GIGABYTE
    if round(vram_gigabytes) < REFERENCE_GPU_VRAM_GIGABYTES:
        mismatches.append(
            EnvironmentMismatch(
                "gpu_vram_gigabytes",
                f">={REFERENCE_GPU_VRAM_GIGABYTES}",
                f"{vram_gigabytes:.1f}",
            )
        )
    return tuple(mismatches)


def check_operating_system() -> tuple[EnvironmentMismatch, ...]:
    os_release_path = Path("/etc/os-release")
    expected = f"{REFERENCE_OS_NAME} {REFERENCE_OS_VERSION_ID}"
    if not os_release_path.exists():
        return (EnvironmentMismatch("operating_system", expected, "unknown"),)
    fields: dict[str, str] = {}
    for line in os_release_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        fields[key] = value.strip('"')
    actual = f"{fields.get('NAME', '')} {fields.get('VERSION_ID', '')}"
    if (
        fields.get("NAME") != REFERENCE_OS_NAME
        or fields.get("VERSION_ID") != REFERENCE_OS_VERSION_ID
    ):
        return (EnvironmentMismatch("operating_system", expected, actual),)
    return ()


def check_hardware_resources(workspace_path: Path) -> tuple[EnvironmentMismatch, ...]:
    mismatches: list[EnvironmentMismatch] = []
    total_ram_gigabytes = (
        os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    ) / BYTES_PER_GIGABYTE
    if total_ram_gigabytes < MINIMUM_CPU_RAM_GIGABYTES:
        mismatches.append(
            EnvironmentMismatch(
                "cpu_ram_gigabytes",
                f">={MINIMUM_CPU_RAM_GIGABYTES}",
                f"{total_ram_gigabytes:.1f}",
            )
        )
    free_storage_gigabytes = shutil.disk_usage(workspace_path).free / BYTES_PER_GIGABYTE
    if free_storage_gigabytes < MINIMUM_FREE_STORAGE_GIGABYTES:
        mismatches.append(
            EnvironmentMismatch(
                "free_storage_gigabytes",
                f">={MINIMUM_FREE_STORAGE_GIGABYTES}",
                f"{free_storage_gigabytes:.1f}",
            )
        )
    return tuple(mismatches)


def check_unrar_availability(rar_archives_present: bool) -> tuple[EnvironmentMismatch, ...]:
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
        return (EnvironmentMismatch("unrar_version", REFERENCE_UNRAR_VERSION, "not installed"),)
    actual_version = result.stdout.strip()
    if result.returncode != 0 or actual_version != REFERENCE_UNRAR_VERSION:
        return (
            EnvironmentMismatch(
                "unrar_version", REFERENCE_UNRAR_VERSION, actual_version or "not installed"
            ),
        )
    return ()


def configure_deterministic_backend() -> None:
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = CUBLAS_WORKSPACE_CONFIG_VALUE
    torch.use_deterministic_algorithms(True, warn_only=False)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    torch.backends.cudnn.conv.fp32_precision = "ieee"


def collect_environment_mismatches(
    workspace_path: Path, rar_archives_present: bool
) -> tuple[EnvironmentMismatch, ...]:
    return (
        check_operating_system()
        + check_python_version()
        + check_installed_package_versions()
        + check_gpu_requirements()
        + check_hardware_resources(workspace_path)
        + check_unrar_availability(rar_archives_present)
    )


def deterministic_execution_available(workspace_path: Path, rar_archives_present: bool) -> bool:
    return len(collect_environment_mismatches(workspace_path, rar_archives_present)) == 0
