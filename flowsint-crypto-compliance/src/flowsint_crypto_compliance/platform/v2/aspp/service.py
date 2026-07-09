"""RFC-0019 ASPP service facade."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.developer_portal import developer_portal_manifest
from flowsint_crypto_compliance.platform.v2.aspp.event_catalog import event_catalog
from flowsint_crypto_compliance.platform.v2.aspp.manifest import aspp_manifest
from flowsint_crypto_compliance.platform.v2.aspp.monitoring import get_aspp_metrics
from flowsint_crypto_compliance.platform.v2.aspp.orchestrator import (
    dispatch_webhook,
    list_marketplace,
    register_plugin,
)
from flowsint_crypto_compliance.platform.v2.aspp.rest_catalog import rest_catalog
from flowsint_crypto_compliance.platform.v2.aspp.webhooks import get_webhook_registry


class ASPPService:
    """API, SDK & Plugin Platform service."""

    def manifest(self) -> dict[str, Any]:
        return aspp_manifest()

    def rest_catalog(self) -> dict[str, Any]:
        return rest_catalog()

    def event_catalog(self) -> dict[str, Any]:
        return event_catalog()

    def marketplace(self) -> dict[str, Any]:
        return list_marketplace()

    def developer_portal(self) -> dict[str, Any]:
        return developer_portal_manifest()

    def subscribe_webhook(
        self,
        *,
        url: str,
        event_types: list[str],
        secret: str | None = None,
    ) -> dict[str, Any]:
        sub = get_webhook_registry().subscribe(url=url, event_types=event_types, secret=secret)
        get_aspp_metrics().record_webhook_subscribe()
        return {"ok": True, "subscription": sub.to_dict()}

    def list_webhooks(self) -> dict[str, Any]:
        subs = get_webhook_registry().list_subscriptions()
        return {"ok": True, "subscriptions": [s.to_dict() for s in subs], "count": len(subs)}

    def register_plugin(self, payload: dict[str, Any]) -> dict[str, Any]:
        return register_plugin(payload)

    def dispatch_webhook(self, *, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return dispatch_webhook(event_type=event_type, payload=payload)

    def monitoring(self) -> dict[str, Any]:
        return {"ok": True, **get_aspp_metrics().get_metrics()}


_service: ASPPService | None = None


def get_aspp_service() -> ASPPService:
    global _service
    if _service is None:
        _service = ASPPService()
    return _service
