"""RFC-0017 Ch.16 — ECCF monitoring metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ECCFMetrics:
    """In-memory ECCF monitoring metrics."""

    registered_count: int = 0
    deduplicated_count: int = 0
    integrity_failures: int = 0
    archived_count: int = 0
    report_usage_count: int = 0
    kg_linked_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    by_category: dict[str, int] = field(default_factory=dict)

    def record_registration(
        self,
        *,
        category: str,
        latency_ms: float,
        deduplicated: bool = False,
        integrity_ok: bool = True,
        kg_linked: bool = False,
        ok: bool = True,
    ) -> None:
        self.registered_count += 1
        self.total_latency_ms += latency_ms
        self.by_category[category] = self.by_category.get(category, 0) + 1
        if deduplicated:
            self.deduplicated_count += 1
        if not integrity_ok:
            self.integrity_failures += 1
        if kg_linked:
            self.kg_linked_count += 1
        if not ok:
            self.error_count += 1

    def record_archive(self) -> None:
        self.archived_count += 1

    def record_report_usage(self) -> None:
        self.report_usage_count += 1

    def get_metrics(self) -> dict[str, Any]:
        avg_latency = self.total_latency_ms / self.registered_count if self.registered_count else 0.0
        return {
            "registered_count": self.registered_count,
            "deduplicated_count": self.deduplicated_count,
            "integrity_failures": self.integrity_failures,
            "archived_count": self.archived_count,
            "report_usage_count": self.report_usage_count,
            "kg_linked_count": self.kg_linked_count,
            "error_count": self.error_count,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": round(
                (self.registered_count - self.error_count) / self.registered_count, 3
            )
            if self.registered_count
            else 1.0,
            "by_category": dict(self.by_category),
        }


_metrics: ECCFMetrics | None = None


def get_eccf_metrics() -> ECCFMetrics:
    global _metrics
    if _metrics is None:
        _metrics = ECCFMetrics()
    return _metrics


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
