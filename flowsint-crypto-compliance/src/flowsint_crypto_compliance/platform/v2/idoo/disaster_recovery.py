"""RFC-0021 Ch.15 — disaster recovery RTO/RPO targets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.backup_runner import get_last_backup_status


def disaster_recovery_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 15,
        "targets": {
            "postgres": {"rto_minutes": 60, "rpo_minutes": 15, "strategy": "point_in_time_recovery"},
            "neo4j": {"rto_minutes": 120, "rpo_minutes": 60, "strategy": "snapshot_restore"},
            "redis": {"rto_minutes": 15, "rpo_minutes": 5, "strategy": "aof_replay"},
            "api": {"rto_minutes": 30, "rpo_minutes": 0, "strategy": "multi_az_failover"},
            "evidence": {"rto_minutes": 240, "rpo_minutes": 60, "strategy": "cross_region_replica"},
        },
        "failover": {
            "automated": False,
            "runbook": "operations.py#dr-failover",
            "technical_debt": "TD-IDOO-5",
        },
        "dr_site": {
            "region": "secondary",
            "sync": "async_replication",
            "last_tested": None,
        },
        "principle_ru": "Цели RTO/RPO для postgres, neo4j, redis, api, evidence",
    }


def dr_readiness_snapshot() -> dict[str, Any]:
    """Additive DR readiness derived from the last local backup run."""
    last = get_last_backup_status()
    if not last:
        return {
            "backup_recent": False,
            "last_backup_at": None,
            "age_hours": None,
            "restore_test_due": True,
        }
    completed = last.get("completed_at") or last.get("started_at")
    age_hours: float | None = None
    backup_recent = False
    if isinstance(completed, str):
        try:
            ts = datetime.strptime(completed, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
            backup_recent = age_hours <= 24.0
        except ValueError:
            pass
    return {
        "backup_recent": backup_recent,
        "last_backup_at": completed,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
        "manifest_sha256": last.get("manifest_sha256"),
        "restore_test_due": not backup_recent,
    }
