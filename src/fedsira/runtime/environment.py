import importlib.metadata
import os
import sys
from dataclasses import dataclass

import torch

from fedsira.domain.records import CanonicalToken, MasterSeed

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
REFERENCE_UNRAR_VERSION = "1:7.0.7-1build1"

CUBLAS_WORKSPACE_CONFIG_VALUE = ":4096:8"
PREPROCESSING_OR_REPORT_ONLY_HASHSEED = "0"


@dataclass(frozen=True)
class EnvironmentMismatch:
    component: CanonicalToken
    expected: CanonicalToken
    actual: CanonicalToken


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
    return tuple(mismatches)


def configure_deterministic_backend() -> None:
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = CUBLAS_WORKSPACE_CONFIG_VALUE
    torch.use_deterministic_algorithms(True, warn_only=False)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    torch.backends.cudnn.conv.fp32_precision = "ieee"


def collect_environment_mismatches() -> tuple[EnvironmentMismatch, ...]:
    return check_python_version() + check_installed_package_versions() + check_gpu_requirements()


def deterministic_execution_available() -> bool:
    return len(collect_environment_mismatches()) == 0
