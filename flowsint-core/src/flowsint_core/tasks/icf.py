"""Celery tasks — RFC-0014 ICF scheduled collections."""

from __future__ import annotations

import os
import uuid
from typing import Any

from celery import states

from flowsint_core.core.celery import celery


def _run(coro):
    import asyncio

    return asyncio.run(coro)


@celery.task(name="icf_run_scheduled_collections", bind=True)
def icf_run_scheduled_collections(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.icf.orchestrator import run_icf_pipeline
    from flowsint_crypto_compliance.platform.v2.icf.scheduler import get_collection_scheduler

    self.update_state(state=states.STARTED, meta={"task": "icf_scheduled_collections"})
    scheduler = get_collection_scheduler()
    tenant_id = uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
    results: list[dict[str, Any]] = []

    for job in scheduler.due_jobs():
        scheduler.mark_running(job.job_id)
        try:
            result = _run(
                run_icf_pipeline(
                    connector_id=job.connector_id,
                    tenant_id=tenant_id,
                    query=job.query,
                    case_ref=job.case_ref,
                    publish=True,
                )
            )
            if result.ok:
                scheduler.mark_completed(job.job_id)
            else:
                scheduler.mark_failed(job.job_id, "; ".join(result.errors) or "pipeline failed")
            results.append({"job_id": job.job_id, "ok": result.ok, "connector_id": job.connector_id})
        except Exception as exc:
            scheduler.mark_failed(job.job_id, str(exc))
            results.append({"job_id": job.job_id, "ok": False, "error": str(exc)})

    return {"ok": True, "processed": len(results), "results": results}
