"""RFC-0022 Ch.15 — four-stage product roadmap."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import RoadmapPhase

_PHASES: dict[RoadmapPhase, dict[str, Any]] = {
    RoadmapPhase.MVP: {
        "name_ru": "MVP — минимальный продукт",
        "timeline": "2025-Q4 — 2026-Q1",
        "status": "complete",
        "rfcs": ["RFC-0000", "RFC-0002", "RFC-0003", "RFC-0004", "RFC-0005"],
        "features": [
            "Entity-first knowledge graph",
            "Intelligence fusion pipeline",
            "Investigation workspace",
            "Compliance demo stand",
        ],
    },
    RoadmapPhase.ENTERPRISE: {
        "name_ru": "Enterprise — корпоративное развёртывание",
        "timeline": "2026-Q1 — 2026-Q2",
        "status": "complete",
        "rfcs": [
            "RFC-0006", "RFC-0007", "RFC-0008", "RFC-0009", "RFC-0010",
            "RFC-0011", "RFC-0012", "RFC-0013", "RFC-0014", "RFC-0015",
            "RFC-0016", "RFC-0017", "RFC-0018",
        ],
        "features": [
            "RBAC harmonization",
            "Analyst workspace UX",
            "Blockchain intelligence",
            "Compliance registry screening",
            "Risk & decision engine",
            "Evidence chain of custody",
            "Explainable AI assistant",
        ],
    },
    RoadmapPhase.PLATFORM: {
        "name_ru": "Platform — экосистема и API",
        "timeline": "2026-Q2 — 2026-Q3",
        "status": "complete",
        "rfcs": ["RFC-0019", "RFC-0020", "RFC-0021", "RFC-0022"],
        "features": [
            "API, SDK & Plugin Platform",
            "Enterprise Security Architecture",
            "Infrastructure & Observability",
            "Enterprise Governance & Roadmap",
        ],
    },
    RoadmapPhase.NATIONAL_SCALE: {
        "name_ru": "National Scale — национальный масштаб",
        "timeline": "2026-Q4 — 2030",
        "status": "planned",
        "rfcs": [],
        "features": [
            "Multi-tenant sovereign deployment",
            "Federation across jurisdictions",
            "Real-time national watchlist sync",
            "AI-assisted regulatory reporting",
            "Volume II architecture chapters",
        ],
    },
}


def roadmap_manifest() -> dict[str, Any]:
    phases = []
    for phase in RoadmapPhase:
        data = _PHASES[phase]
        phases.append({
            "phase": phase.value,
            "name_ru": data["name_ru"],
            "timeline": data["timeline"],
            "status": data["status"],
            "rfc_count": len(data["rfcs"]),
            "rfcs": data["rfcs"],
            "features": data["features"],
        })
    complete = sum(1 for p in phases if p["status"] == "complete")
    return {
        "rfc": "RFC-0022",
        "chapter": 15,
        "phase_count": len(RoadmapPhase),
        "phases_complete": complete,
        "phases": phases,
        "current_phase": RoadmapPhase.NATIONAL_SCALE.value,
        "volume_i_status": "complete",
        "principle_ru": "Дорожная карта — MVP → Enterprise → Platform → National Scale",
    }
