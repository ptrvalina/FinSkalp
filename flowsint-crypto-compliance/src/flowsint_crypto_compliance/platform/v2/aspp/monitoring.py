"""RFC-0019 Ch.16 — API + plugin monitoring metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.plugin_manager import get_plugin_manager
from flowsint_crypto_compliance.platform.v2.aspp.webhooks import get_webhook_registry


@dataclass
class ASPPMetrics:
    api_request_count: int = 0
    api_error_count: int = 0
    total_latency_ms: float = 0.0
    plugin_register_count: int = 0
    webhook_subscribe_count: int = 0
    webhook_delivery_count: int = 0
    by_endpoint: dict[str, int] = field(default_factory=dict)

    def record_request(self, *, endpoint: str, latency_ms: float, ok: bool = True) -> None:
        self.api_request_count += 1
        self.total_latency_ms += latency_ms
        self.by_endpoint[endpoint] = self.by_endpoint.get(endpoint, 0) + 1
        if not ok:
            self.api_error_count += 1

    def record_plugin_register(self) -> None:
        self.plugin_register_count += 1

    def record_webhook_subscribe(self) -> None:
        self.webhook_subscribe_count += 1

    def record_webhook_delivery(self, count: int = 1) -> None:
        self.webhook_delivery_count += count

    def get_metrics(self) -> dict[str, Any]:
        mgr = get_plugin_manager()
        webhook_reg = get_webhook_registry()
        avg_latency = self.total_latency_ms / self.api_request_count if self.api_request_count else 0.0
        return {
            "api_request_count": self.api_request_count,
            "api_error_count": self.api_error_count,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": round(
                (self.api_request_count - self.api_error_count) / self.api_request_count, 3
            )
            if self.api_request_count
            else 1.0,
            "plugin_count": len(mgr.list()),
            "plugin_health": mgr.health_summary(),
            "plugin_register_count": self.plugin_register_count,
            "webhook_subscription_count": len(webhook_reg.list_subscriptions()),
            "webhook_subscribe_count": self.webhook_subscribe_count,
            "webhook_delivery_count": self.webhook_delivery_count,
            "by_endpoint": dict(self.by_endpoint),
        }


_metrics: ASPPMetrics | None = None


def get_aspp_metrics() -> ASPPMetrics:
    global _metrics
    if _metrics is None:
        _metrics = ASPPMetrics()
    return _metrics


def reset_aspp_metrics() -> None:
    global _metrics
    _metrics = None


class LatencyTimer:
    def __init__(self) -> None:
        self._start = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self) -> LatencyTimer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0
