"""Celery tasks — RFC-0019 ASPP webhook delivery."""

from __future__ import annotations

from typing import Any

from celery import states

from flowsint_core.core.celery import celery


@celery.task(name="aspp_deliver_webhooks", bind=True)
def aspp_deliver_webhooks(self) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.aspp.orchestrator import dispatch_webhook

    self.update_state(state=states.STARTED, meta={"task": "aspp_deliver_webhooks"})
    result = dispatch_webhook(event_type="webhook.heartbeat", payload={"source": "celery.beat"})
    return {"ok": True, **result}
