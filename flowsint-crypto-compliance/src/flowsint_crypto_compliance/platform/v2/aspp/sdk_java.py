"""RFC-0019 Ch.10 — Java SDK manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.types import SDKLanguage


def java_sdk_manifest() -> dict[str, Any]:
    return {
        "language": SDKLanguage.JAVA.value,
        "package": "com.flowsint.sdk",
        "version": "2.0.0",
        "min_java": "17",
        "modules": {
            "client": "com.flowsint.sdk.PlatformClient",
            "events": "com.flowsint.sdk.events.EventSubscriber",
            "auth": "com.flowsint.sdk.auth.JwtAuthProvider",
            "plugin_generator": "com.flowsint.sdk.cli.PluginGenerator",
        },
        "features": [
            "okhttp_client",
            "jackson_models",
            "event_subscription",
            "plugin_scaffold_cli",
            "retry_backoff",
            "correlation_id_header",
        ],
        "install": "implementation 'com.flowsint:flowsint-sdk:2.0.0'",
        "templates": ["enterprise_connector", "rules_engine_plugin"],
    }
