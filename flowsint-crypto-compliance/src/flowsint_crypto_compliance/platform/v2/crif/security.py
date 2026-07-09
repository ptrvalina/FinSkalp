"""RFC-0015 Ch.15 — security requirements manifest."""

from __future__ import annotations

from typing import Any


def crif_security_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0015",
        "chapter": 15,
        "requirements": [
            "secure_key_storage",
            "certificate_verification",
            "access_logging",
            "rate_limiting",
            "input_validation",
            "service_isolation",
            "sanctions_data_protection",
        ],
        "implementation": {
            "vault": "flowsint vault secrets",
            "tls": "httpx verify=True default",
            "rate_limit": "crif.monitor + celery beat",
            "logging": "platform event bus + crif metrics",
            "input_validation": "schema_validator + connector.validate",
            "isolation": "connector forbidden_modules — no direct KG/risk/investigation",
            "sanctions": "requires_analyst_confirmation for probable matches",
        },
    }
