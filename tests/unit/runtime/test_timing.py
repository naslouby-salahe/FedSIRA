import time

import pytest

from fedsira.domain.enums import RuntimeComponentName
from fedsira.runtime import (
    ElapsedTimer,
    OperationTimeoutError,
    peak_host_resident_set_bytes,
    run_bounded,
)


def test_elapsed_timer_is_non_negative() -> None:
    timer = ElapsedTimer()
    assert timer.elapsed_seconds() >= 0.0


def test_elapsed_timer_advances() -> None:
    timer = ElapsedTimer()
    time.sleep(0.02)
    assert timer.elapsed_seconds() >= 0.01


def test_elapsed_timer_fresh_instance_restarts() -> None:
    timer = ElapsedTimer()
    time.sleep(0.02)
    second = ElapsedTimer()
    assert second.elapsed_seconds() < timer.elapsed_seconds()


def test_peak_host_resident_set_bytes_is_positive() -> None:
    assert peak_host_resident_set_bytes() > 0


def test_run_bounded_returns_promptly_when_a_main_thread_operation_times_out() -> None:
    started_at = time.monotonic()
    with pytest.raises(OperationTimeoutError):
        run_bounded(RuntimeComponentName.PREPROCESSING, 1, lambda: time.sleep(2))
    assert time.monotonic() - started_at < 1.5
