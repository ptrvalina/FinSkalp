"""RFC-0022 Ch.5 — RFC lifecycle and catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import RFCEntry, RFCLifecycleStage

_DOCS_ROOT = Path(__file__).resolve().parents[5]

_RFC_DEFINITIONS: list[dict[str, Any]] = [
    {"number": 0, "title": "Enterprise Constitution", "title_ru": "Конституция платформы", "stage": RFCLifecycleStage.ACCEPTED, "doc": "RFC-0000-enterprise-constitution.md"},
    {"number": 1, "title": "Enterprise Architecture Audit", "title_ru": "Архитектурный аудит", "stage": RFCLifecycleStage.DRAFT, "doc": "RFC-0001-enterprise-architecture-audit.md"},
    {"number": 2, "title": "Enterprise Architecture v2", "title_ru": "Архитектура 2-го поколения", "stage": RFCLifecycleStage.ACCEPTED, "doc": "RFC-0002-enterprise-architecture.md"},
    {"number": 3, "title": "Unified Data Model & Knowledge Graph v2.0", "title_ru": "Единая модель и граф знаний", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0003-unified-data-model-knowledge-graph.md"},
    {"number": 4, "title": "Intelligence Platform v2.0", "title_ru": "Архитектура интеллектуального ядра", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0004-intelligence-platform.md"},
    {"number": 5, "title": "Investigation Platform & Enterprise Operations v2.0", "title_ru": "Платформа расследований", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0005-investigation-platform.md"},
    {"number": 6, "title": "Intelligence Engine", "title_ru": "Движок анализа знаний", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0006-intelligence-engine.md"},
    {"number": 7, "title": "Integration & Intelligence Connectors v2.0", "title_ru": "Интеграции и коннекторы", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0007-integration-connectors.md"},
    {"number": 8, "title": "Enterprise Design System v2.0", "title_ru": "Корпоративная дизайн-система", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0008-enterprise-design-system.md"},
    {"number": 9, "title": "RBAC Harmonization v2.0", "title_ru": "Гармонизация RBAC", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0009-rbac-harmonization.md"},
    {"number": 10, "title": "Analyst Workspace & User Experience v2.0", "title_ru": "Рабочее место аналитика", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0010-analyst-workspace.md"},
    {"number": 11, "title": "Workflow & User Interaction Logic v2.0", "title_ru": "Логика workflow и взаимодействия", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0011-workflow-user-interaction.md"},
    {"number": 12, "title": "Blockchain Intelligence Framework v2.0", "title_ru": "Фреймворк блокчейн-аналитики", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0012-blockchain-intelligence.md"},
    {"number": 13, "title": "Incremental Block Sync", "title_ru": "Инкрементальная синхронизация блоков", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0013-incremental-block-sync.md"},
    {"number": 14, "title": "Intelligence Collection Framework v2.0", "title_ru": "Фреймворк сбора разведданных", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0014-intelligence-collection-framework.md"},
    {"number": 15, "title": "Compliance & Registry Intelligence Framework v2.0", "title_ru": "Комплаенс и реестровая аналитика", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0015-compliance-registry-intelligence.md"},
    {"number": 16, "title": "Risk & Decision Engine v2.0", "title_ru": "Движок рисков и решений", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0016-risk-decision-engine.md"},
    {"number": 17, "title": "Evidence & Chain of Custody Framework v2.0", "title_ru": "Доказательства и цепочка хранения", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0017-evidence-chain-of-custody.md"},
    {"number": 18, "title": "Explainable AI & Investigation Assistant v2.0", "title_ru": "Объяснимый ИИ и ассистент", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0018-explainable-ai-investigation-assistant.md"},
    {"number": 19, "title": "API, SDK & Plugin Platform v2.0", "title_ru": "API, SDK и платформа плагинов", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0019-api-sdk-plugin-platform.md"},
    {"number": 20, "title": "Enterprise Security Architecture v2.0", "title_ru": "Корпоративная безопасность", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0020-enterprise-security-architecture.md"},
    {"number": 21, "title": "Infrastructure, DevOps & Observability v2.0", "title_ru": "Инфраструктура, DevOps и наблюдаемость", "stage": RFCLifecycleStage.COMPLETE, "doc": "RFC-0021-infrastructure-devops-observability.md"},
]

_VALID_TRANSITIONS: dict[RFCLifecycleStage, set[RFCLifecycleStage]] = {
    RFCLifecycleStage.DRAFT: {RFCLifecycleStage.PROPOSED, RFCLifecycleStage.REJECTED},
    RFCLifecycleStage.PROPOSED: {RFCLifecycleStage.UNDER_REVIEW, RFCLifecycleStage.DRAFT},
    RFCLifecycleStage.UNDER_REVIEW: {RFCLifecycleStage.ACCEPTED, RFCLifecycleStage.REJECTED, RFCLifecycleStage.DRAFT},
    RFCLifecycleStage.ACCEPTED: {RFCLifecycleStage.IMPLEMENTED, RFCLifecycleStage.SUPERSEDED},
    RFCLifecycleStage.IMPLEMENTED: {RFCLifecycleStage.COMPLETE, RFCLifecycleStage.SUPERSEDED},
    RFCLifecycleStage.COMPLETE: {RFCLifecycleStage.SUPERSEDED},
    RFCLifecycleStage.SUPERSEDED: set(),
    RFCLifecycleStage.REJECTED: {RFCLifecycleStage.DRAFT},
}

_rfc_catalog: dict[str, RFCEntry] = {}


def _completion_doc_path(number: int) -> str | None:
    if number < 3:
        return None
    rel = f"docs/architecture/v2/rfc{number:04d}-completion.md"
    if (_DOCS_ROOT / rel).is_file():
        return rel
    return None


def _build_catalog() -> dict[str, RFCEntry]:
    if _rfc_catalog:
        return _rfc_catalog
    for defn in _RFC_DEFINITIONS:
        num = defn["number"]
        rfc_id = f"RFC-{num:04d}"
        entry = RFCEntry(
            id=rfc_id,
            number=num,
            title=defn["title"],
            title_ru=defn["title_ru"],
            stage=defn["stage"],
            completion_doc=_completion_doc_path(num),
            doc_path=f"docs/rfc/{defn['doc']}",
        )
        _rfc_catalog[rfc_id] = entry
    return _rfc_catalog


def get_rfc_catalog() -> list[dict[str, Any]]:
    catalog = _build_catalog()
    return [e.to_dict() for e in sorted(catalog.values(), key=lambda x: x.number)]


def get_rfc_entry(rfc_id: str) -> dict[str, Any] | None:
    entry = _build_catalog().get(rfc_id.upper())
    return entry.to_dict() if entry else None


def propose_rfc_transition(
    rfc_id: str,
    target_stage: str,
    *,
    reviewer: str = "architecture_board",
) -> dict[str, Any]:
    """Validate and stub-apply RFC lifecycle transition."""
    catalog = _build_catalog()
    entry = catalog.get(rfc_id.upper())
    if entry is None:
        return {"ok": False, "error": "rfc_not_found", "rfc_id": rfc_id}

    try:
        target = RFCLifecycleStage(target_stage)
    except ValueError:
        return {"ok": False, "error": "invalid_stage", "target_stage": target_stage}

    allowed = _VALID_TRANSITIONS.get(entry.stage, set())
    if target not in allowed:
        return {
            "ok": False,
            "error": "invalid_transition",
            "from": entry.stage.value,
            "to": target.value,
            "allowed": sorted(s.value for s in allowed),
        }

    # Stub: record transition without mutating catalog (immutable bootstrap)
    return {
        "ok": True,
        "rfc_id": entry.id,
        "from_stage": entry.stage.value,
        "to_stage": target.value,
        "reviewer": reviewer,
        "message": "Transition approved (not configured — catalog is read-only bootstrap)",
    }


def rfc_lifecycle_manifest() -> dict[str, Any]:
    catalog = get_rfc_catalog()
    stages = {s.value: sum(1 for r in catalog if r["stage"] == s.value) for s in RFCLifecycleStage}
    return {
        "rfc": "RFC-0022",
        "chapter": 5,
        "catalog_source": "docs/rfc/README.md",
        "rfc_count": len(catalog),
        "rfc_range": "RFC-0000 through RFC-0021",
        "stage_distribution": stages,
        "lifecycle_stages": [s.value for s in RFCLifecycleStage],
        "catalog": catalog,
        "principle_ru": "Жизненный цикл RFC — от черновика до полной реализации",
    }
