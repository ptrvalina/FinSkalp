"""Celery tasks — RFC-0016 RDE batch reassessment."""

from __future__ import annotations

import os
import uuid
from typing import Any

from celery import states

from flowsint_core.core.celery import celery


def _run(coro):
    import asyncio

    return asyncio.run(coro)


@celery.task(name="rde_batch_reassess", bind=True)
def rde_batch_reassess(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rde.orchestrator import run_rde_assessment

    self.update_state(state=states.STARTED, meta={"task": "rde_batch_reassess"})
    tenant_id = uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
    results: list[dict[str, Any]] = []

    entities = (
        os.getenv("RDE_BATCH_ENTITIES", "RDE-SYNC-ENTITY-1,RDE-SYNC-ENTITY-2").split(",")
    )

    for entity_key in entities:
        key = entity_key.strip()
        if not key:
            continue
        try:
            result = _run(
                run_rde_assessment(
                    entity_key=key,
                    tenant_id=tenant_id,
                    case_ref="RDE-BATCH",
                    signals={
                        "registry_signals": {"org_status": "active", "license_status": "valid"},
                        "blockchain_signals": {"transaction_count": 5, "volume_usd": 10000},
                    },
                )
            )
            results.append({
                "entity_key": key,
                "ok": result.ok,
                "risk_level": result.risk_level.value,
                "composite_score": result.composite_score,
            })
        except Exception as exc:
            results.append({"entity_key": key, "ok": False, "error": str(exc)})

    return {"ok": True, "processed": len(results), "results": results}
