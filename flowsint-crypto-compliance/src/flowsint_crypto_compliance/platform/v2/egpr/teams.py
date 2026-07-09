"""RFC-0022 Ch.13 — platform team model."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import TeamDomain

_TEAMS: list[dict[str, Any]] = [
    {
        "domain": TeamDomain.PLATFORM_CORE,
        "name_ru": "Ядро платформы",
        "size": 4,
        "rfcs": ["RFC-0002", "RFC-0003"],
        "roadmap_stub": "Entity consolidation, package cycle break",
        "kpi_stub": {"velocity": "8 RFC/sprint", "debt_ratio": "< 15%"},
    },
    {
        "domain": TeamDomain.INTELLIGENCE,
        "name_ru": "Интеллектуальное ядро",
        "size": 3,
        "rfcs": ["RFC-0004", "RFC-0006", "RFC-0014"],
        "roadmap_stub": "ICF scheduler hardening",
        "kpi_stub": {"fusion_latency_p99": "< 2s"},
    },
    {
        "domain": TeamDomain.INVESTIGATION,
        "name_ru": "Расследования",
        "size": 3,
        "rfcs": ["RFC-0005", "RFC-0017", "RFC-0018"],
        "roadmap_stub": "Evidence first-class closure",
        "kpi_stub": {"case_resolution_days": "< 5"},
    },
    {
        "domain": TeamDomain.COMPLIANCE,
        "name_ru": "Комплаенс",
        "size": 3,
        "rfcs": ["RFC-0015", "RFC-0016"],
        "roadmap_stub": "CRIF registry expansion",
        "kpi_stub": {"screening_accuracy": "> 99%"},
    },
    {
        "domain": TeamDomain.BLOCKCHAIN,
        "name_ru": "Блокчейн-аналитика",
        "size": 2,
        "rfcs": ["RFC-0012", "RFC-0013"],
        "roadmap_stub": "Multi-chain sync",
        "kpi_stub": {"sync_lag_blocks": "< 10"},
    },
    {
        "domain": TeamDomain.SECURITY,
        "name_ru": "Безопасность",
        "size": 2,
        "rfcs": ["RFC-0009", "RFC-0020"],
        "roadmap_stub": "SDL full closure",
        "kpi_stub": {"incident_mttr_hours": "< 4"},
    },
    {
        "domain": TeamDomain.INFRASTRUCTURE,
        "name_ru": "Инфраструктура",
        "size": 2,
        "rfcs": ["RFC-0021"],
        "roadmap_stub": "Blue/green deployment",
        "kpi_stub": {"uptime_sla": "99.9%"},
    },
    {
        "domain": TeamDomain.API_ECOSYSTEM,
        "name_ru": "API и экосистема",
        "size": 2,
        "rfcs": ["RFC-0019"],
        "roadmap_stub": "Marketplace GA",
        "kpi_stub": {"api_uptime": "99.95%"},
    },
    {
        "domain": TeamDomain.ANALYST_UX,
        "name_ru": "UX аналитика",
        "size": 2,
        "rfcs": ["RFC-0008", "RFC-0010", "RFC-0011"],
        "roadmap_stub": "Command palette v2",
        "kpi_stub": {"task_completion_rate": "> 90%"},
    },
    {
        "domain": TeamDomain.GOVERNANCE,
        "name_ru": "Управление и архитектура",
        "size": 2,
        "rfcs": ["RFC-0000", "RFC-0022"],
        "roadmap_stub": "Volume II planning",
        "kpi_stub": {"rfc_completion_rate": "100% Vol I"},
    },
]


def teams_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 13,
        "team_count": len(_TEAMS),
        "domains": [d.value for d in TeamDomain],
        "teams": [
            {**t, "domain": t["domain"].value if isinstance(t["domain"], TeamDomain) else t["domain"]}
            for t in _TEAMS
        ],
        "principle_ru": "Модель команд — 10 доменов с привязкой к RFC и KPI",
    }
