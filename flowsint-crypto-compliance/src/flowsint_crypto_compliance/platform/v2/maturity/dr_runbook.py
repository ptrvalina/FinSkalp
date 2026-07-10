"""Disaster recovery restore runbook (operational JSON, Wave 5)."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.backup_runner import get_last_backup_status
from flowsint_crypto_compliance.platform.v2.idoo.disaster_recovery import disaster_recovery_manifest


def dr_restore_runbook() -> dict[str, Any]:
    last = get_last_backup_status()
    manifest = disaster_recovery_manifest()
    return {
        "ok": True,
        "rfc": "RFC-0021",
        "automated_failover": False,
        "targets": manifest["targets"],
        "last_backup": last,
        "steps": [
            {
                "order": 1,
                "action": "verify_backup_manifest",
                "command": "python flowsint-crypto-compliance/scripts/finskalp_backup.py --dry-run",
                "owner": "ops",
            },
            {
                "order": 2,
                "action": "restore_postgres",
                "command": "psql $DATABASE_URL < data/backups/<stamp>/postgres.sql",
                "note": "Only when FINSKALP_BACKUP_PG_DUMP=1 was used",
                "owner": "dba",
            },
            {
                "order": 3,
                "action": "restore_evidence_inventory",
                "command": "Compare backup_manifest.json evidence_inventory SHA-256 with data/osint_evidence",
                "owner": "forensics",
            },
            {
                "order": 4,
                "action": "smoke_health",
                "command": "curl -s $FINSKALP_API_HEALTH_URL",
                "owner": "ops",
            },
            {
                "order": 5,
                "action": "enable_real_probes",
                "command": "FINSKALP_IDOO_REAL_HEALTH_PROBES=1",
                "owner": "ops",
            },
        ],
        "rollback": "Unset feature flags and redeploy previous image tag",
    }
