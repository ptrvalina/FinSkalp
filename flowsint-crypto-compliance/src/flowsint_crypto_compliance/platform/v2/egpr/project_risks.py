"""RFC-0022 Ch.12 — project risk register."""

from __future__ import annotations

from typing import Any

_RISKS: list[dict[str, Any]] = [
    {
        "id": "RISK-001",
        "title": "Package cycle blocks Plugin First",
        "severity": "high",
        "probability": "certain",
        "mitigation": "TD-C4 — extract compliance as plugin",
        "owner": "platform_core",
        "status": "open",
    },
    {
        "id": "RISK-002",
        "title": "Evidence not fully first-class in DB",
        "severity": "high",
        "probability": "likely",
        "mitigation": "RFC-0017 ECCF + entity consolidation",
        "owner": "investigation",
        "status": "mitigating",
    },
    {
        "id": "RISK-003",
        "title": "Dual API gateway security drift",
        "severity": "medium",
        "probability": "possible",
        "mitigation": "Consolidate on platform/v2/routes.py",
        "owner": "api_ecosystem",
        "status": "mitigating",
    },
    {
        "id": "RISK-004",
        "title": "SAST/pen-test gaps in SDLC",
        "severity": "medium",
        "probability": "possible",
        "mitigation": "RFC-0020 SDL checklist closure",
        "owner": "security",
        "status": "open",
    },
    {
        "id": "RISK-005",
        "title": "Blue/green deployment not enabled",
        "severity": "low",
        "probability": "unlikely",
        "mitigation": "TD-IDOO-1 — IDOO versioning strategies",
        "owner": "infrastructure",
        "status": "accepted",
    },
]


def project_risks_manifest() -> dict[str, Any]:
    open_risks = sum(1 for r in _RISKS if r["status"] in ("open", "mitigating"))
    return {
        "rfc": "RFC-0022",
        "chapter": 12,
        "count": len(_RISKS),
        "open_count": open_risks,
        "risks": _RISKS,
        "principle_ru": "Реестр рисков проекта — severity, вероятность и план митигации",
    }
