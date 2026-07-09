"""RFC-0021 Ch.15 — disaster recovery RTO/RPO targets."""

from __future__ import annotations

from typing import Any


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
