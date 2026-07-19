"""Scalpel Console — enriched collector catalog for admin UI."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.infrastructure.circuit_breaker import all_breaker_statuses
from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus
from flowsint_crypto_compliance.osint.collector_health import get_collector_health_snapshot
from flowsint_crypto_compliance.osint_core.scalpel.registry import registry_manifest

_CATEGORY_GROUPS: dict[str, str] = {
    "onchain": "on-chain",
    "sanctions": "sanctions",
    "darknet": "darknet",
    "registry": "registries",
    "username": "osint",
    "abuse": "osint",
    "osint": "osint",
}

_ENV_HINTS: dict[str, str] = {
    "TRONGRID_API_KEY": "TronGrid API key for Tron on-chain data",
    "BITCOINABUSE_API_KEY": "BitcoinAbuse API key for abuse reports",
    "ETHERSCAN_API_KEY": "Etherscan API key for Ethereum explorers",
    "BSCSCAN_API_KEY": "BscScan API key for BSC explorers",
    "OPENSANCTIONS_API_KEY": "OpenSanctions API key (optional, improves rate limits)",
}


def _ui_status(raw_status: str, health_status: str | None, requires_env: list[str]) -> str:
    if raw_status == "disabled":
        return "in_development"
    if raw_status in ("partial", "conditional") or requires_env:
        return "needs_config"
    if health_status in ("error", "timeout", "degraded"):
        return "needs_config"
    if raw_status == "works" and health_status in (None, "ok", "warming"):
        return "live"
    return "needs_config"


def _api_key_hint(collector: dict[str, Any]) -> str | None:
    env_keys = list(collector.get("requires_env") or [])
    if collector.get("id") == "onchain_explorer":
        env_keys.append("TRONGRID_API_KEY")
    if collector.get("id") == "abuse_scam_registry":
        env_keys.append("BITCOINABUSE_API_KEY")
    if collector.get("id") == "sanctions_watchlist":
        env_keys.append("OPENSANCTIONS_API_KEY")
    if not env_keys:
        return None
    hints = [_ENV_HINTS.get(k, k) for k in env_keys]
    return "; ".join(hints)


def _collector_events(collector_id: str, recent: list[dict[str, Any]], *, limit: int = 8) -> tuple[list[dict], list[dict]]:
    history: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    needle = collector_id.lower()
    for ev in recent:
        payload = ev.get("payload") or {}
        text = str(ev.get("text_ru") or "")
        collectors_run = payload.get("collectors_run") or payload.get("collectors") or []
        collector_field = str(payload.get("collector_id") or payload.get("collector") or "")
        matched = (
            collector_field == collector_id
            or needle in text.lower()
            or collector_id in collectors_run
            or any(needle in str(c).lower() for c in collectors_run)
        )
        if not matched:
            continue
        row = {
            "id": ev.get("id"),
            "type": ev.get("type"),
            "ts": ev.get("ts"),
            "text_ru": text,
            "severity": ev.get("severity"),
        }
        history.append(row)
        if ev.get("severity") in ("high", "critical") or "fail" in str(ev.get("type", "")).lower():
            errors.append(row)
    return history[:limit], errors[:5]


async def build_scalpel_console_catalog(
    *,
    tor_available: bool | None = None,
    trongrid_configured: bool | None = None,
) -> dict[str, Any]:
    """Merge registry manifest, health snapshot, metrics, and recent event history."""
    manifest = registry_manifest(
        tor_available=tor_available,
        trongrid_configured=trongrid_configured,
    )
    health = get_collector_health_snapshot()
    health_by_id = {row.get("collector_id"): row for row in health.get("collectors") or []}
    breakers = {b["name"]: b for b in all_breaker_statuses()}

    request_counts: dict[str, int] = {}
    error_counts: dict[str, int] = {}
    try:
        from flowsint_crypto_compliance.platform.v2.icf.monitoring import get_icf_monitoring

        for row in get_icf_monitoring().get_metrics().get("collectors") or []:
            cid = str(row.get("connector_id") or "")
            request_counts[cid] = int(row.get("request_count") or 0)
            error_counts[cid] = int(row.get("error_count") or 0)
    except Exception:
        pass

    recent = get_event_bus().recent(120)
    collectors: list[dict[str, Any]] = []
    for row in manifest:
        cid = row["id"]
        health_row = health_by_id.get(cid) or {}
        breaker = breakers.get(cid) or breakers.get(str(row.get("rate_limit_key") or ""), {})
        call_history, recent_errors = _collector_events(cid, recent)
        req = request_counts.get(cid, breaker.get("failures", 0))
        ui_status = _ui_status(
            str(row.get("status") or "partial"),
            health_row.get("status"),
            list(row.get("requires_env") or []),
        )
        if breaker.get("degraded"):
            ui_status = "needs_config"

        collectors.append(
            {
                **row,
                "name": row.get("name_ru") or cid,
                "description": row.get("status_ru") or row.get("legal_basis_ru") or "",
                "group": _CATEGORY_GROUPS.get(str(row.get("category") or "osint"), "osint"),
                "ui_status": ui_status,
                "last_health_check": health_row.get("checked_at"),
                "health_status": health_row.get("status"),
                "latency_ms": health_row.get("latency_ms"),
                "request_count": req,
                "error_count": error_counts.get(cid, 0),
                "recent_errors": recent_errors,
                "call_history": call_history,
                "api_key_hint": _api_key_hint(row),
                "breaker": {
                    "degraded": bool(breaker.get("degraded")),
                    "failures": int(breaker.get("failures") or 0),
                    "available": breaker.get("available", True),
                },
            }
        )

    groups: dict[str, list[dict[str, Any]]] = {}
    for c in collectors:
        groups.setdefault(str(c["group"]), []).append(c)

    return {
        "collectors": collectors,
        "groups": groups,
        "group_order": ["on-chain", "sanctions", "osint", "darknet", "registries"],
        "health_summary": {
            "status": health.get("status"),
            "collectors_ok": health.get("collectors_ok"),
            "collectors_total": health.get("collectors_total") or len(collectors),
            "checked_at": health.get("checked_at"),
        },
        "tor_available": tor_available,
        "trongrid_configured": trongrid_configured,
    }
