"""RFC-0020 Ch.19 — BCP/DR manifest."""

from __future__ import annotations

from typing import Any


def continuity_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 19,
        "bcp": {
            "rto_hours": 4,
            "rpo_hours": 1,
            "critical_services": [
                "flowsint-api",
                "postgresql",
                "redis",
                "flowsint-core-worker",
            ],
            "runbook_ref": "docs/operations/bcp-runbook.md",
        },
        "dr": {
            "backup_strategy": {
                "postgresql": "continuous WAL + daily snapshot",
                "neo4j": "daily dump",
                "evidence_store": "S3 cross-region replication",
                "audit_logs": "append-only WORM bucket",
            },
            "failover": {
                "database": "hot standby (planned)",
                "api": "multi-AZ deployment",
                "workers": "auto-scaling Celery pool",
            },
            "dr_test_frequency": "quarterly",
        },
        "incident_response": {
            "severity_levels": ["SEV1", "SEV2", "SEV3", "SEV4"],
            "notification_channels": ["pagerduty", "email", "slack"],
            "escalation_minutes": {"SEV1": 15, "SEV2": 60},
        },
        "principle_ru": "Непрерывность бизнеса — RTO/RPO, резервное копирование, DR-тестирование",
    }
