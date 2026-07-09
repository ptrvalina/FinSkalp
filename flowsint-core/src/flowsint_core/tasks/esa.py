"""Celery tasks — RFC-0020 ESA security scan batch."""

from __future__ import annotations

from typing import Any

from celery import states

from flowsint_core.core.celery import celery


@celery.task(name="esa_security_scan_batch", bind=True)
def esa_security_scan_batch(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.esa.orchestrator import run_security_scan

    self.update_state(state=states.STARTED, meta={"task": "esa_security_scan_batch"})
    result = run_security_scan()
    return {
        "ok": True,
        "task": "esa_security_scan_batch",
        **result,
    }
