"""RFC-0021 Ch.13 — Celery queue catalog from beat schedules."""

from __future__ import annotations

from typing import Any


def _beat_schedule() -> dict[str, Any]:
    try:
        from flowsint_core.core.celery import celery

        return dict(celery.conf.beat_schedule or {})
    except Exception:
        return {}


def queues_manifest() -> dict[str, Any]:
    beat = _beat_schedule()
    beat_tasks = [
        {
            "beat_key": key,
            "task": entry.get("task", ""),
            "schedule_seconds": entry.get("schedule"),
            "kwargs": entry.get("kwargs", {}),
        }
        for key, entry in beat.items()
    ]
    platform_tasks = [
        t for t in beat_tasks
        if any(
            prefix in t["task"]
            for prefix in (
                "icf_",
                "crif_",
                "rde_",
                "eccf_",
                "eia_",
                "aspp_",
                "esa_",
                "idoo_",
            )
        )
    ]
    return {
        "rfc": "RFC-0021",
        "chapter": 13,
        "broker": "redis",
        "default_queue": "celery",
        "named_queues": [
            "celery",
            "scalpel-onchain",
            "scalpel-sanctions",
            "scalpel-username",
            "scalpel-abuse",
            "scalpel-darknet",
            "scalpel-vasp",
            "scalpel-court",
            "scalpel-dns",
            "scalpel-fusion",
            "scalpel-enforcement",
            "live-onchain",
            "live-sanctions",
            "live-abuse",
            "live-username",
            "live-darknet",
        ],
        "beat_schedule": beat_tasks,
        "platform_beat_tasks": platform_tasks,
        "platform_task_count": len(platform_tasks),
        "principle_ru": "Каталог очередей Celery и beat-задач платформы (ICF, CRIF, RDE, ECCF, EIA, ASPP, ESA, IDOO)",
    }
