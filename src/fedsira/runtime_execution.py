from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import os
import random
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated, ClassVar, Protocol, TypeVar, cast

import numpy
import torch
from pydantic import Field

from fedsira.domain.enums import SeedNamespace
from fedsira.domain.types import (
    UINT32_MODULUS,
    AlgorithmName,
    ByteCount,
    CheckpointIdentity,
    DatasetManifestDigest,
    DerivedSeed,
    DeterministicInteger,
    DomainId,
    EnvironmentText,
    EpochIndex,
    FramingField,
    FrozenDomainModel,
    LogRecordText,
    MasterSeed,
    NamespaceSeed,
    PeakMemoryBytes,
    RarArchivesPresent,
    RoundIndex,
    RuntimeComponentName,
    SampleId,
    SeedDerivationLabel,
    TextValue,
    TrainingConditionId,
    WallClockSeconds,
)

NAMESPACE_SEED_PREFIX = "FedSIRA|seed_namespace|"
LOCAL_TRAINING_JOB_SEPARATOR: SeedDerivationLabel = "LOCAL_TRAINING_JOB"
LOCAL_TRAINING_BATCH_ORDER_SEPARATOR: SeedDerivationLabel = "LOCAL_TRAINING_BATCH_ORDER"

FramedBytes = Annotated[bytes, Field()]
DigestBytes = Annotated[bytes, Field(min_length=32, max_length=32)]
OrderItem = TypeVar("OrderItem")


class _TorchSeedFunction(Protocol):
    def __call__(self, seed: DeterministicInteger) -> None: ...


_TORCH_MANUAL_SEED = cast(_TorchSeedFunction, torch.manual_seed)
_TORCH_CUDA_MANUAL_SEED_ALL = cast(_TorchSeedFunction, torch.cuda.manual_seed_all)


def framed_bytes(*fields: FramingField) -> FramedBytes:
    encoded = bytearray()
    for field in fields:
        payload = str(field).encode("utf-8")
        encoded += len(payload).to_bytes(4, byteorder="big", signed=False)
        encoded += payload
    return bytes(encoded)


def namespace_seed(master_seed: MasterSeed, namespace: SeedNamespace) -> NamespaceSeed:
    message = f"{NAMESPACE_SEED_PREFIX}{master_seed}|{namespace}"
    digest = hashlib.sha256(message.encode("utf-8")).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % UINT32_MODULUS


def derive_uint32(
    separator: SeedDerivationLabel,
    parent: DeterministicInteger,
    *values: FramingField,
) -> DerivedSeed:
    digest = hashlib.sha256(framed_bytes(separator, parent, *values)).digest()
    return int.from_bytes(digest[0:8], byteorder="big", signed=False) % UINT32_MODULUS


def local_training_seed(
    local_training_namespace_seed: NamespaceSeed,
    dataset_manifest_hash: DatasetManifestDigest,
    start_checkpoint_identity: CheckpointIdentity,
    training_algorithm_token: AlgorithmName,
    domain_hash_token: DomainId,
    scientific_training_condition_token: TrainingConditionId,
    round_index_or_minus_one: RoundIndex,
) -> DerivedSeed:
    return derive_uint32(
        LOCAL_TRAINING_JOB_SEPARATOR,
        local_training_namespace_seed,
        dataset_manifest_hash,
        start_checkpoint_identity,
        training_algorithm_token,
        domain_hash_token,
        scientific_training_condition_token,
        round_index_or_minus_one,
    )


def deterministic_order(
    items: tuple[OrderItem, ...],
    domain_separator: SeedDerivationLabel,
    order_namespace_seed: NamespaceSeed,
) -> tuple[OrderItem, ...]:
    def sort_key(item: OrderItem) -> tuple[DigestBytes, TextValue]:
        item_text: TextValue = str(item)
        digest: DigestBytes = hashlib.sha256(
            framed_bytes(domain_separator, order_namespace_seed, item_text)
        ).digest()
        return digest, item_text

    return tuple(sorted(items, key=sort_key))


def minibatch_order(
    training_seed: DerivedSeed,
    epoch: EpochIndex,
    sample_ids: tuple[SampleId, ...],
) -> tuple[SampleId, ...]:
    def sort_key(sample_id: SampleId) -> tuple[DigestBytes, SampleId]:
        digest: DigestBytes = hashlib.sha256(
            framed_bytes(LOCAL_TRAINING_BATCH_ORDER_SEPARATOR, training_seed, epoch, sample_id)
        ).digest()
        return digest, sample_id

    return tuple(sorted(sample_ids, key=sort_key))


def seed_job_local_rng_streams(seed: DerivedSeed) -> None:
    random.seed(seed)
    numpy.random.seed(seed)
    _TORCH_MANUAL_SEED(seed)
    _TORCH_CUDA_MANUAL_SEED_ALL(seed)


BYTES_PER_GIGABYTE: ByteCount = 1_073_741_824
REFERENCE_OS_NAME: EnvironmentText = "Ubuntu"
REFERENCE_OS_VERSION_ID: EnvironmentText = "24.04"
REFERENCE_PYTHON_VERSION: EnvironmentText = "3.11.9"
REFERENCE_CUDA_RUNTIME_VERSION: EnvironmentText = "12.8"
REFERENCE_GPU_NAME: EnvironmentText = "NVIDIA GeForce RTX 5060 Ti"
REFERENCE_GPU_VRAM_GIGABYTES: ByteCount = 16
REFERENCE_MINIMUM_CPU_RAM_GIGABYTES: ByteCount = 32
REFERENCE_REQUIRED_GPU_COUNT: ByteCount = 1
REFERENCE_UNRAR_VERSION: EnvironmentText = "1:7.0.7-1build1"
REFERENCE_CUBLAS_WORKSPACE_CONFIG: EnvironmentText = ":4096:8"


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


def check_python_version() -> tuple[EnvironmentMismatch, ...]:
    actual: EnvironmentText = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    expected = REFERENCE_PYTHON_VERSION
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
    if not torch.cuda.is_available():
        return (
            EnvironmentMismatch(
                component="gpu_availability",
                expected="available",
                actual="unavailable",
            ),
        )
    device_count = torch.cuda.device_count()
    if device_count != REFERENCE_REQUIRED_GPU_COUNT:
        mismatches.append(
            EnvironmentMismatch(
                component="gpu_count",
                expected=str(REFERENCE_REQUIRED_GPU_COUNT),
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


def check_hardware_resources() -> tuple[EnvironmentMismatch, ...]:
    mismatches: list[EnvironmentMismatch] = []
    total_ram_gigabytes = (
        os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    ) / BYTES_PER_GIGABYTE
    if total_ram_gigabytes < REFERENCE_MINIMUM_CPU_RAM_GIGABYTES:
        mismatches.append(
            EnvironmentMismatch(
                component="cpu_ram_gigabytes",
                expected=f">={REFERENCE_MINIMUM_CPU_RAM_GIGABYTES}",
                actual=f"{total_ram_gigabytes:.1f}",
            )
        )
    return tuple(mismatches)


def check_unrar_availability(
    rar_archives_present: RarArchivesPresent,
) -> tuple[EnvironmentMismatch, ...]:
    if not rar_archives_present:
        return ()
    expected = REFERENCE_UNRAR_VERSION
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
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = REFERENCE_CUBLAS_WORKSPACE_CONFIG
    torch.use_deterministic_algorithms(True, warn_only=False)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    cudnn_conv = cast(_Fp32PrecisionController, torch.backends.cudnn.conv)
    cudnn_conv.fp32_precision = "ieee"


def collect_environment_mismatches(
    rar_archives_present: RarArchivesPresent,
) -> tuple[EnvironmentMismatch, ...]:
    return (
        check_operating_system()
        + check_python_version()
        + check_installed_package_versions()
        + check_gpu_requirements()
        + check_hardware_resources()
        + check_unrar_availability(rar_archives_present)
    )


LOGGER_NAME_PREFIX = "fedsira"


class StructuredJsonFormatter(logging.Formatter):
    RESERVED_ATTRIBUTES: ClassVar[frozenset[str]] = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__
    )

    def format(self, record: logging.LogRecord) -> LogRecordText:
        payload = record.__dict__.copy()
        for reserved_key in self.RESERVED_ATTRIBUTES:
            payload.pop(reserved_key, None)
        payload["timestamp"] = self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z")
        payload["level"] = record.levelname
        payload["component"] = record.name
        payload["message"] = record.getMessage()
        return json.dumps(payload, sort_keys=True, default=str)


def get_structured_logger(component: RuntimeComponentName) -> logging.Logger:
    logger = logging.getLogger(f"{LOGGER_NAME_PREFIX}.{component}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.WARNING)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def configure_structured_file_logging(logger: logging.Logger, log_path: Path) -> None:
    resolved_path = log_path.resolve()
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == resolved_path:
            return
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(resolved_path, encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(StructuredJsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


BYTES_PER_KIBIBYTE = 1024


class ElapsedTimer:
    def __init__(self) -> None:
        self._start = time.monotonic()

    def elapsed_seconds(self) -> WallClockSeconds:
        return time.monotonic() - self._start


def reset_peak_gpu_memory_counter() -> None:
    torch.cuda.reset_peak_memory_stats()


def peak_gpu_memory_bytes() -> PeakMemoryBytes:
    return torch.cuda.max_memory_allocated()


def peak_host_resident_set_bytes() -> PeakMemoryBytes:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * BYTES_PER_KIBIBYTE
