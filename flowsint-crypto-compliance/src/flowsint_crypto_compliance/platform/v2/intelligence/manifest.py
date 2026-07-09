"""Intelligence Platform manifest — RFC-0004."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.intelligence.blockchain_capabilities import (
    blockchain_capabilities_manifest,
)
from flowsint_crypto_compliance.platform.v2.intelligence.engines import SUPPORTED_CHAINS


def intelligence_platform_manifest(engines: list[Any] | None = None) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.intelligence.orchestrator import get_intelligence_engines

    eng_list = engines or get_intelligence_engines()
    bc = blockchain_capabilities_manifest()
    return {
        "rfc": "RFC-0004",
        "schema_version": "4.0.0",
        "title": "Intelligence Platform — Архитектура интеллектуального ядра v2.0",
        "rule_ru": "Все движки работают исключительно поверх Knowledge Graph",
        "orchestrator": "IntelligenceOrchestrator",
        "engines": [e.manifest_entry() for e in eng_list],
        "blockchain_chains": bc,
        "blockchain_capabilities": bc,
        "supported_chains": list(SUPPORTED_CHAINS),
        "osint_categories": [
            "social", "forum", "telegram", "news", "registry", "court_decision",
            "corporate", "document", "search", "archive", "scientific",
        ],
        "api": {
            "manifest": "/api/platform/v2/intelligence/manifest",
            "analyze": "POST /api/platform/v2/intelligence/analyze",
        },
    }
