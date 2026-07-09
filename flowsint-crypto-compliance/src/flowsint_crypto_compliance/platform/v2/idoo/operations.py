"""RFC-0021 Ch.16 — operations runbook manifest per service."""

from __future__ import annotations

from typing import Any


def operations_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 16,
        "runbooks": [
            {
                "id": "rb-api-restart",
                "service": "flowsint-api",
                "title": "Restart API service",
                "steps": [
                    "Check /health endpoint",
                    "Review recent error logs",
                    "docker compose restart api",
                    "Verify /health returns 200",
                ],
            },
            {
                "id": "rb-celery-scale",
                "service": "flowsint-celery",
                "title": "Scale Celery workers",
                "steps": [
                    "Check queue depth via celery inspect active",
                    "Increase worker concurrency or replicas",
                    "Monitor task completion rate",
                ],
            },
            {
                "id": "rb-postgres-backup-restore",
                "service": "postgres",
                "title": "Restore Postgres from backup",
                "steps": [
                    "Stop dependent services",
                    "Restore pg_dump from S3",
                    "Run alembic upgrade head",
                    "Restart services and verify connectivity",
                ],
            },
            {
                "id": "rb-redis-flush",
                "service": "redis",
                "title": "Redis cache flush (emergency)",
                "steps": [
                    "Confirm no critical Celery tasks in flight",
                    "redis-cli FLUSHDB",
                    "Restart celery workers",
                ],
            },
            {
                "id": "rb-neo4j-recovery",
                "service": "neo4j",
                "title": "Neo4j recovery",
                "steps": [
                    "Stop neo4j container",
                    "Restore from neo4j-admin dump",
                    "Verify cypher-shell RETURN 1",
                ],
            },
            {
                "id": "dr-failover",
                "service": "platform",
                "title": "Disaster recovery failover",
                "steps": [
                    "Declare incident",
                    "Promote DR replica",
                    "Update DNS / load balancer",
                    "Verify all health checks green",
                    "Notify stakeholders",
                ],
            },
        ],
        "on_call": {
            "escalation": ["platform-team", "security-team"],
            "channels": ["pagerduty", "slack"],
        },
        "principle_ru": "Операционные runbook для api, celery, postgres, redis, neo4j, DR",
    }
