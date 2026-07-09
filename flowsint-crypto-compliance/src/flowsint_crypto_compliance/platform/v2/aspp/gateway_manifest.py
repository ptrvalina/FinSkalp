"""RFC-0019 Ch.3 — gateway capabilities manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.versioning import PLATFORM_API_VERSION


def gateway_capabilities_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0019",
        "chapter": 3,
        "schema_version": PLATFORM_API_VERSION,
        "title_ru": "API Gateway — единая точка входа платформы",
        "capabilities": {
            "authentication": {
                "enabled": True,
                "methods": ["jwt_bearer", "api_key", "oauth2_stub"],
                "mTLS_optional": True,
            },
            "rate_limiting": {
                "enabled": True,
                "default_rpm": 600,
                "burst": 120,
                "per_tenant": True,
            },
            "routing": {
                "enabled": True,
                "prefix": "/api/platform/v2",
                "protocols": ["rest", "graphql_stub", "grpc_internal"],
            },
            "audit": {
                "enabled": True,
                "log_mutations": True,
                "correlation_id": True,
                "actor_tracking": True,
            },
        },
        "principles": ["api_first", "plugin_first", "zero_trust_boundary"],
        "principles_ru": [
            "API First — контракт до реализации",
            "Plugin First — расширения без форков ядра",
            "Zero Trust — RBAC на каждом маршруте",
        ],
    }
