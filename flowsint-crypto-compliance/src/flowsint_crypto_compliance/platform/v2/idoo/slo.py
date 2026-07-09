"""RFC-0021 Ch.18 — SLA / SLO targets."""

from __future__ import annotations

from typing import Any


def slo_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 18,
        "slos": [
            {
                "name": "api_availability",
                "target": 99.9,
                "unit": "percent",
                "window": "30d",
                "measurement": "/health uptime",
            },
            {
                "name": "api_latency_p95",
                "target": 500,
                "unit": "milliseconds",
                "window": "7d",
                "measurement": "X-Finskalp-Latency-Ms header",
            },
            {
                "name": "celery_queue_throughput",
                "target": 100,
                "unit": "tasks_per_minute",
                "window": "1h",
                "measurement": "completed tasks / minute",
            },
            {
                "name": "celery_task_latency_p99",
                "target": 300,
                "unit": "seconds",
                "window": "7d",
                "measurement": "task duration",
            },
            {
                "name": "postgres_query_p95",
                "target": 100,
                "unit": "milliseconds",
                "window": "7d",
                "measurement": "slow query log",
            },
            {
                "name": "backup_success_rate",
                "target": 100,
                "unit": "percent",
                "window": "30d",
                "measurement": "backup job completion",
            },
        ],
        "error_budget": {
            "api_availability": "43.2 minutes/month",
        },
        "principle_ru": "SLA-цели — доступность API, латентность, пропускная способность очередей",
    }
