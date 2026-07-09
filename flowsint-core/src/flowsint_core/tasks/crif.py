"""Celery tasks — RFC-0015 CRIF registry sync."""

from __future__ import annotations

import os
import uuid
from typing import Any

from celery import states

from flowsint_core.core.celery import celery

_REGISTRY_CONNECTORS = (
    "registry.sovereign",
    "registry.ofac",
    "registry.cis_vasp",
    "registry.corporate",
)


def _run(coro):
    import asyncio

    return asyncio.run(coro)


@celery.task(name="crif_sync_registries", bind=True)
def crif_sync_registries(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif.orchestrator import run_crif_pipeline

    self.update_state(state=states.STARTED, meta={"task": "crif_sync_registries"})
    tenant_id = uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
    results: list[dict[str, Any]] = []

    for connector_id in _REGISTRY_CONNECTORS:
        try:
            result = _run(
                run_crif_pipeline(
                    connector_id=connector_id,
                    tenant_id=tenant_id,
                    query={"entity_value": "CRIF-SYNC-ORG", "organization": "CRIF Sync Organization"},
                    case_ref="CRIF-SYNC",
                    organization_key="CRIF-SYNC-ORG",
                    publish=True,
                )
            )
            results.append({"connector_id": connector_id, "ok": result.ok, "stages": len(result.stages)})
        except Exception as exc:
            results.append({"connector_id": connector_id, "ok": False, "error": str(exc)})

    return {"ok": True, "processed": len(results), "results": results}
