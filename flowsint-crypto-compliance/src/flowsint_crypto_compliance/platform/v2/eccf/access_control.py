"""RFC-0017 Ch.15 — RBAC access control manifest."""

from __future__ import annotations

from typing import Any


def eccf_access_control_manifest() -> dict[str, Any]:
    """RBAC permissions for ECCF operations."""
    return {
        "permissions": {
            "eccf:view": {
                "description": "View evidence metadata and audit trail",
                "description_ru": "Просмотр метаданных доказательств и аудита",
                "roles": ["analyst", "lead_analyst", "compliance_officer", "auditor"],
            },
            "eccf:use": {
                "description": "Use evidence in investigations and reports",
                "description_ru": "Использование доказательств в расследованиях и отчётах",
                "roles": ["analyst", "lead_analyst", "compliance_officer"],
            },
            "eccf:export": {
                "description": "Export evidence packages",
                "description_ru": "Экспорт пакетов доказательств",
                "roles": ["lead_analyst", "compliance_officer", "auditor"],
            },
            "eccf:comment": {
                "description": "Add analyst comments to evidence chain",
                "description_ru": "Добавление комментариев аналитика к цепочке",
                "roles": ["analyst", "lead_analyst"],
            },
            "eccf:archive": {
                "description": "Archive evidence at case closure",
                "description_ru": "Архивация доказательств при закрытии дела",
                "roles": ["lead_analyst", "compliance_officer"],
            },
            "eccf:register": {
                "description": "Register new evidence via ECCF pipeline",
                "description_ru": "Регистрация новых доказательств через ECCF",
                "roles": ["analyst", "lead_analyst", "system_collector"],
            },
        },
        "principle": "Least privilege — evidence content is read-only after registration",
        "principle_ru": "Минимальные привилегии — содержимое неизменяемо после регистрации",
    }
