"""RFC-0020 Ch.15 — threat register per component."""

from __future__ import annotations

from typing import Any


_THREATS: list[dict[str, Any]] = [
    {
        "id": "T-ESA-001",
        "component": "flowsint-api",
        "threat": "Credential stuffing / brute force",
        "stride": "Spoofing",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "MFA, rate limiting, account lockout",
        "status": "mitigated",
    },
    {
        "id": "T-ESA-002",
        "component": "platform/v2/gateway",
        "threat": "Privilege escalation via JWT manipulation",
        "stride": "Elevation of Privilege",
        "likelihood": "low",
        "impact": "critical",
        "mitigation": "JWT signature validation, RBAC harmonization RFC-0009",
        "status": "mitigated",
    },
    {
        "id": "T-ESA-003",
        "component": "eccf",
        "threat": "Evidence tampering",
        "stride": "Tampering",
        "likelihood": "low",
        "impact": "critical",
        "mitigation": "Immutable audit, content hash, forbidden mutations",
        "status": "mitigated",
    },
    {
        "id": "T-ESA-004",
        "component": "connectors",
        "threat": "SSRF via connector query",
        "stride": "Information Disclosure",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Host allowlist, vault secrets, TLS verify",
        "status": "partial",
    },
    {
        "id": "T-ESA-005",
        "component": "knowledge_graph",
        "threat": "Cross-tenant data leak",
        "stride": "Information Disclosure",
        "likelihood": "medium",
        "impact": "critical",
        "mitigation": "ABAC tenant_id, row-level security (planned)",
        "status": "partial",
    },
    {
        "id": "T-ESA-006",
        "component": "eia",
        "threat": "Prompt injection / data exfiltration via AI",
        "stride": "Information Disclosure",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Context filtering, classification rules, audit",
        "status": "partial",
    },
    {
        "id": "T-ESA-007",
        "component": "celery_workers",
        "threat": "Malicious task injection",
        "stride": "Tampering",
        "likelihood": "low",
        "impact": "high",
        "mitigation": "Broker auth, task signing, queue isolation",
        "status": "partial",
    },
    {
        "id": "T-ESA-008",
        "component": "service_mesh",
        "threat": "Lateral movement without mTLS",
        "stride": "Elevation of Privilege",
        "likelihood": "medium",
        "impact": "high",
        "mitigation": "Istio mTLS STRICT (planned TD-ESA-3)",
        "status": "open",
    },
]


def threat_model_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 15,
        "methodology": "STRIDE",
        "threat_count": len(_THREATS),
        "threats": list(_THREATS),
        "components_covered": sorted({t["component"] for t in _THREATS}),
        "status_summary": {
            "mitigated": sum(1 for t in _THREATS if t["status"] == "mitigated"),
            "partial": sum(1 for t in _THREATS if t["status"] == "partial"),
            "open": sum(1 for t in _THREATS if t["status"] == "open"),
        },
        "principle_ru": "Реестр угроз по компонентам — STRIDE с митигациями и статусом",
    }


def get_threats_for_component(component: str) -> list[dict[str, Any]]:
    return [t for t in _THREATS if t["component"] == component]
