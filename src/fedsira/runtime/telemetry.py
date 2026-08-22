import resource

import torch

from fedsira.domain.records import NonNegativeInt

BYTES_PER_KIBIBYTE = 1024


def reset_peak_gpu_memory_counter() -> None:
    torch.cuda.reset_peak_memory_stats()


def peak_gpu_memory_bytes() -> NonNegativeInt:
    return torch.cuda.max_memory_allocated()


def peak_host_resident_set_bytes() -> NonNegativeInt:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * BYTES_PER_KIBIBYTE
