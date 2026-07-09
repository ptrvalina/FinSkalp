"""RFC-0020 Ch.9 — API protection pipeline descriptor."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.security_manifest import security_manifest as aspp_security
from flowsint_crypto_compliance.platform.v2.connectors.security import integration_security_manifest


def api_protection_pipeline() -> list[dict[str, Any]]:
    """Middleware pipeline stages for API request protection."""
    return [
        {
            "stage": 1,
            "name": "authentication",
            "description_ru": "JWT / API Key / service account",
            "handler": "flowsint_api.middleware.auth",
            "required": True,
        },
        {
            "stage": 2,
            "name": "authorization",
            "description_ru": "RBAC + ABAC через ESA evaluate_access",
            "handler": "platform.v2.esa.orchestrator.evaluate_security_request",
            "required": True,
        },
        {
            "stage": 3,
            "name": "schema_validation",
            "description_ru": "Pydantic request/response validation",
            "handler": "fastapi.routing",
            "required": True,
        },
        {
            "stage": 4,
            "name": "rate_limiting",
            "description_ru": "Per-tenant и per-endpoint лимиты",
            "handler": "compliance infrastructure circuit_breaker",
            "required": True,
        },
        {
            "stage": 5,
            "name": "audit",
            "description_ru": "Append-only security audit log",
            "handler": "platform.v2.esa.audit_system",
            "required": True,
        },
    ]


def api_protection_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 9,
        "pipeline": api_protection_pipeline(),
        "aspp_security": aspp_security(),
        "connector_security": integration_security_manifest(),
        "headers": {
            "required": ["Authorization", "X-Request-ID"],
            "optional": ["X-Tenant-ID", "X-Case-Ref"],
        },
        "rate_limits": {
            "default_rpm": 120,
            "batch_rpm": 30,
            "admin_rpm": 60,
        },
        "principle_ru": "Каждый API-запрос проходит auth → authz → schema → rate limit → audit",
    }
