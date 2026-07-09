"""RFC-0021 Ch.14 — backup targets manifest."""

from __future__ import annotations

from typing import Any


def backup_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 14,
        "targets": [
            {
                "name": "postgres",
                "method": "pg_dump",
                "schedule": "0 2 * * *",
                "retention_days": 30,
                "encryption": "AES-256",
                "destination": "s3://finskalp-backups/postgres/",
            },
            {
                "name": "neo4j",
                "method": "neo4j-admin database dump",
                "schedule": "0 3 * * *",
                "retention_days": 14,
                "encryption": "AES-256",
                "destination": "s3://finskalp-backups/neo4j/",
            },
            {
                "name": "evidence",
                "method": "eccf repository export",
                "schedule": "0 4 * * *",
                "retention_days": 365,
                "encryption": "AES-256",
                "destination": "s3://finskalp-backups/evidence/",
                "rfc": "RFC-0017",
            },
            {
                "name": "audit",
                "method": "append-only audit log export",
                "schedule": "0 1 * * *",
                "retention_days": 2555,
                "encryption": "AES-256",
                "destination": "s3://finskalp-backups/audit/",
                "immutable": True,
            },
        ],
        "verification": {
            "restore_test_schedule": "monthly",
            "checksum": "sha256",
        },
        "principle_ru": "Резервное копирование postgres, neo4j, evidence, audit",
    }
