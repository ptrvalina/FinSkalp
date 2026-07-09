"""RFC-0015 Ch.17 — CRIF metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConnectorMetrics:
    connector_id: str
    latency_ms: float = 0.0
    request_count: int = 0
    error_count: int = 0
    records_processed: int = 0
    success_count: int = 0
    checks_run: int = 0
    sanctions_screened: int = 0
    rules_fired: int = 0
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
            "checks_run": self.checks_run,
            "sanctions_screened": self.sanctions_screened,
            "rules_fired": self.rules_fired,
            "success_rate": round(self.success_rate, 4),
            "connection_status": "connected" if self.connected else "disconnected",
            "last_updated": self.last_updated,
        }


class CRIFMetrics:
    """Track per-connector CRIF metrics."""

    def __init__(self) -> None:
        self._metrics: dict[str, ConnectorMetrics] = {}

    def _get(self, connector_id: str) -> ConnectorMetrics:
        if connector_id not in self._metrics:
            self._metrics[connector_id] = ConnectorMetrics(connector_id=connector_id)
        return self._metrics[connector_id]

    def record_pipeline(
        self,
        connector_id: str,
        *,
        latency_ms: float,
        success: bool,
        records: int = 0,
        checks: int = 0,
        connected: bool = True,
    ) -> None:
        m = self._get(connector_id)
        m.request_count += 1
        m.latency_ms = latency_ms
        m.records_processed += records
        m.checks_run += checks
        m.connected = connected
        m.last_updated = time.time()
        if success:
            m.success_count += 1
        else:
            m.error_count += 1

    def record_sanctions_screen(self, connector_id: str = "sanctions") -> None:
        m = self._get(connector_id)
        m.sanctions_screened += 1
        m.last_updated = time.time()

    def record_rules_fired(self, connector_id: str, count: int) -> None:
        m = self._get(connector_id)
        m.rules_fired += count
        m.last_updated = time.time()

    def get_metrics(self, connector_id: str | None = None) -> dict[str, Any]:
        if connector_id:
            return self._get(connector_id).to_dict()
        return {
            "connectors": [m.to_dict() for m in self._metrics.values()],
            "total_connectors": len(self._metrics),
        }


_metrics: CRIFMetrics | None = None


def get_crif_metrics() -> CRIFMetrics:
    global _metrics
    if _metrics is None:
        _metrics = CRIFMetrics()
    return _metrics
