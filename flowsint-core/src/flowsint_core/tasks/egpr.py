"""Celery tasks — RFC-0022 EGPR daily maturity snapshot."""

from __future__ import annotations

from typing import Any

from celery import states

from flowsint_core.core.celery import celery


@celery.task(name="egpr_maturity_snapshot", bind=True)
def egpr_maturity_snapshot(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.egpr.orchestrator import run_maturity_snapshot

    self.update_state(state=states.STARTED, meta={"task": "egpr_maturity_snapshot"})
    result = run_maturity_snapshot()
    return {
        "ok": True,
        "task": "egpr_maturity_snapshot",
        **result,
    }
