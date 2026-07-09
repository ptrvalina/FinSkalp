"""RFC-0021 Ch.8 — unified observability manifest (metrics/logs/traces)."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.types import ObservabilitySignal


def observability_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 8,
        "pillars": [s.value for s in ObservabilitySignal],
        "metrics": {
            "backend": "Prometheus",
            "scrape_interval": "15s",
            "exporters": ["fastapi", "celery", "postgres", "redis"],
            "dashboards": "Grafana",
            "technical_debt": "TD-IDOO-3",
        },
        "logs": {
            "backend": "Loki",
            "format": "structured_json",
            "retention_days": 30,
            "technical_debt": "TD-IDOO-4",
        },
        "traces": {
            "backend": "Tempo",
            "protocol": "OpenTelemetry",
            "propagation": "X-Correlation-ID + W3C traceparent",
            "endpoint": "http://otel-collector:4317",
        },
        "compose_hardening": {
            "file": "docker-compose.hardening.yml",
            "services": ["prometheus", "grafana", "loki", "tempo", "pghero"],
        },
        "principle_ru": "Три столпа наблюдаемости — метрики, логи, трейсы",
    }
