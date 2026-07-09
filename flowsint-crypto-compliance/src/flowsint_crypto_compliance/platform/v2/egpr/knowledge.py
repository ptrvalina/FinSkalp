"""RFC-0022 Ch.11 — knowledge management portal."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.developer_portal import developer_portal_manifest


def knowledge_manifest() -> dict[str, Any]:
    portal = developer_portal_manifest()
    return {
        "rfc": "RFC-0022",
        "chapter": 11,
        "title_ru": "Портал знаний FinSkalp",
        "portals": {
            "rfc_catalog": {
                "path": "/docs/rfc/README.md",
                "description_ru": "Каталог RFC Volume I (0000–0022)",
            },
            "architecture": {
                "path": "/docs/architecture/v2/README.md",
                "description_ru": "Архитектура to-be v2",
            },
            "completion_docs": {
                "path": "/docs/architecture/v2/",
                "pattern": "rfc{NNNN}-completion.md",
                "description_ru": "Чеклисты завершения RFC",
            },
            "audit": {
                "path": "/docs/audit/",
                "description_ru": "Архитектурный аудит и технический долг",
            },
            "developer_portal": portal["docs"],
        },
        "runbooks": [
            {"id": "RB-001", "title": "Platform health check", "path": "/api/platform/v2/idoo/health"},
            {"id": "RB-002", "title": "Backup manifest", "path": "/api/platform/v2/idoo/backup"},
            {"id": "RB-003", "title": "Security monitoring", "path": "/api/platform/v2/esa/monitoring"},
            {"id": "RB-004", "title": "EGPR maturity snapshot", "path": "/api/platform/v2/egpr/maturity"},
        ],
        "principle_ru": "Управление знаниями — единый портал RFC, архитектуры и runbooks",
    }
