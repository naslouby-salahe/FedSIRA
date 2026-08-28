import time

from fedsira.runtime.timing import ElapsedTimer


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


from fedsira.runtime.timing import peak_host_resident_set_bytes


def test_peak_host_resident_set_bytes_is_positive() -> None:
    assert peak_host_resident_set_bytes() > 0
