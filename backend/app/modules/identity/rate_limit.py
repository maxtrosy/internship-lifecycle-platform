"""Small per-process guard against repeated credential and recovery requests.

Production deployments with multiple API workers should add a shared Redis/WAF limiter.
The current Compose deployment runs one API worker, so a bounded in-memory window is useful
without adding an infrastructure dependency.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.errors import TooManyRequests


class FailureRateLimiter:
    def __init__(self, window_seconds: int = 900, per_identity: int = 10, per_ip: int = 60):
        self.window_seconds = window_seconds
        self.per_identity = per_identity
        self.per_ip = per_ip
        self._lock = threading.Lock()
        self._failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, purpose: str, identity: str, ip_address: str) -> None:
        now = time.monotonic()
        with self._lock:
            identity_key = (purpose, f"identity:{identity}")
            ip_key = (purpose, f"ip:{ip_address}")
            self._prune(identity_key, now)
            self._prune(ip_key, now)
            if (len(self._failures[identity_key]) >= self.per_identity
                    or len(self._failures[ip_key]) >= self.per_ip):
                raise TooManyRequests()

    def failed(self, purpose: str, identity: str, ip_address: str) -> None:
        self.record(purpose, identity, ip_address)

    def record(self, purpose: str, identity: str, ip_address: str) -> None:
        """Count a request even when the endpoint deliberately returns a generic result."""
        now = time.monotonic()
        with self._lock:
            self._failures[(purpose, f"identity:{identity}")].append(now)
            self._failures[(purpose, f"ip:{ip_address}")].append(now)

    def succeeded(self, purpose: str, identity: str) -> None:
        with self._lock:
            self._failures.pop((purpose, f"identity:{identity}"), None)

    def _prune(self, key: tuple[str, str], now: float) -> None:
        bucket = self._failures[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if not bucket:
            self._failures.pop(key, None)


login_rate_limiter = FailureRateLimiter()
reset_rate_limiter = FailureRateLimiter(per_identity=5, per_ip=20)
