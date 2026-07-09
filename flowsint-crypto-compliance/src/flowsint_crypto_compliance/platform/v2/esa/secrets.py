"""RFC-0020 Ch.8 — secrets management manifest."""

from __future__ import annotations

import re
from typing import Any

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{20,}['\"]"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]


def secrets_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 8,
        "vault": {
            "provider": "flowsint-core vault",
            "backend": "flowsint vault secrets",
            "paths": {
                "connectors": "vault://connectors/{connector_id}",
                "api_keys": "vault://platform/api-keys/{key_id}",
                "encryption": "vault://crypto/keys/{key_id}",
            },
            "rotation_policy_days": 90,
            "audit_access": True,
        },
        "no_secrets_in_code": {
            "enabled": True,
            "scan_patterns": [p.pattern for p in _SECRET_PATTERNS],
            "ci_gate": "pre-commit + CI scan",
            "allowed_env_prefixes": ["FINSKALP_", "VAULT_", "CELERY_"],
        },
        "forbidden_locations": [
            "source code literals",
            "git history (unrotated)",
            "docker images",
            "client-side bundles",
            "log output",
        ],
        "principle_ru": "Секреты только в vault — запрет хранения в коде и логах",
    }


def scan_for_secrets_in_text(text: str) -> list[dict[str, str]]:
    """Stub secret scanner — returns matches for CI/pre-commit."""
    findings: list[dict[str, str]] = []
    for pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            findings.append({
                "pattern": pattern.pattern,
                "match_preview": match.group()[:20] + "...",
            })
    return findings
