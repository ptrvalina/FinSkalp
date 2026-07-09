"""RFC-0019 Ch.10 — Python SDK manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.types import SDKLanguage


def python_sdk_manifest() -> dict[str, Any]:
    return {
        "language": SDKLanguage.PYTHON.value,
        "package": "flowsint-sdk",
        "version": "2.0.0",
        "min_python": "3.11",
        "modules": {
            "client": "flowsint_sdk.client.PlatformClient",
            "events": "flowsint_sdk.events.EventSubscriber",
            "auth": "flowsint_sdk.auth.JWTAuthProvider",
            "plugin_generator": "flowsint_sdk.cli.generate_plugin",
        },
        "features": [
            "async_http_client",
            "typed_models_pydantic",
            "event_subscription",
            "plugin_scaffold_cli",
            "retry_backoff",
            "correlation_id_header",
        ],
        "install": "pip install flowsint-sdk",
        "templates": ["connector_plugin", "analytics_plugin", "rules_plugin"],
    }
