"""A small in-memory sliding-window rate limiter.

Good enough for one server process. With several server instances each one
keeps its own counters; a shared store such as Redis would be the next step.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:

    def __init__(self, max_calls: int, window_seconds: float, clock=time.monotonic):

        self.max_calls = max_calls
        self.window = window_seconds
        self.clock = clock
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def _trim(self, key):

        events = self._events[key]
        cutoff = self.clock() - self.window

        while events and events[0] <= cutoff:
            events.popleft()

        return events

    def is_limited(self, key) -> bool:
        with self._lock:
            return len(self._trim(key)) >= self.max_calls

    def record(self, key):
        """Count one event (for example one failed login)."""
        with self._lock:
            self._trim(key).append(self.clock())

    def try_acquire(self, key) -> bool:
        """Count one event unless the limit is already reached.
        Returns False when the caller must be refused."""

        with self._lock:
            events = self._trim(key)

            if len(events) >= self.max_calls:
                return False

            events.append(self.clock())
            return True

    def reset(self, key):
        with self._lock:
            self._events.pop(key, None)

    def retry_after(self, key) -> int:
        """Seconds until the oldest counted event expires."""

        with self._lock:
            events = self._trim(key)

            if not events:
                return 0

            return max(1, int(events[0] + self.window - self.clock()) + 1)
