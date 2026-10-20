from __future__ import annotations

import time
from collections.abc import Callable


class PerDomainRateLimiter:
    def __init__(
        self,
        min_interval_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = min_interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._last_call: dict[str, float] = {}

    def wait(self, domain: str) -> None:
        now = self._clock()
        last = self._last_call.get(domain)
        if last is not None:
            elapsed = now - last
            if elapsed < self._min_interval:
                self._sleep(self._min_interval - elapsed)
        self._last_call[domain] = self._clock()
