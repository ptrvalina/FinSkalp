"""RFC-0007 integration security policies — Ch.9."""

from __future__ import annotations

from typing import Any


def integration_security_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0007",
        "chapter": 9,
        "requirements": [
            "api_key_vault",
            "network_request_control",
            "ssrf_protection",
            "rate_limiting",
            "access_logging",
            "tls_verification",
            "data_integrity_checks",
        ],
        "implementation": {
            "vault": "flowsint vault secrets",
            "rate_limit": "compliance infrastructure circuit_breaker",
            "tls": "httpx verify=True default",
            "logging": "platform event bus + compliance audit",
            "ssrf": "allowlist hosts per connector constraints",
        },
    }
