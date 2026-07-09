"""RFC-0022 Ch.2 — strategic principles and compliance check."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import StrategicPrinciple

_PRINCIPLE_COMPLIANCE: dict[StrategicPrinciple, dict[str, Any]] = {
    StrategicPrinciple.ENTITY_FIRST: {
        "rfc": "RFC-0002",
        "status": "implemented",
        "module": "platform/v2/knowledge_model",
    },
    StrategicPrinciple.EVIDENCE_FIRST: {
        "rfc": "RFC-0017",
        "status": "implemented",
        "module": "platform/v2/eccf",
    },
    StrategicPrinciple.API_FIRST: {
        "rfc": "RFC-0019",
        "status": "implemented",
        "module": "platform/v2/aspp",
    },
    StrategicPrinciple.PLUGIN_FIRST: {
        "rfc": "RFC-0019",
        "status": "partial",
        "module": "platform/v2/plugin_registry",
        "debt": "TD-C4",
    },
    StrategicPrinciple.EXPLAINABILITY: {
        "rfc": "RFC-0018",
        "status": "implemented",
        "module": "platform/v2/eia",
    },
    StrategicPrinciple.HUMAN_IN_THE_LOOP: {
        "rfc": "RFC-0011",
        "status": "implemented",
        "module": "platform/v2/workflow",
    },
    StrategicPrinciple.KNOWLEDGE_GRAPH: {
        "rfc": "RFC-0003",
        "status": "implemented",
        "module": "platform/v2/knowledge_model",
    },
    StrategicPrinciple.EVENT_DRIVEN: {
        "rfc": "RFC-0004",
        "status": "implemented",
        "module": "platform/v2/events",
    },
    StrategicPrinciple.SOVEREIGN_BY_DESIGN: {
        "rfc": "RFC-0020",
        "status": "implemented",
        "module": "platform/v2/esa",
    },
    StrategicPrinciple.MODULARITY: {
        "rfc": "RFC-0002",
        "status": "implemented",
        "module": "platform/v2/",
    },
}


def principles_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 2,
        "principles": [p.value for p in StrategicPrinciple],
        "principles_ru": {
            StrategicPrinciple.ENTITY_FIRST.value: "Entity First — сущность как первичный объект",
            StrategicPrinciple.EVIDENCE_FIRST.value: "Evidence First — доказательства first-class",
            StrategicPrinciple.API_FIRST.value: "API First — платформа через API",
            StrategicPrinciple.PLUGIN_FIRST.value: "Plugin First — расширяемость плагинами",
            StrategicPrinciple.EXPLAINABILITY.value: "Explainability — объяснимый интеллект",
            StrategicPrinciple.HUMAN_IN_THE_LOOP.value: "Human in the Loop — аналитик в центре",
            StrategicPrinciple.KNOWLEDGE_GRAPH.value: "Knowledge Graph — граф знаний",
            StrategicPrinciple.EVENT_DRIVEN.value: "Event Driven — событийная архитектура",
            StrategicPrinciple.SOVEREIGN_BY_DESIGN.value: "Sovereign by Design — суверенность",
            StrategicPrinciple.MODULARITY.value: "Modularity — модульность платформы",
        },
        "principle_count": len(StrategicPrinciple),
        "principle_ru": "Десять стратегических принципов Enterprise Constitution (RFC-0000)",
    }


def check_principle_compliance(principle: str) -> dict[str, Any]:
    """Evaluate a strategic principle against implemented RFC modules."""
    try:
        p = StrategicPrinciple(principle)
    except ValueError:
        return {"ok": False, "principle": principle, "error": "unknown_principle"}

    mapping = _PRINCIPLE_COMPLIANCE.get(p, {})
    status = mapping.get("status", "unknown")
    return {
        "ok": status in ("implemented", "partial"),
        "principle": p.value,
        "compliance_status": status,
        "rfc": mapping.get("rfc"),
        "module": mapping.get("module"),
        "technical_debt": mapping.get("debt"),
    }


def compliance_summary() -> dict[str, Any]:
    checks = [check_principle_compliance(p.value) for p in StrategicPrinciple]
    implemented = sum(1 for c in checks if c.get("compliance_status") == "implemented")
    partial = sum(1 for c in checks if c.get("compliance_status") == "partial")
    return {
        "total": len(StrategicPrinciple),
        "implemented": implemented,
        "partial": partial,
        "checks": checks,
    }
