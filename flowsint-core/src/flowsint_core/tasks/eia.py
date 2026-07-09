"""Celery tasks — RFC-0018 EIA context cache warming."""

from __future__ import annotations

import os
from typing import Any

from celery import states

from flowsint_core.core.celery import celery


def _run(coro):
    import asyncio

    return asyncio.run(coro)


@celery.task(name="eia_warm_context_cache", bind=True)
def eia_warm_context_cache(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eia.context_engine import build_investigation_context
    from flowsint_crypto_compliance.platform.v2.eia.monitoring import get_eia_metrics

    self.update_state(state=states.STARTED, meta={"task": "eia_warm_context_cache"})
    tenant_id = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    case_refs_raw = os.getenv("EIA_WARM_CASE_REFS", "")
    case_refs = [r.strip() for r in case_refs_raw.split(",") if r.strip()]

    if not case_refs:
        return {"ok": True, "warmed": 0, "note": "no EIA_WARM_CASE_REFS configured"}

    import uuid

    warmed = 0
    for case_ref in case_refs:
        try:
            _run(
                build_investigation_context(
                    case_ref=case_ref,
                    entity_keys=[],
                    tenant_id=uuid.UUID(tenant_id),
                    use_cache=False,
                )
            )
            warmed += 1
        except Exception:
            pass

    get_eia_metrics().record_cache_warm(warmed)
    return {"ok": True, "warmed": warmed, "case_refs": case_refs}
