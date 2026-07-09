"""RFC-0018 Ch.16 — EIA monitoring metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EIAMetrics:
    """In-memory EIA monitoring metrics."""

    task_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    by_task_type: dict[str, int] = field(default_factory=dict)

    def record_task(
        self,
        *,
        task_type: str,
        latency_ms: float,
        ok: bool = True,
        cache_hit: bool = False,
    ) -> None:
        self.task_count += 1
        self.total_latency_ms += latency_ms
        self.by_task_type[task_type] = self.by_task_type.get(task_type, 0) + 1
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        if not ok:
            self.error_count += 1

    def record_cache_warm(self, count: int) -> None:
        self.cache_hits += count

    def get_metrics(self) -> dict[str, Any]:
        avg_latency = self.total_latency_ms / self.task_count if self.task_count else 0.0
        return {
            "task_count": self.task_count,
            "error_count": self.error_count,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": round(
                (self.task_count - self.error_count) / self.task_count, 3
            )
            if self.task_count
            else 1.0,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "by_task_type": dict(self.by_task_type),
        }


_metrics: EIAMetrics | None = None


def get_eia_metrics() -> EIAMetrics:
    global _metrics
    if _metrics is None:
        _metrics = EIAMetrics()
    return _metrics


def reset_eia_metrics() -> None:
    global _metrics
    _metrics = EIAMetrics()


class LatencyTimer:
    """Context manager for latency measurement."""

    def __init__(self) -> None:
        self._start = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self) -> "LatencyTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
