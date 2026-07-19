"""In-session operational metrics — real counters, no synthetic KPIs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class LiveOpsMetrics:
    started_at: float = field(default_factory=time.time)
    wallet_screens: int = 0
    investigations: int = 0
    str_received: int = 0
    kyt_alerts: int = 0
    graph_nodes_total: int = 0
    graph_edges_total: int = 0
    decision_ms_total: int = 0
    decision_samples: int = 0
    last_screen_risk: float | None = None
    last_screen_address: str | None = None

    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_screen(self, *, risk_score: float, address: str) -> None:
        with self._lock:
            self.wallet_screens += 1
            self.last_screen_risk = risk_score
            self.last_screen_address = address

    def record_investigation(
        self,
        *,
        duration_ms: int,
        graph_nodes: int = 0,
        graph_edges: int = 0,
    ) -> None:
        with self._lock:
            self.investigations += 1
            self.decision_ms_total += duration_ms
            self.decision_samples += 1
            self.graph_nodes_total += graph_nodes
            self.graph_edges_total += graph_edges

    def record_str(self) -> None:
        with self._lock:
            self.str_received += 1

    def record_kyt_alert(self) -> None:
        with self._lock:
            self.kyt_alerts += 1

    def snapshot(self) -> dict[str, int | float | None]:
        with self._lock:
            uptime = max(1, int(time.time() - self.started_at))
            tps = round(self.wallet_screens / uptime, 2) if self.wallet_screens else 0.0
            return {
                "wallet_screens": self.wallet_screens,
                "investigations": self.investigations,
                "str_received": self.str_received,
                "kyt_alerts": self.kyt_alerts,
                "graph_nodes_total": self.graph_nodes_total,
                "graph_edges_total": self.graph_edges_total,
                "avg_decision_ms": (
                    int(self.decision_ms_total / self.decision_samples)
                    if self.decision_samples
                    else None
                ),
                "decision_samples": self.decision_samples,
                "screening_tps": tps,
                "uptime_sec": uptime,
                "last_screen_risk": self.last_screen_risk,
            }


_metrics: LiveOpsMetrics | None = None


def get_live_ops_metrics() -> LiveOpsMetrics:
    global _metrics
    if _metrics is None:
        _metrics = LiveOpsMetrics()
    return _metrics
