"""RFC-0014 Ch.12 — per-collector monitoring."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CollectorMetrics:
    connector_id: str
    latency_ms: float = 0.0
    request_count: int = 0
    error_count: int = 0
    records_processed: int = 0
    success_count: int = 0
    connected: bool = False
    last_updated: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        if self.request_count == 0:
            return 1.0
        return self.success_count / self.request_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "latency_ms": round(self.latency_ms, 2),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "records_processed": self.records_processed,
            "success_rate": round(self.success_rate, 4),
            "connection_status": "connected" if self.connected else "disconnected",
            "last_updated": self.last_updated,
        }


class ICFMonitoring:
    """Track per-collector metrics."""

    def __init__(self) -> None:
        self._metrics: dict[str, CollectorMetrics] = {}

    def _get(self, connector_id: str) -> CollectorMetrics:
        if connector_id not in self._metrics:
            self._metrics[connector_id] = CollectorMetrics(connector_id=connector_id)
        return self._metrics[connector_id]

    def record_request(
        self,
        connector_id: str,
        *,
        latency_ms: float,
        success: bool,
        records: int = 0,
        connected: bool = True,
    ) -> None:
        m = self._get(connector_id)
        m.request_count += 1
        m.latency_ms = latency_ms
        m.records_processed += records
        m.connected = connected
        m.last_updated = time.time()
        if success:
            m.success_count += 1
        else:
            m.error_count += 1

    def get_metrics(self, connector_id: str | None = None) -> dict[str, Any]:
        if connector_id:
            return self._get(connector_id).to_dict()
        return {
            "collectors": [m.to_dict() for m in self._metrics.values()],
            "total_collectors": len(self._metrics),
        }


_monitoring: ICFMonitoring | None = None


def get_icf_monitoring() -> ICFMonitoring:
    global _monitoring
    if _monitoring is None:
        _monitoring = ICFMonitoring()
    return _monitoring
