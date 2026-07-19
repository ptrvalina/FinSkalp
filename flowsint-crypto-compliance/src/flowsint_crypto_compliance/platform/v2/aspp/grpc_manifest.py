"""RFC-0019 Ch.6 — internal gRPC service stubs manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.versioning import PLATFORM_API_VERSION


def grpc_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0019",
        "chapter": 6,
        "schema_version": PLATFORM_API_VERSION,
        "status": "stub",
        "proto_package": "flowsint.platform.v2",
        "services": [
            {
                "name": "PluginRegistryService",
                "methods": ["ListPlugins", "RegisterPlugin", "GetHealth"],
                "proto_ref": "flowsint/platform/v2/plugin_registry.proto",
            },
            {
                "name": "EventBusService",
                "methods": ["Publish", "Subscribe", "Replay"],
                "proto_ref": "flowsint/platform/v2/event_bus.proto",
            },
            {
                "name": "InvestigationService",
                "methods": ["GetWorkspace", "ListEvidence", "GetTimeline"],
                "proto_ref": "flowsint/platform/v2/investigation.proto",
            },
            {
                "name": "WebhookDeliveryService",
                "methods": ["Enqueue", "Deliver", "RetryFailed"],
                "proto_ref": "flowsint/platform/v2/webhooks.proto",
            },
        ],
        "transport": "grpc_internal",
        "tls_required": True,
        "principle_ru": "gRPC — внутренние сервисы между микросервисами (not configured)",
        "technical_debt": "TD-ASPP-2",
    }
