"""RFC-0016 Ch.14 — monitoring metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RDEMetrics:
    """In-memory RDE monitoring metrics."""

    assessment_count: int = 0
    rule_events_fired: int = 0
    total_latency_ms: float = 0.0
    error_count: int = 0
    by_risk_level: dict[str, int] = field(default_factory=dict)
    by_entity: dict[str, int] = field(default_factory=dict)

    def record_assessment(
        self,
        *,
        entity_key: str,
        risk_level: str,
        latency_ms: float,
        rule_count: int = 0,
        ok: bool = True,
    ) -> None:
        self.assessment_count += 1
        self.total_latency_ms += latency_ms
        self.by_risk_level[risk_level] = self.by_risk_level.get(risk_level, 0) + 1
        self.by_entity[entity_key] = self.by_entity.get(entity_key, 0) + 1
        self.rule_events_fired += rule_count
        if not ok:
            self.error_count += 1

    def get_metrics(self) -> dict[str, Any]:
        avg_latency = self.total_latency_ms / self.assessment_count if self.assessment_count else 0.0
        return {
            "assessment_count": self.assessment_count,
            "rule_events_fired": self.rule_events_fired,
            "error_count": self.error_count,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": round(
                (self.assessment_count - self.error_count) / self.assessment_count, 3
            )
            if self.assessment_count
            else 1.0,
            "by_risk_level": dict(self.by_risk_level),
            "unique_entities": len(self.by_entity),
        }


_metrics: RDEMetrics | None = None


def get_rde_metrics() -> RDEMetrics:
    global _metrics
    if _metrics is None:
        _metrics = RDEMetrics()
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
