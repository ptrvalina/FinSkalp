"""RFC-0019 ASPP orchestrator."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.constraints import aspp_architectural_constraints
from flowsint_crypto_compliance.platform.v2.aspp.marketplace import marketplace_catalog
from flowsint_crypto_compliance.platform.v2.aspp.monitoring import LatencyTimer, get_aspp_metrics
from flowsint_crypto_compliance.platform.v2.aspp.plugin_manager import get_plugin_manager
from flowsint_crypto_compliance.platform.v2.aspp.types import PluginCategory, PluginManifest
from flowsint_crypto_compliance.platform.v2.aspp.webhooks import get_webhook_registry


def _parse_manifest(data: dict[str, Any]) -> PluginManifest:
    category_raw = data.get("category", PluginCategory.CONNECTOR.value)
    if isinstance(category_raw, PluginCategory):
        category = category_raw
    else:
        category = PluginCategory(str(category_raw))
    return PluginManifest(
        plugin_id=str(data["plugin_id"]),
        category=category,
        version=str(data.get("version", "1.0.0")),
        name_ru=str(data.get("name_ru", data["plugin_id"])),
        description_ru=str(data.get("description_ru", "")),
        permissions=list(data.get("permissions", [])),
        dependencies=list(data.get("dependencies", [])),
        events_published=list(data.get("events_published", [])),
        events_subscribed=list(data.get("events_subscribed", [])),
        config_schema=dict(data.get("config_schema", {})),
        health_status=str(data.get("health_status", "healthy")),
        source=str(data.get("source", "api")),
        metadata=dict(data.get("metadata", {})),
    )


def register_plugin(manifest: PluginManifest | dict[str, Any]) -> dict[str, Any]:
    """Register a new plugin via ASPP plugin manager."""
    if isinstance(manifest, dict):
        manifest = _parse_manifest(manifest)

    forbidden = set(aspp_architectural_constraints()["forbidden_actions"])
    for perm in manifest.permissions:
        if perm in forbidden:
            return {"ok": False, "error": f"forbidden permission: {perm}"}

    mgr = get_plugin_manager()
    with LatencyTimer() as timer:
        try:
            mgr.register(manifest)
            get_aspp_metrics().record_plugin_register()
            ok = True
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
    get_aspp_metrics().record_request(endpoint="register_plugin", latency_ms=timer.elapsed_ms, ok=ok)
    get_webhook_registry().enqueue_delivery(
        event_type="plugin.registered",
        payload={"plugin_id": manifest.plugin_id, "version": manifest.version},
    )
    return {"ok": True, "plugin": manifest.to_dict()}


def list_marketplace() -> dict[str, Any]:
    with LatencyTimer() as timer:
        catalog = marketplace_catalog()
    get_aspp_metrics().record_request(endpoint="list_marketplace", latency_ms=timer.elapsed_ms)
    return catalog


def dispatch_webhook(*, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Enqueue and deliver pending webhooks (stub)."""
    reg = get_webhook_registry()
    with LatencyTimer() as timer:
        created = reg.enqueue_delivery(event_type=event_type, payload=payload or {})
        result = reg.deliver_pending()
    get_aspp_metrics().record_webhook_delivery(result.get("delivered", 0))
    get_aspp_metrics().record_request(endpoint="dispatch_webhook", latency_ms=timer.elapsed_ms)
    return {
        "ok": True,
        "event_type": event_type,
        "enqueued": len(created),
        **result,
    }
