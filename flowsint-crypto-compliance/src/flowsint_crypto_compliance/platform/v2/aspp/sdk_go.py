"""RFC-0019 Ch.10 — Go SDK manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.types import SDKLanguage


def go_sdk_manifest() -> dict[str, Any]:
    return {
        "language": SDKLanguage.GO.value,
        "package": "github.com/flowsint/flowsint-sdk-go",
        "version": "v2.0.0",
        "min_go": "1.22",
        "modules": {
            "client": "platform.Client",
            "events": "events.Subscriber",
            "auth": "auth.JWTProvider",
            "plugin_generator": "cmd/flowsint-plugin-gen",
        },
        "features": [
            "http_client",
            "context_aware",
            "event_subscription",
            "plugin_scaffold_cli",
            "retry_backoff",
            "correlation_id_header",
        ],
        "install": "go get github.com/flowsint/flowsint-sdk-go/v2",
        "templates": ["collector_plugin", "grpc_bridge"],
    }
