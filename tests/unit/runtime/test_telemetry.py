from fedsira.runtime.telemetry import peak_host_resident_set_bytes


def test_peak_host_resident_set_bytes_is_positive() -> None:
    assert peak_host_resident_set_bytes() > 0
