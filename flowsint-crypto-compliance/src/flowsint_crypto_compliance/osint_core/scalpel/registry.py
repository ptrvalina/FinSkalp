"""Реестр легальных коллекторов OSINT Scalpel и mapping на Celery tasks."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.scalpel.collectors.abuse_scam_registry import (
    AbuseScamRegistryCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.court_enforcement import (
    CourtEnforcementCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.clearnet_intel import (
    ClearnetIntelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.darknet_tor import (
    DarknetTorCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.darknet_index import (
    DarknetIndexCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.onchain_explorer import (
    OnchainExplorerCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.reverse_whois_dns import (
    ReverseWhoisDnsCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.sanctions_watchlist import (
    SanctionsWatchlistCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.username_probe import (
    UsernameProbeCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.username_social import (
    UsernameSocialCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.collectors.vasp_registry import (
    VaspRegistryCollector,
)

SCALPEL_COLLECTORS = [
    OnchainExplorerCollector,
    SanctionsWatchlistCollector,
    UsernameSocialCollector,
    UsernameProbeCollector,
    AbuseScamRegistryCollector,
    DarknetIndexCollector,
    DarknetTorCollector,
    ClearnetIntelCollector,
    VaspRegistryCollector,
    CourtEnforcementCollector,
    ReverseWhoisDnsCollector,
]

CELERY_COLLECTOR_TASKS: dict[str, str] = {
    "onchain_explorer": "scalpel_collect_onchain",
    "sanctions_watchlist": "scalpel_collect_sanctions",
    "username_social": "scalpel_collect_username",
    "username_probe": "scalpel_collect_username_probe",
    "abuse_scam_registry": "scalpel_collect_abuse",
    "darknet_index": "scalpel_collect_darknet",
    "darknet_tor": "scalpel_collect_darknet_tor",
    "clearnet_intel": "scalpel_collect_clearnet",
    "vasp_registry": "scalpel_collect_vasp",
    "court_enforcement": "scalpel_collect_court",
    "reverse_whois_dns": "scalpel_collect_dns",
}


# UI / health metadata per checkbox in «Центр OSINT»
_COLLECTOR_UI: dict[str, dict[str, Any]] = {
    "onchain_explorer": {
        "status": "works",
        "status_ru": "TronGrid / mempool · live on-chain",
        "default_checked": True,
    },
    "sanctions_watchlist": {
        "status": "works",
        "status_ru": "OFAC SDN + OpenSanctions API",
        "default_checked": True,
    },
    "username_social": {
        "status": "works",
        "status_ru": "Maigret live · ФИО→handles / usernames",
        "default_checked": True,
    },
    "username_probe": {
        "status": "works",
        "status_ru": "Sherlock-паттерн · быстрый probe публичных профилей",
        "default_checked": True,
    },
    "abuse_scam_registry": {
        "status": "partial",
        "status_ru": "Chainabuse + BitcoinAbuse (BTC) + локальный scam-корпус",
        "default_checked": True,
    },
    "darknet_index": {
        "status": "partial",
        "status_ru": "Ahmia clearnet + локальный darknet-корпус",
        "default_checked": True,
        "hot": True,
    },
    "darknet_tor": {
        "status": "partial",
        "status_ru": "Ahmia live · clearnet + Tor SOCKS (авто 9050)",
        "status_ru_disabled": "Ahmia clearnet · Tor SOCKS не обнаружен",
        "default_checked": True,
        "requires_env": [],
        "hot": True,
    },
    "clearnet_intel": {
        "status": "works",
        "status_ru": "Clearnet dork · публичные индексы",
        "default_checked": True,
    },
    "vasp_registry": {
        "status": "works",
        "status_ru": "Реестр VASP СНГ · 115-ФЗ + match по имени/кошельку",
        "default_checked": True,
    },
    "court_enforcement": {
        "status": "works",
        "status_ru": "DOJ/Europol seizure store",
        "default_checked": True,
    },
    "reverse_whois_dns": {
        "status": "works",
        "status_ru": "RDAP/DNS · домены из URL/текста wave-0 (depth≥2 hop-1)",
        "default_checked": True,
    },
}


def _category_for(cls: type) -> str:
    if "darknet" in cls.collector_id or cls.collector_id == "darknet_tor":
        return "darknet"
    if cls.collector_id == "onchain_explorer":
        return "onchain"
    if cls.collector_id == "sanctions_watchlist":
        return "sanctions"
    if cls.collector_id in {"username_social", "username_probe"}:
        return "username"
    if cls.collector_id == "abuse_scam_registry":
        return "abuse"
    if cls.collector_id == "vasp_registry":
        return "registry"
    return "osint"


def registry_manifest(
    *,
    tor_available: bool | None = None,
    trongrid_configured: bool | None = None,
) -> list[dict[str, Any]]:
    """Collector list for OSINT Center checkboxes with honest availability."""
    out: list[dict[str, Any]] = []
    for cls in SCALPEL_COLLECTORS:
        meta = dict(_COLLECTOR_UI.get(cls.collector_id, {}))
        cid = cls.collector_id
        selectable = True
        effective_status = meta.get("status", "partial")

        if cid == "darknet_tor" and tor_available is not None:
            if tor_available:
                meta["status_ru"] = "Ahmia live · Tor SOCKS активен"
                effective_status = "works"
            else:
                meta["status_ru"] = "Ahmia clearnet live · Tor SOCKS не обнаружен (9050)"
                effective_status = "partial"
            selectable = True

        if effective_status == "conditional" and tor_available is not None:
            if not tor_available:
                effective_status = "disabled"
                selectable = False
                meta["status_ru"] = meta.get("status_ru_disabled", meta.get("status_ru", ""))

        if cid == "onchain_explorer" and trongrid_configured is False:
            effective_status = "partial"
            meta["status_ru"] = "TronGrid без API key — деградированный режим"

        out.append(
            {
                "id": cid,
                "name_ru": cls.name_ru,
                "legal_basis_ru": getattr(cls, "legal_basis_ru", ""),
                "celery_task": CELERY_COLLECTOR_TASKS.get(cid),
                "rate_limit_key": cid,
                "routes": list(getattr(cls, "routes", ("clearnet",))),
                "category": _category_for(cls),
                "status": effective_status,
                "status_ru": meta.get("status_ru", ""),
                "selectable": selectable,
                "default_checked": bool(meta.get("default_checked", True)) and selectable,
                "hot": bool(meta.get("hot")),
                "requires_context": meta.get("requires_context") or [],
                "requires_env": meta.get("requires_env") or [],
            }
        )
    return out
