"""Celery tasks — RFC-0017 ECCF integrity verification batch."""

from __future__ import annotations

import os
import uuid
from typing import Any

from celery import states

from flowsint_core.core.celery import celery


def _run(coro):
    import asyncio

    return asyncio.run(coro)


@celery.task(name="eccf_verify_integrity_batch", bind=True)
def eccf_verify_integrity_batch(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository
    from flowsint_crypto_compliance.platform.v2.eccf.service import get_eccf_service

    self.update_state(state=states.STARTED, meta={"task": "eccf_verify_integrity_batch"})
    tenant_id = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    service = get_eccf_service()
    repo = get_eccf_repository()

    results: list[dict[str, Any]] = []
    for record in repo.list_all():
        if record.tenant_id != str(tenant_id):
            continue
        try:
            verification = service.verify_integrity(record.evidence_id)
            results.append({
                "evidence_id": record.evidence_id,
                "ok": verification.get("ok", False),
            })
        except Exception as exc:
            results.append({
                "evidence_id": record.evidence_id,
                "ok": False,
                "error": str(exc),
            })

    verified = sum(1 for r in results if r.get("ok"))
    return {
        "ok": True,
        "tenant_id": str(tenant_id),
        "processed": len(results),
        "verified": verified,
        "failed": len(results) - verified,
        "results": results,
    }
