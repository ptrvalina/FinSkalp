"""RFC-0019 Ch.18 — plugin architectural constraints."""

from __future__ import annotations

from typing import Any

_FORBIDDEN_ACTIONS = frozenset({
    "direct_knowledge_graph_mutation",
    "direct_risk_scoring",
    "entity_resolution_bypass",
    "direct_investigation_mutation",
    "bypass_ingest_pipeline",
    "bypass_rbac",
    "bypass_audit_trail",
    "silent_data_write",
    "auto_close_case",
    "cross_tenant_data_access",
})


def aspp_architectural_constraints() -> dict[str, Any]:
    return {
        "forbidden_actions": sorted(_FORBIDDEN_ACTIONS),
        "principle": "API First, Plugin First — extensions via manifest, not core forks",
        "principle_ru": "API First, Plugin First — расширения через манифест, без форков ядра",
        "api_first": True,
        "plugin_first": True,
        "mandatory_ingest_path": True,
        "rbac_enforced": True,
        "audit_required": True,
        "allowed_extension_points": [
            "connectors.registry.register",
            "plugin_manager.register",
            "event_bus.subscribe",
            "marketplace.publish",
            "webhooks.subscribe",
        ],
    }


def assert_not_forbidden(action: str) -> None:
    if action in _FORBIDDEN_ACTIONS:
        raise PermissionError(f"ASPP forbidden action: {action}")
