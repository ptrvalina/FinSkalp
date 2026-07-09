"""RFC-0022 Ch.9 — requirements registry linked to RFCs."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import RequirementKind

_REQUIREMENTS: list[dict[str, Any]] = [
    {"id": "REQ-0001", "kind": RequirementKind.FUNCTIONAL, "title": "Entity-first knowledge graph", "rfc": "RFC-0003", "status": "implemented"},
    {"id": "REQ-0002", "kind": RequirementKind.FUNCTIONAL, "title": "Multihop intelligence fusion", "rfc": "RFC-0004", "status": "implemented"},
    {"id": "REQ-0003", "kind": RequirementKind.FUNCTIONAL, "title": "Investigation workspace with evidence", "rfc": "RFC-0005", "status": "implemented"},
    {"id": "REQ-0004", "kind": RequirementKind.SECURITY, "title": "Harmonized RBAC across domains", "rfc": "RFC-0009", "status": "implemented"},
    {"id": "REQ-0005", "kind": RequirementKind.FUNCTIONAL, "title": "Blockchain address analysis", "rfc": "RFC-0012", "status": "implemented"},
    {"id": "REQ-0006", "kind": RequirementKind.COMPLIANCE, "title": "Sanctions screening", "rfc": "RFC-0015", "status": "implemented"},
    {"id": "REQ-0007", "kind": RequirementKind.FUNCTIONAL, "title": "Risk assessment engine", "rfc": "RFC-0016", "status": "implemented"},
    {"id": "REQ-0008", "kind": RequirementKind.COMPLIANCE, "title": "Chain of custody for evidence", "rfc": "RFC-0017", "status": "implemented"},
    {"id": "REQ-0009", "kind": RequirementKind.FUNCTIONAL, "title": "Explainable AI assistant", "rfc": "RFC-0018", "status": "implemented"},
    {"id": "REQ-0010", "kind": RequirementKind.NON_FUNCTIONAL, "title": "REST API catalog with SDKs", "rfc": "RFC-0019", "status": "implemented"},
    {"id": "REQ-0011", "kind": RequirementKind.SECURITY, "title": "Zero Trust security architecture", "rfc": "RFC-0020", "status": "implemented"},
    {"id": "REQ-0012", "kind": RequirementKind.OPERATIONAL, "title": "Observability three pillars", "rfc": "RFC-0021", "status": "implemented"},
    {"id": "REQ-0013", "kind": RequirementKind.NON_FUNCTIONAL, "title": "Enterprise governance framework", "rfc": "RFC-0022", "status": "implemented"},
    {"id": "REQ-0014", "kind": RequirementKind.OPERATIONAL, "title": "Daily maturity snapshot", "rfc": "RFC-0022", "status": "implemented"},
]


def list_requirements(*, kind: str | None = None, rfc: str | None = None) -> list[dict[str, Any]]:
    items = list(_REQUIREMENTS)
    if kind:
        items = [r for r in items if r["kind"].value == kind or r["kind"] == kind]
    if rfc:
        items = [r for r in items if r["rfc"] == rfc.upper()]
    return [
        {
            **r,
            "kind": r["kind"].value if isinstance(r["kind"], RequirementKind) else r["kind"],
        }
        for r in items
    ]


def requirements_manifest() -> dict[str, Any]:
    items = list_requirements()
    by_kind = {k.value: sum(1 for r in items if r["kind"] == k.value) for k in RequirementKind}
    return {
        "rfc": "RFC-0022",
        "chapter": 9,
        "count": len(items),
        "by_kind": by_kind,
        "requirements": items,
        "principle_ru": "Реестр требований — связь с RFC и статусом реализации",
    }
