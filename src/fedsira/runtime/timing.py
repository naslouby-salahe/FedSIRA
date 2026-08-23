from __future__ import annotations

import time

from fedsira.domain.records import NonNegativeFloat


class ElapsedTimer:
    def __init__(self) -> None:
        self._start = time.monotonic()

    def elapsed_seconds(self) -> NonNegativeFloat:
        return time.monotonic() - self._start
