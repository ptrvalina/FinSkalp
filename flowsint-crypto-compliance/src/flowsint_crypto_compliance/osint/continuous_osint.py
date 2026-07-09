"""
Continuous OSINT — periodic rescan of KYT watchlist addresses.

New findings publish to compliance event bus (SLA_BREACH / watchlist pattern).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.demo.live_kyt_scanner import kyt_watchlist, list_kyt_watch_addresses
from flowsint_crypto_compliance.osint.fusion_confidence import fuse_mention_hits
from flowsint_crypto_compliance.osint.institutional_memory import index_findings_from_scalpel
from flowsint_types.fiat_crypto import Chain

_last_fingerprints: dict[str, str] = {}
_rescan_interval_hours = float(os.getenv("FINSKALP_OSINT_RESCAN_HOURS", "24"))


def osint_rescan_interval_hours() -> float:
    return _rescan_interval_hours


def _mention_fingerprint(mentions: list[dict[str, Any]]) -> str:
    import hashlib

    keys = sorted(
        f"{m.get('source_type')}:{m.get('source_name')}:{m.get('title_ru', '')[:40]}"
        for m in mentions
    )
    return hashlib.sha256("|".join(keys).encode()).hexdigest()[:16]


def publish_osint_watchlist_alert(
    *,
    address: str,
    chain: str,
    new_mentions: list[dict[str, Any]],
    fusion: dict[str, Any],
) -> None:
    try:
        from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

        get_event_bus().publish(
            "osint_watchlist_finding",
            payload={
                "address": address,
                "chain": chain,
                "new_mentions_count": len(new_mentions),
                "fusion": fusion,
                "mentions_sample": new_mentions[:3],
            },
            severity="high",
            text_ru=(
                f"Новые OSINT-сигналы · watchlist · {chain.upper()} · "
                f"{address[:14]}… · {len(new_mentions)} находок · "
                f"уверенность {fusion.get('composite_pct', 0):.0f}%"
            ),
        )
    except Exception:
        pass


async def rescan_watch_address(
    address: str,
    chain: str,
    *,
    tenant_id: str | None = None,
    case_ref: str | None = None,
) -> dict[str, Any]:
    """Run Scalpel on one watchlist address; alert if fingerprint changed."""
    from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine

    key = f"{chain}:{address}"
    engine = ScalpelEngine(timeout=10.0)
    try:
        ch = Chain(chain) if chain in {c.value for c in Chain} else Chain.TRON
    except Exception:
        ch = Chain.TRON

    result = await engine.collect(address, ch, depth=1)
    mentions = [m.to_dict() for m in result.mentions]
    fp = _mention_fingerprint(mentions)
    prev = _last_fingerprints.get(key)
    _last_fingerprints[key] = fp

    fusion = fuse_mention_hits(result.mentions).to_dict()
    out: dict[str, Any] = {
        "address": address,
        "chain": chain,
        "mentions_count": len(mentions),
        "fingerprint": fp,
        "changed": prev is not None and prev != fp,
        "fusion": fusion,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }

    if tenant_id and case_ref:
        index_findings_from_scalpel(
            tenant_id=tenant_id,
            case_id=str(uuid.uuid4()),
            case_ref=case_ref,
            extracted_entities=result.extracted_entities,
            mentions=mentions,
        )

    if out["changed"] and mentions:
        publish_osint_watchlist_alert(
            address=address,
            chain=chain,
            new_mentions=mentions,
            fusion=fusion,
        )
        out["alert_published"] = True
    return out


async def run_continuous_osint_rescan(
    *,
    tenant_id: str | None = None,
    max_addresses: int = 8,
) -> dict[str, Any]:
    """Rescan all KYT watchlist addresses (bounded)."""
    entries = kyt_watchlist()[:max_addresses]
    if not entries:
        return {"status": "empty", "watchlist": list_kyt_watch_addresses()}

    results = await asyncio.gather(
        *[
            rescan_watch_address(addr, chain, tenant_id=tenant_id, case_ref=f"WATCH-{addr[:8]}")
            for addr, chain in entries
        ],
        return_exceptions=True,
    )
    changed = sum(
        1 for r in results if isinstance(r, dict) and r.get("changed")
    )
    return {
        "status": "ok",
        "scanned": len(entries),
        "changed": changed,
        "interval_hours": _rescan_interval_hours,
        "results": [r for r in results if isinstance(r, dict)],
    }
