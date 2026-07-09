"""Celery tasks — batch screening, watchlist monitoring."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from celery import states

from flowsint_core.core.celery import celery
from flowsint_core.core.postgre_db import SessionLocal
from flowsint_crypto_compliance.infrastructure.idempotency import IdempotencyStore, make_idempotency_key
from flowsint_crypto_compliance.observability.tracing import trace_celery_task


def _run(coro):
    return asyncio.run(coro)


@celery.task(name="run_batch_wallet_screen", bind=True)
@trace_celery_task("run_batch_wallet_screen")
def run_batch_wallet_screen(
    self,
    job_id: str,
    rows: list[dict[str, str]],
    *,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.observability.metrics import COMPLIANCE_BATCH_SCREEN_TOTAL
    from flowsint_crypto_compliance.services.batch_screening import BatchScreeningService
    from flowsint_crypto_compliance.storage.db_models import ComplianceBatchScreenJob

    idem = idempotency_key or make_idempotency_key("batch_screen", job_id)
    store = IdempotencyStore()
    if store.acquire("run_batch_wallet_screen", idem) == "done":
        cached = store.get_result("run_batch_wallet_screen", idem)
        if cached is not None:
            return cached

    session = SessionLocal()
    try:
        self.update_state(state=states.STARTED, meta={"job_id": job_id})
        job = session.get(ComplianceBatchScreenJob, uuid.UUID(job_id))
        if job:
            job.celery_task_id = self.request.id
            job.status = "running"
            session.commit()
        svc = BatchScreeningService(session)
        summary = _run(svc.run_job_sync(uuid.UUID(job_id), rows))
        COMPLIANCE_BATCH_SCREEN_TOTAL.labels(status="completed").inc()
        store.complete("run_batch_wallet_screen", idem, summary)
        return summary
    except Exception:
        COMPLIANCE_BATCH_SCREEN_TOTAL.labels(status="failed").inc()
        store.release("run_batch_wallet_screen", idem)
        job = session.get(ComplianceBatchScreenJob, uuid.UUID(job_id))
        if job:
            job.status = "failed"
            session.commit()
        raise
    finally:
        session.close()


@celery.task(name="scan_watchlist_subscriptions", bind=True)
@trace_celery_task("scan_watchlist_subscriptions")
def scan_watchlist_subscriptions(
    self,
    limit: int = 200,
    *,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.services.watchlist_monitor import WatchlistMonitorService

    window = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    idem = idempotency_key or make_idempotency_key("watchlist_scan", window)
    store = IdempotencyStore()
    if store.acquire("scan_watchlist_subscriptions", idem) == "done":
        cached = store.get_result("scan_watchlist_subscriptions", idem)
        if cached is not None:
            return cached

    session = SessionLocal()
    try:
        self.update_state(state=states.STARTED, meta={"phase": "watchlist_scan"})
        svc = WatchlistMonitorService(session)
        result = _run(svc.scan_all_active(limit=limit))
        store.complete("scan_watchlist_subscriptions", idem, result)
        return result
    except Exception:
        store.release("scan_watchlist_subscriptions", idem)
        raise
    finally:
        session.close()
