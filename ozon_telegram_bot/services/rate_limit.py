from __future__ import annotations

import threading
import time


class SimpleRateLimiter:
    def __init__(self, rate_per_second: float) -> None:
        self.interval = 1.0 / rate_per_second
        self.lock = threading.Lock()
        self.next_allowed_at = 0.0

    def acquire(self) -> None:
        with self.lock:
            now = time.monotonic()
            wait_time = self.next_allowed_at - now
            if wait_time > 0:
                time.sleep(wait_time)
                now = time.monotonic()
            self.next_allowed_at = now + self.interval
