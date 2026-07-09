"""Celery tasks — RFC-0021 IDOO health probe batch."""

from __future__ import annotations

from typing import Any

from celery import states

from flowsint_core.core.celery import celery


@celery.task(name="idoo_health_probe_batch", bind=True)
def idoo_health_probe_batch(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.idoo.orchestrator import run_health_probe_batch

    self.update_state(state=states.STARTED, meta={"task": "idoo_health_probe_batch"})
    result = run_health_probe_batch()
    return {
        "ok": True,
        "task": "idoo_health_probe_batch",
        **result,
    }
