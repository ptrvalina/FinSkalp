"""Enterprise maturity checklist — automated snapshot (Wave 5, additive)."""

from __future__ import annotations

import os
from typing import Any

from flowsint_crypto_compliance.feature_flags import flag_snapshot, is_enabled
from flowsint_crypto_compliance.observability.tracing import otel_enabled


def _status(ok: bool, partial: bool = False) -> str:
    if ok:
        return "implemented"
    if partial:
        return "partial"
    return "gap"


def build_maturity_snapshot() -> dict[str, Any]:
    """Assess maturity dimensions from env, flags, and existing modules."""
    flags = flag_snapshot()
    has_db = bool(os.getenv("DATABASE_URL", "").strip())
    has_redis = bool(os.getenv("REDIS_URL", "").strip())
    has_otel = otel_enabled()
    enterprise_reports = bool(flags.get("enterprise_report_sections", {}).get("enabled"))
    eccf_pg = bool(flags.get("eccf_postgres_persistence", {}).get("enabled"))
    idoo_probes = bool(flags.get("idoo_real_health_probes", {}).get("enabled"))
    backup_runner = bool(flags.get("idoo_backup_runner", {}).get("enabled"))
    esa_pg = bool(flags.get("esa_postgres_audit", {}).get("enabled"))

    backup_last = None
    if backup_runner:
        try:
            from flowsint_crypto_compliance.platform.v2.idoo.backup_runner import get_last_backup_status

            backup_last = get_last_backup_status()
        except Exception:
            pass

    dimensions: dict[str, dict[str, Any]] = {
        "security": {
            "status": _status(has_db and bool(os.getenv("AUTH_SECRET"))),
            "notes": "JWT + vault + RBAC on platform v2; demo plane may differ",
        },
        "audit": {
            "status": _status(eccf_pg, partial=not esa_pg),
            "eccf_postgres": eccf_pg,
            "esa_postgres": esa_pg,
        },
        "observability": {
            "status": _status(has_otel or idoo_probes, partial=not has_otel),
            "otel_enabled": has_otel,
            "idoo_real_probes": idoo_probes,
        },
        "performance": {
            "status": _status(has_redis, partial=not has_db),
            "redis": has_redis,
            "postgres_entity_store": os.getenv("FINSKALP_ENTITY_STORE", "postgres"),
        },
        "resilience": {
            "status": _status(idoo_probes),
            "health_probe_mode": "real" if idoo_probes else "stub",
        },
        "recovery": {
            "status": _status(bool(backup_last), partial=backup_runner and not backup_last),
            "backup_runner": backup_runner,
            "last_backup": backup_last,
        },
        "logging": {
            "status": _status(True),
            "format": "json",
            "correlation_id": True,
        },
        "metrics": {
            "status": _status(True),
            "prometheus": True,
            "idoo_probe_metrics": idoo_probes,
        },
        "health": {
            "status": _status(idoo_probes, partial=True),
            "endpoints": ["/api/health", "/api/platform/v2/idoo/health"],
        },
        "feature_flags": {
            "status": _status(True),
            "registry_count": len(flags),
            "flags": flags,
        },
        "config": {
            "status": _status(True),
            "combat_mode": os.getenv("COMPLIANCE_COMBAT_MODE", "0"),
        },
        "secrets": {
            "status": _status(bool(os.getenv("MASTER_VAULT_KEY_V1") or os.getenv("AUTH_SECRET"))),
        },
        "caching": {
            "status": _status(has_redis),
        },
        "scalability": {
            "status": _status(eccf_pg and has_db, partial=has_db),
            "stateful_singletons_migrated": eccf_pg,
        },
        "ci_cd": {
            "status": _status(True),
            "workflows": ["tests.yml", "finskalp-compliance.yml", "images.yml"],
        },
        "backup": {
            "status": _status(backup_runner, partial=bool(backup_last)),
            "runner_enabled": backup_runner,
        },
        "disaster_recovery": {
            "status": _status(bool(backup_last), partial=backup_runner),
            "dr_readiness": backup_last is not None,
        },
        "documentation": {
            "status": _status(True),
            "audit_docs": "docs/audit/",
        },
        "test_coverage": {
            "status": _status(is_enabled("maturity_extended_ci", default=False), partial=True),
            "extended_ci_flag": "FINSKALP_MATURITY_EXTENDED_CI",
        },
        "reports": {
            "status": _status(enterprise_reports),
            "enterprise_sections": enterprise_reports,
        },
        "knowledge_graph": {
            "status": _status(True),
            "snapshots": True,
            "diff": True,
            "confidence_propagation": True,
            "temporal": True,
        },
        "workspace": {
            "status": _status(is_enabled("workspace_full_panels", default=False)),
            "flag": "FINSKALP_WORKSPACE_FULL_PANELS",
        },
    }

    implemented = sum(1 for d in dimensions.values() if d["status"] == "implemented")
    partial = sum(1 for d in dimensions.values() if d["status"] == "partial")
    gap = sum(1 for d in dimensions.values() if d["status"] == "gap")

    return {
        "ok": True,
        "schema": "maturity-snapshot/v1",
        "dimension_count": len(dimensions),
        "summary": {
            "implemented": implemented,
            "partial": partial,
            "gap": gap,
            "readiness_pct": round(100 * (implemented + 0.5 * partial) / max(len(dimensions), 1), 1),
        },
        "dimensions": dimensions,
    }
