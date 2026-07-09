"""RFC-0021 Ch.12 — HPA scaling rules stub per service."""

from __future__ import annotations

from typing import Any


def scaling_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 12,
        "hpa_rules": [
            {
                "service": "flowsint-api",
                "min_replicas": 2,
                "max_replicas": 10,
                "metrics": [{"type": "cpu", "target_percent": 70}],
                "scale_up_cooldown_seconds": 60,
                "scale_down_cooldown_seconds": 300,
            },
            {
                "service": "flowsint-celery-worker",
                "min_replicas": 2,
                "max_replicas": 20,
                "metrics": [{"type": "custom", "name": "celery_queue_depth", "target": 100}],
                "scale_up_cooldown_seconds": 30,
                "scale_down_cooldown_seconds": 600,
            },
            {
                "service": "flowsint-app",
                "min_replicas": 2,
                "max_replicas": 5,
                "metrics": [{"type": "cpu", "target_percent": 80}],
                "scale_up_cooldown_seconds": 120,
                "scale_down_cooldown_seconds": 300,
            },
        ],
        "celery_concurrency": {
            "dev": {"pool": "threads", "concurrency": 10},
            "prod": {"pool": "prefork", "concurrency": 4},
        },
        "technical_debt": "TD-IDOO-1",
        "principle_ru": "Автомасштабирование HPA по CPU и глубине очереди Celery",
    }
