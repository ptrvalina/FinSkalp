"""Live KYT pattern scan — real on-chain screening, no canned scenarios."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from threading import Lock

from flowsint_crypto_compliance.chains import get_chain_adapter
from flowsint_crypto_compliance.demo.alert_registry import format_monitor_alert_code
from flowsint_crypto_compliance.demo.combat_mode import combat_seed_address, is_combat_mode
from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache
from flowsint_crypto_compliance.demo.live_feed import publish_screening_feed
from flowsint_crypto_compliance.demo.live_ops_metrics import get_live_ops_metrics
from flowsint_crypto_compliance.demo.operations_center import ComplianceAlert
from flowsint_crypto_compliance.osint_core.multihop_fusion import MultiHopFusionEngine, is_live_address
from flowsint_crypto_compliance.services.wallet_screening import (
    WalletScreeningRequest,
    WalletScreeningService,
    infer_chain,
)
from flowsint_types.fiat_crypto import Chain

_runtime_watchlist: set[str] = set()
_watchlist_lock = Lock()
_last_tx_fingerprint: dict[str, str] = {}


def add_kyt_watch_address(address: str) -> tuple[str, Chain]:
    """Add address to in-session KYT watchlist (merged with env list)."""
    addr = address.strip()
    if not addr:
        raise ValueError("address required")
    chain = infer_chain(addr)
    with _watchlist_lock:
        _runtime_watchlist.add(addr)
    return addr, chain


def list_kyt_watch_addresses() -> list[str]:
    with _watchlist_lock:
        runtime = sorted(_runtime_watchlist)
    env_addrs = [p.strip() for p in os.getenv("FINSKALP_KYT_WATCHLIST", "").split(",") if p.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for a in runtime + env_addrs:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            out.append(a)
    seed = combat_seed_address()
    if seed and seed[0].lower() not in seen:
        out.insert(0, seed[0])
    return out


def _parse_watch_entry(raw: str) -> tuple[str, str] | None:
    """Return (address, chain_slug). Supports `polygon:0x…` prefix for non-ETH EVM."""
    entry = raw.strip()
    if not entry:
        return None
    if ":" in entry and not entry.startswith("0x"):
        chain_slug, addr = entry.split(":", 1)
        chain_slug = chain_slug.lower().strip()
        if chain_slug in ("polygon", "bsc", "eth", "tron", "btc", "solana"):
            return addr.strip(), chain_slug
    try:
        chain = infer_chain(entry)
        return entry, chain.value
    except ValueError:
        return None


def kyt_watchlist() -> list[tuple[str, str]]:
    """List of (address, chain_slug) for live monitoring."""
    out: list[tuple[str, str]] = []
    for raw in list_kyt_watch_addresses():
        parsed = _parse_watch_entry(raw)
        if not parsed:
            continue
        addr, chain = parsed
        if is_live_address(addr, chain) or chain in ("polygon", "bsc", "solana"):
            out.append((addr, chain))
    return out


async def _latest_tx_fingerprint(address: str, chain: str) -> str | None:
    """Return fingerprint of newest on-chain tx for watchlist change detection."""
    try:
        if chain == "tron":
            from flowsint_crypto_compliance.osint_core.live_collectors import collect_tron_trc20_transfers

            data = await collect_tron_trc20_transfers(address, max_transfers=3)
            transfers = data.get("transfers") or []
        elif chain == "btc":
            from flowsint_crypto_compliance.osint_core.live_collectors import collect_btc_chain

            data = await collect_btc_chain(address)
            transfers = data.get("transfers") or []
        elif chain == "polygon":
            from flowsint_crypto_compliance.osint_core.live_collectors import collect_polygon_chain

            data = await collect_polygon_chain(address)
            transfers = data.get("transfers") or []
        elif chain == "solana":
            from flowsint_crypto_compliance.osint_core.live_collectors import collect_solana_chain

            data = await collect_solana_chain(address)
            transfers = data.get("transfers") or []
        elif chain == "bsc":
            from flowsint_crypto_compliance.osint_core.live_collectors import collect_bsc_chain

            data = await collect_bsc_chain(address)
            transfers = data.get("transfers") or []
        elif chain == "eth":
            from flowsint_crypto_compliance.osint_core.live_collectors import collect_eth_chain

            data = await collect_eth_chain(address)
            transfers = data.get("transfers") or []
        else:
            return None
        if not transfers:
            return None
        latest = max(transfers, key=lambda t: int(t.get("timestamp") or 0))
        return str(latest.get("tx_hash") or latest.get("timestamp") or "")
    except Exception:
        return None


def publish_watchlist_tx_feed(*, address: str, chain: str, tx_hash: str) -> None:
    """Push SSE event when a watched address has new on-chain activity."""
    try:
        from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

        get_event_bus().publish(
            "watchlist_tx",
            payload={"address": address, "chain": chain, "tx_hash": tx_hash},
            severity="high",
            text_ru=f"Новая tx · watchlist · {chain.upper()} · {address[:14]}… · {tx_hash[:16]}…",
        )
    except Exception:
        pass


async def run_live_kyt_scan(*, seen: set[str]) -> list[ComplianceAlert]:
    if not is_combat_mode():
        return []

    addresses = kyt_watchlist()
    if not addresses:
        return []

    found: list[ComplianceAlert] = []
    metrics = get_live_ops_metrics()
    cache = get_demo_label_cache()

    for address, chain_slug in addresses:
        key = f"{chain_slug}:{address}"
        already_alerted = key in seen

        # New-tx detection for watchlist — SSE even before risk threshold
        fp = await _latest_tx_fingerprint(address, chain_slug)
        if fp:
            prev = _last_tx_fingerprint.get(key)
            if prev and prev != fp:
                publish_watchlist_tx_feed(address=address, chain=chain_slug, tx_hash=fp)
            _last_tx_fingerprint[key] = fp

        chain_enum: Chain | None = None
        try:
            chain_enum = infer_chain(address) if chain_slug not in ("polygon", "bsc") else Chain.ETH
        except ValueError:
            continue

        adapters = {chain_enum: get_chain_adapter(chain_enum)} if chain_enum else {}
        if not adapters:
            continue
        svc = WalletScreeningService(chain_adapters=adapters, label_cache=cache)
        try:
            screening = await svc.screen(
                WalletScreeningRequest(address=address, chain=chain_enum, depth=1, limit=40)
            )
        except Exception:
            if not already_alerted:
                seen.add(key)
            continue

        risk = float(screening.risk_score)
        metrics.record_screen(risk_score=risk, address=address)
        publish_screening_feed(
            address=address,
            chain=chain_slug,
            risk_score=risk,
            summary_ru=screening.summary_ru,
        )

        hop_nodes = 0
        hop_edges = 0
        corridor = False
        if is_live_address(address, chain_slug):
            try:
                graph = await asyncio.wait_for(
                    MultiHopFusionEngine(max_hops=2).explore(address, chain_slug),
                    timeout=20.0,
                )
                hop_nodes = len(graph.nodes)
                hop_edges = len(graph.edges)
                corridor = graph.corridor_flagged
            except Exception:
                pass

        if already_alerted:
            continue

        seen.add(key)
        if risk < 55 and not corridor:
            continue

        priority = "critical" if risk >= 80 or corridor else "high" if risk >= 65 else "medium"
        findings = screening.findings or []
        f0 = findings[0] if findings else None
        top = (
            (f0.get("title_ru") if isinstance(f0, dict) else getattr(f0, "title_ru", None))
            if f0
            else "Live KYT · on-chain аномалия"
        )
        alert = ComplianceAlert(
            id=f"alert-{uuid.uuid4().hex[:10]}",
            alert_code=format_monitor_alert_code(f"live-{key[-8:]}"),
            source="pattern_monitor",
            status="new",
            priority=priority,  # type: ignore[arg-type]
            title_ru=f"KYT live · {top}",
            official_title_ru=(
                f"Live KYT: риск {risk:.0f}/100 · {chain_slug.upper()} · "
                f"{hop_nodes} узлов · {hop_edges} рёбер"
            ),
            summary_ru=screening.summary_ru or f"On-chain скрининг {address[:16]}…",
            scenario_id="live_kyt",
            typology_code="KYT-LIVE",
            typology_name_ru="Live on-chain KYT",
            legal_signs_ru=[
                "п. 1 ч. 2 ст. 6 115-ФЗ — операции с цифровыми финансовыми активами",
                "Live TronGrid / Blockstream / Etherscan · FinSkalp screening",
            ],
            instruments=["ИЦ-02", "ИЦ-03", "ИЦ-07"],
            received_at=datetime.now(timezone.utc).isoformat(),
            region="RU",
            pattern_id=f"live_kyt:{key}",
            pattern_indicators=[
                f"risk_score={risk:.0f}",
                f"findings={len(findings)}",
                f"graph_nodes={hop_nodes}",
                f"corridor={'yes' if corridor else 'no'}",
            ],
            case_ref=f"LIVE-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}",
            subject_category_ru="Live KYT · кошелёк под мониторингом",
            crypto_address=address,
            crypto_chain=chain_slug,
        )
        found.append(alert)
        metrics.record_kyt_alert()
        publish_screening_feed(
            address=address,
            chain=chain_slug,
            risk_score=risk,
            summary_ru=alert.summary_ru,
            alert_id=alert.id,
        )

    return found
