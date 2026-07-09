"""RFC-0019 Ch.10 — TypeScript SDK manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.types import SDKLanguage


def typescript_sdk_manifest() -> dict[str, Any]:
    return {
        "language": SDKLanguage.TYPESCRIPT.value,
        "package": "@flowsint/sdk",
        "version": "2.0.0",
        "min_node": "18",
        "modules": {
            "client": "PlatformClient",
            "events": "EventSubscriber",
            "auth": "JWTAuthProvider",
            "plugin_generator": "generatePlugin",
        },
        "features": [
            "fetch_client",
            "typed_interfaces",
            "event_websocket_stub",
            "plugin_scaffold_cli",
            "retry_backoff",
            "correlation_id_header",
        ],
        "install": "npm install @flowsint/sdk",
        "templates": ["connector_plugin", "dashboard_widget", "report_template"],
    }
