"""RFC-0012 Ch.6–8, 11–12 — address profiling, clustering, flows."""

from __future__ import annotations

from collections import Counter
from typing import Any

from flowsint_crypto_compliance.chains.base import AddressNeighborhood, OnChainTransfer


def profile_address(neighborhood: AddressNeighborhood) -> dict[str, Any]:
    inbound = neighborhood.inbound
    outbound = neighborhood.outbound
    all_txs = inbound + outbound
    timestamps = [t.timestamp for t in all_txs if t.timestamp]
    assets = Counter(t.asset or "native" for t in all_txs)
    inbound_vol = sum(t.amount or 0 for t in inbound)
    outbound_vol = sum(t.amount or 0 for t in outbound)

    return {
        "address": neighborhood.address,
        "chain": neighborhood.chain.value if hasattr(neighborhood.chain, "value") else str(neighborhood.chain),
        "first_activity": min(timestamps) if timestamps else None,
        "last_activity": max(timestamps) if timestamps else None,
        "inbound_count": len(inbound),
        "outbound_count": len(outbound),
        "inbound_volume": round(inbound_vol, 8),
        "outbound_volume": round(outbound_vol, 8),
        "asset_types": dict(assets),
        "avg_tx_count": round(len(all_txs) / max(1, len(set(timestamps))), 2),
    }


def cluster_counterparties(neighborhood: AddressNeighborhood, *, min_shared: int = 2) -> list[dict[str, Any]]:
    """Ch.7 — heuristic clustering by shared interaction patterns."""
    peers: Counter[str] = Counter()
    for tx in neighborhood.inbound + neighborhood.outbound:
        peer = tx.source if tx.target == neighborhood.address else tx.target
        if peer and peer != neighborhood.address:
            peers[peer] += 1
    clusters = []
    for peer, count in peers.most_common(20):
        confidence = min(0.95, 0.3 + count * 0.15)
        clusters.append(
            {
                "cluster_id": f"peer:{peer[:16]}",
                "method": "shared_counterparties",
                "members": [neighborhood.address, peer],
                "confidence": round(confidence, 2),
                "evidence_ru": f"Общих взаимодействий: {count}",
                "analyst_verifiable": True,
            }
        )
        if count < min_shared:
            break
    return clusters


def build_flow_graph(neighborhood: AddressNeighborhood, *, depth: int = 1) -> dict[str, Any]:
    """Ch.8, 12 — inbound/outbound flow graph."""
    nodes = {neighborhood.address: {"kind": "address", "label": neighborhood.address[:12]}}
    edges: list[dict[str, Any]] = []

    for tx in neighborhood.inbound:
        nodes[tx.source] = {"kind": "address", "label": tx.source[:12]}
        edges.append(
            {
                "from": tx.source,
                "to": neighborhood.address,
                "tx_hash": tx.tx_hash,
                "amount": tx.amount,
                "asset": tx.asset,
                "direction": "inbound",
            }
        )
    for tx in neighborhood.outbound:
        nodes[tx.target] = {"kind": "address", "label": tx.target[:12]}
        edges.append(
            {
                "from": neighborhood.address,
                "to": tx.target,
                "tx_hash": tx.tx_hash,
                "amount": tx.amount,
                "asset": tx.asset,
                "direction": "outbound",
            }
        )

    return {
        "nodes": [{"id": k, **v} for k, v in nodes.items()],
        "edges": edges,
        "depth": depth,
        "inbound_flows": len(neighborhood.inbound),
        "outbound_flows": len(neighborhood.outbound),
    }


def behavior_profile(profile: dict[str, Any], neighborhood: AddressNeighborhood) -> dict[str, Any]:
    """Ch.11 — behavioral profile from on-chain activity."""
    total = profile["inbound_count"] + profile["outbound_count"]
    ratio = profile["inbound_volume"] / max(profile["outbound_volume"], 1e-9)
    anomalies: list[str] = []
    if ratio > 10:
        anomalies.append("high_inbound_skew")
    if total > 100:
        anomalies.append("high_frequency")
    return {
        "typical_intervals": "unknown_without_timestamps" if not profile.get("first_activity") else "computed",
        "avg_amount": round((profile["inbound_volume"] + profile["outbound_volume"]) / max(total, 1), 8),
        "inbound_outbound_ratio": round(ratio, 2),
        "counterparty_count": len(
            {t.source for t in neighborhood.inbound} | {t.target for t in neighborhood.outbound}
        ),
        "anomalies": anomalies,
    }


def normalize_transfers(neighborhood: AddressNeighborhood, chain_key: str) -> list[dict[str, Any]]:
    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.canonical_model import transfer_to_canonical

    out: list[dict[str, Any]] = []
    for tx in neighborhood.inbound + neighborhood.outbound:
        out.append(
            transfer_to_canonical(
                chain=chain_key,
                tx_hash=tx.tx_hash,
                source=tx.source,
                target=tx.target,
                asset=tx.asset,
                amount=tx.amount,
                timestamp=tx.timestamp,
            )
        )
    return out


def enrich_neighborhood_from_index(
    neighborhood: AddressNeighborhood,
    chain_key: str,
    address: str,
) -> tuple[AddressNeighborhood, str, int]:
    """Merge local block sync index into neighborhood (RFC-0013)."""
    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.sync_store import get_block_sync_store

    indexed = get_block_sync_store().get_transfers_for_address(chain_key, address)
    if not indexed:
        return neighborhood, "adapter", 0

    norm_addr = address.lower() if chain_key in ("eth", "bsc", "polygon") else address.strip()
    inbound = list(neighborhood.inbound)
    outbound = list(neighborhood.outbound)
    added = 0
    for tr in indexed:
        ot = OnChainTransfer(
            chain=neighborhood.chain,
            tx_hash=str(tr.get("tx_hash", "")),
            source=str(tr.get("source", "")),
            target=str(tr.get("target", "")),
            asset=tr.get("asset"),
            amount=tr.get("amount"),
            timestamp=tr.get("timestamp"),
        )
        tgt = (tr.get("target") or "").lower() if chain_key in ("eth", "bsc", "polygon") else tr.get("target")
        if tgt == norm_addr:
            inbound.append(ot)
            added += 1
        src = (tr.get("source") or "").lower() if chain_key in ("eth", "bsc", "polygon") else tr.get("source")
        if src == norm_addr:
            outbound.append(ot)
            added += 1

    merged = AddressNeighborhood(
        address=neighborhood.address,
        chain=neighborhood.chain,
        inbound=inbound,
        outbound=outbound,
    )
    source = "merged" if added else "adapter"
    return merged, source, added
