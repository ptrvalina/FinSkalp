"""RFC-0014 Ch.13 — security requirements manifest."""

from __future__ import annotations

from typing import Any


def icf_security_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0014",
        "chapter": 13,
        "requirements": [
            "secure_key_storage",
            "certificate_verification",
            "access_logging",
            "rate_limiting",
            "input_validation",
            "service_isolation",
        ],
        "implementation": {
            "vault": "flowsint vault secrets",
            "tls": "httpx verify=True default",
            "rate_limit": "icf.scheduler rate_limit_per_minute",
            "logging": "platform event bus + icf monitoring",
            "input_validation": "icf.validator + connector.validate",
            "isolation": "collector forbidden_modules — no direct KG/ER access",
        },
    }
