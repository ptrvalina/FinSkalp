"""RFC-0022 Ch.17 — LTS support policy."""

from __future__ import annotations

from typing import Any


def support_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 17,
        "lts_policy": {
            "current_lts": "2.0.x",
            "lts_duration_months": 24,
            "security_patch_sla_days": 7,
            "bugfix_sla_days": 30,
            "eol_notice_months": 6,
        },
        "support_tiers": [
            {
                "tier": "community",
                "sla": "best effort",
                "channels": ["github issues"],
            },
            {
                "tier": "enterprise",
                "sla": "99.9% uptime",
                "channels": ["email", "dedicated slack"],
            },
            {
                "tier": "sovereign",
                "sla": "on-prem with air-gap support",
                "channels": ["secure portal", "on-site"],
            },
        ],
        "versioning": {
            "scheme": "semver",
            "api_prefix": "/api/platform/v2",
            "breaking_changes": "major version bump only",
        },
        "principle_ru": "LTS политика — 24 месяца поддержки, SLA патчей безопасности",
    }
