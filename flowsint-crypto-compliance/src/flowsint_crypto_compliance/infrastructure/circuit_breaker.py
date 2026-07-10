"""
Circuit breaker for external OSINT/blockchain collectors.

When TronGrid / OpenSanctions / Ahmia fail repeatedly, mark source degraded
and skip calls until recovery window — investigation continues with other sources.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _BreakerState:
    failures: int = 0
    last_failure: float = 0.0
    open_until: float = 0.0
    degraded: bool = False


class CollectorCircuitBreaker:
    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int | None = None,
        recovery_timeout_sec: float | None = None,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold or int(
            os.getenv("FINSKALP_CB_FAILURE_THRESHOLD", "5")
        )
        self.recovery_timeout_sec = recovery_timeout_sec or float(
            os.getenv("FINSKALP_CB_RECOVERY_SEC", "60")
        )
        self._state = _BreakerState()
        self._lock = threading.RLock()

    def allow_request(self) -> bool:
        now = time.monotonic()
        with self._lock:
            if now < self._state.open_until:
                return False
            if self._state.open_until and now >= self._state.open_until:
                self._state.open_until = 0.0
                self._state.failures = 0
                self._state.degraded = False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._state.failures = 0
            self._state.degraded = False
            self._state.open_until = 0.0

    def record_failure(self) -> None:
        now = time.monotonic()
        with self._lock:
            self._state.failures += 1
            self._state.last_failure = now
            if self._state.failures >= self.failure_threshold:
                self._state.open_until = now + self.recovery_timeout_sec
                self._state.degraded = True

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "degraded": self._state.degraded,
                "failures": self._state.failures,
                "open_until": self._state.open_until,
                "available": self.allow_request(),
            }


_breakers: dict[str, CollectorCircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_breaker(source: str) -> CollectorCircuitBreaker:
    key = source.lower()
    with _registry_lock:
        if key not in _breakers:
            _breakers[key] = CollectorCircuitBreaker(key)
        return _breakers[key]


def all_breaker_statuses() -> list[dict[str, Any]]:
    with _registry_lock:
        return [b.status() for b in _breakers.values()]
