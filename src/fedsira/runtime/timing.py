from __future__ import annotations

import resource
import time

import torch

from fedsira.domain.types import PeakMemoryBytes, WallClockSeconds

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
