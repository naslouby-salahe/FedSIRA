from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from fedsira.domain.enums import AdmissionState
from fedsira.domain.types import (
    ByteCount,
    ConditionName,
    ExperimentName,
    FrozenDomainModel,
    MasterSeed,
    MethodName,
    MetricValue,
    ModelTransmissionCount,
    PeakMemoryBytes,
    RepetitionIndex,
    ScientificCellSemanticKey,
    WallClockSeconds,
)
from fedsira.runtime import (
    CudaIntervalTimer,
    ElapsedTimer,
    peak_gpu_memory_bytes,
    peak_host_resident_set_bytes,
    reset_peak_gpu_memory_counter,
)


class TimingRepetitionObservation(FrozenDomainModel):
    experiment: ExperimentName
    method: MethodName
    condition: ConditionName
    master_seed: MasterSeed
    repetition: RepetitionIndex
    semantic_key: ScientificCellSemanticKey
    wall_clock_seconds: WallClockSeconds
    gpu_seconds: WallClockSeconds
    peak_gpu_memory_bytes: PeakMemoryBytes
    peak_host_rss_bytes: PeakMemoryBytes
    communication_bytes: ByteCount
    model_transmissions: ModelTransmissionCount


@dataclass(frozen=True)
class TimingWorkerObservation:
    value: tuple[AdmissionState, ByteCount, ByteCount]
    wall_clock_seconds: MetricValue
    gpu_seconds: MetricValue
    peak_gpu_memory_bytes: PeakMemoryBytes
    peak_host_rss_bytes: PeakMemoryBytes


TimingWorkerResult: TypeAlias = tuple[AdmissionState, ByteCount, ByteCount]


class SingleProcessTimingWorker:
    def measure(
        self,
        action: Callable[[], TimingWorkerResult],
    ) -> TimingWorkerObservation:
        reset_peak_gpu_memory_counter()
        timer = ElapsedTimer()
        gpu_timer = CudaIntervalTimer()
        gpu_timer.start()
        state, communication_bytes_total, transmissions = action()
        gpu_seconds = gpu_timer.elapsed_seconds()
        return TimingWorkerObservation(
            value=(state, communication_bytes_total, transmissions),
            wall_clock_seconds=timer.elapsed_seconds(),
            gpu_seconds=gpu_seconds,
            peak_gpu_memory_bytes=int(peak_gpu_memory_bytes()),
            peak_host_rss_bytes=int(peak_host_resident_set_bytes()),
        )
