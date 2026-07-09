"""RFC-0022 EGPR orchestrator — maturity evaluation and RFC transitions."""

from __future__ import annotations

import time
from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.kpi_maturity import kpi_maturity_manifest
from flowsint_crypto_compliance.platform.v2.egpr.maturity import evaluate_maturity_criteria, maturity_manifest
from flowsint_crypto_compliance.platform.v2.egpr.principles import compliance_summary
from flowsint_crypto_compliance.platform.v2.egpr.rfc_lifecycle import (
    get_rfc_catalog,
    propose_rfc_transition as _propose_rfc_transition,
)


def propose_rfc_transition(
    rfc_id: str,
    target_stage: str,
    *,
    reviewer: str = "architecture_board",
) -> dict[str, Any]:
    return _propose_rfc_transition(rfc_id, target_stage, reviewer=reviewer)
from flowsint_crypto_compliance.platform.v2.egpr.tech_debt import tech_debt_manifest


def evaluate_maturity() -> dict[str, Any]:
    """Full maturity evaluation snapshot."""
    mat = maturity_manifest()
    principles = compliance_summary()
    debt = tech_debt_manifest()
    kpis = kpi_maturity_manifest()
    catalog = get_rfc_catalog()
    complete_rfcs = sum(1 for r in catalog if r["stage"] == "complete")
    accepted_rfcs = sum(1 for r in catalog if r["stage"] in ("complete", "accepted"))

    return {
        "ok": True,
        "maturity": mat,
        "principles": principles,
        "tech_debt": {
            "total": debt["total"],
            "open_count": debt["open_count"],
            "by_severity": debt["by_severity"],
        },
        "kpis": kpis["platform_kpis"],
        "rfc_summary": {
            "total": len(catalog),
            "complete": complete_rfcs,
            "accepted": accepted_rfcs,
        },
        "volume_i_status": "complete" if mat.get("volume_i_ready") else "in_progress",
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def run_maturity_snapshot() -> dict[str, Any]:
    """Celery beat entry — daily maturity snapshot."""
    result = evaluate_maturity()
    return {
        "ok": True,
        "task": "egpr_maturity_snapshot",
        **result,
    }
