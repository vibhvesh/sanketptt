"""Polite gaps between calls to public APIs, and a small per-user search cap."""

from __future__ import annotations

import threading
import time


class RateGate:
    """Serialise callers so a public API is hit at most once per interval."""

    def __init__(self, min_interval: float) -> None:
        self.min_interval = max(0.0, min_interval)
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._next - now
            if delay > 0:
                time.sleep(delay)
                now = time.monotonic()
            self._next = now + self.min_interval


class WindowLimiter:
    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            recent = [stamp for stamp in self._hits.get(key, []) if now - stamp < self.window]
            if len(recent) >= self.max_calls:
                self._hits[key] = recent
                return False
            recent.append(now)
            self._hits[key] = recent
            return True

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()
