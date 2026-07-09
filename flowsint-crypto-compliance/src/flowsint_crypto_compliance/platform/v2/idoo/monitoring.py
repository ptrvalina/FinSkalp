"""RFC-0021 Ch.9 — service health checks catalog."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.types import ServiceHealth


@dataclass
class IDOOMetrics:
    health_probe_count: int = 0
    health_probe_failures: int = 0
    last_probe_at: str = ""
    by_service: dict[str, str] = field(default_factory=dict)

    def record_probe(self, *, service: str, status: ServiceHealth) -> None:
        self.health_probe_count += 1
        self.by_service[service] = status.value
        if status in (ServiceHealth.UNHEALTHY, ServiceHealth.DEGRADED):
            self.health_probe_failures += 1
        self.last_probe_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def get_metrics(self) -> dict[str, Any]:
        return {
            "health_probe_count": self.health_probe_count,
            "health_probe_failures": self.health_probe_failures,
            "last_probe_at": self.last_probe_at,
            "by_service": dict(self.by_service),
        }


_metrics: IDOOMetrics | None = None


def get_idoo_metrics() -> IDOOMetrics:
    global _metrics
    if _metrics is None:
        _metrics = IDOOMetrics()
    return _metrics


def reset_idoo_metrics() -> None:
    global _metrics
    _metrics = None


def monitoring_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 9,
        "health_checks": [
            {
                "service": "api",
                "endpoint": "/health",
                "method": "GET",
                "expected_status": 200,
                "interval_seconds": 10,
            },
            {
                "service": "celery",
                "endpoint": "celery inspect ping",
                "method": "CLI",
                "expected_status": "pong",
                "interval_seconds": 30,
            },
            {
                "service": "postgres",
                "endpoint": "pg_isready -U flowsint",
                "method": "CLI",
                "expected_status": "accepting connections",
                "interval_seconds": 10,
            },
            {
                "service": "redis",
                "endpoint": "redis-cli ping",
                "method": "CLI",
                "expected_status": "PONG",
                "interval_seconds": 10,
            },
            {
                "service": "neo4j",
                "endpoint": 'cypher-shell "RETURN 1"',
                "method": "CLI",
                "expected_status": 1,
                "interval_seconds": 5,
            },
        ],
        "response_headers": {
            "latency": "X-Finskalp-Latency-Ms",
            "correlation": "X-Correlation-ID",
        },
        "principle_ru": "Каталог health-check для api, celery, postgres, redis, neo4j",
    }
