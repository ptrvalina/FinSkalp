"""RFC-0019 Ch.11 — security manifest (OAuth2/JWT/RBAC/ABAC/mTLS)."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.versioning import PLATFORM_API_VERSION


def security_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0019",
        "chapter": 11,
        "schema_version": PLATFORM_API_VERSION,
        "oauth2": {
            "enabled": False,
            "provider": "stub",
            "flows": ["authorization_code", "client_credentials"],
            "scopes": ["platform.read", "platform.write", "plugin.register"],
            "technical_debt": "TD-ASPP-3",
        },
        "jwt": {
            "enabled": True,
            "algorithm": "HS256",
            "issuer": "flowsint",
            "audience": "platform-v2",
            "ttl_seconds": 3600,
        },
        "rbac": {
            "enabled": True,
            "harmonized_layer": "platform/v2/rbac/",
            "roles": ["viewer", "analyst", "lead", "admin", "batch"],
        },
        "abac": {
            "enabled": True,
            "attributes": ["tenant_id", "case_ref", "investigation_id", "role"],
            "policy_engine": "stub",
        },
        "mtls": {
            "enabled": False,
            "required_for_internal": True,
            "ca_bundle_ref": "certs/platform-ca.pem",
        },
        "api_key": {
            "enabled": True,
            "header": "X-API-Key",
            "scopes": ["demo", "batch"],
        },
        "principle_ru": "Zero Trust — аутентификация и авторизация на каждом маршруте",
    }
