"""Convert OSINT evidence graph → force-graph payload for demo UI."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.detection.findings import IllegalFlowFinding
from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind


def onchain_summary_to_fusion_graph(
    address: str,
    chain: str,
    onchain: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build force-graph payload from live wallet screening / TronGrid sample."""
    if not onchain:
        return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}

    chain = (chain or onchain.get("chain") or "tron").lower()
    root_id = f"{chain}:{address}"
    nodes: dict[str, dict[str, Any]] = {
        root_id: {
            "id": root_id,
            "address": address,
            "chain": chain,
            "hop": 0,
            "role": "root",
            "label": _short_label(address),
        }
    }
    edges: list[dict[str, Any]] = []
    seen_edges: set[str] = set()

    def _node(addr: str, hop: int = 1) -> str:
        nid = f"{chain}:{addr}"
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "address": addr,
                "chain": chain,
                "hop": hop,
                "role": "counterparty",
                "label": _short_label(addr),
            }
        return nid

    for tx in onchain.get("sample_tx") or []:
        cp = (tx.get("counterparty") or "").strip()
        if not cp or cp == address:
            continue
        cp_id = _node(cp, 1)
        if tx.get("direction") == "in":
            frm, to = cp_id, root_id
        else:
            frm, to = root_id, cp_id
        eid = f"{frm}->{to}:{tx.get('hash', '')}"
        if eid in seen_edges:
            continue
        seen_edges.add(eid)
        edges.append(
            {
                "id": eid,
                "from": frm,
                "to": to,
                "amount": tx.get("amount"),
                "asset": tx.get("asset"),
                "tx_hash": tx.get("hash"),
                "rel_type": "SENT_TO",
            }
        )

    for cp in onchain.get("counterparty_addresses") or []:
        cp = str(cp).strip()
        if cp and cp != address:
            _node(cp, 1)

    node_list = list(nodes.values())
    return {
        "nodes": node_list,
        "edges": edges,
        "risk_annotations": [],
        "node_count": len(node_list),
        "edge_count": len(edges),
        "corridor_flagged": False,
        "source": "onchain_screening",
    }


def merge_fusion_graphs(*graphs: dict[str, Any] | None) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    for g in graphs:
        if not g:
            continue
        for n in g.get("nodes") or []:
            nid = n.get("id")
            if nid:
                nodes[nid] = n
        for e in g.get("edges") or []:
            if e not in edges:
                edges.append(e)
        annotations.extend(g.get("risk_annotations") or [])
    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "risk_annotations": annotations,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "corridor_flagged": any(g.get("corridor_flagged") for g in graphs if g),
    }


def ensure_investigation_graph(
    *,
    address: str,
    chain: str,
    live_fusion: dict[str, Any] | None,
    onchain: dict[str, Any] | None,
    evidence_graph_viz: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prefer live multi-hop graph; fall back to on-chain edges so UI always shows links."""
    live = live_fusion or {}
    if len(live.get("edges") or []) >= 1:
        return live
    onchain_g = onchain_summary_to_fusion_graph(address, chain, onchain)
    if len(onchain_g.get("edges") or []) >= 1:
        if live.get("nodes"):
            merged = merge_fusion_graphs(live, onchain_g)
            merged["source"] = "live_fusion+onchain"
            return merged
        return onchain_g
    if evidence_graph_viz and evidence_graph_viz.get("nodes"):
        return evidence_graph_viz
    result = live if live.get("nodes") else onchain_g
    if result.get("nodes"):
        from flowsint_crypto_compliance.reporting.graph_top_tier import enrich_investigation_graph

        return enrich_investigation_graph(result, root_address=address)
    return result


def _short_label(addr: str) -> str:
    return addr if len(addr) <= 14 else f"{addr[:6]}…{addr[-4:]}"


def evidence_graph_to_viz(
    graph: EvidenceGraph,
    findings: list[IllegalFlowFinding] | None = None,
) -> dict[str, Any]:
    flagged_addrs: set[str] = set()
    for finding in findings or []:
        for addr in finding.addresses or []:
            flagged_addrs.add(str(addr).lower())

    risk_annotations: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    hop_map: dict[str, int] = {}

    for node in graph.nodes:
        payload = node.payload or {}
        addr = str(payload.get("address") or node.primary_key)
        chain = str(payload.get("chain") or _chain_from_key(node.primary_key))
        hop = int(payload.get("hop", hop_map.get(node.node_id, 0)))
        hop_map[node.node_id] = hop
        flagged = addr.lower() in flagged_addrs or node.kind == NodeKind.REGISTRY_LABEL
        role = "illicit" if flagged else _role_for_kind(node.kind)
        if flagged:
            risk_annotations.append(
                {
                    "type": "illicit_hit",
                    "chain": chain,
                    "address": addr,
                    "hop": hop,
                    "reason_ru": "Совпадение с реестром / индикатор 115-ФЗ",
                }
            )
        label = addr if len(addr) <= 14 else f"{addr[:6]}…{addr[-4:]}"
        nodes.append(
            {
                "id": node.node_id,
                "label": label,
                "address": addr,
                "chain": chain,
                "hop": hop,
                "role": role,
                "kind": node.kind.value,
                "confidence": node.confidence,
            }
        )

    edges = [
        {
            "from": edge.from_id,
            "to": edge.to_id,
            "amount": edge.strength,
            "asset": edge.rel_type,
        }
        for edge in graph.edges
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "risk_annotations": risk_annotations,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "corridor_flagged": any(a.get("type") == "illicit_hit" for a in risk_annotations),
    }


def _chain_from_key(key: str) -> str:
    low = key.lower()
    if low.startswith("0x"):
        return "eth"
    if low.startswith("t") and len(key) >= 30:
        return "tron"
    if low.startswith("bc1") or low.startswith("1") or low.startswith("3"):
        return "btc"
    return ""


def _role_for_kind(kind: NodeKind) -> str:
    if kind == NodeKind.WALLET:
        return "wallet"
    if kind == NodeKind.BANK_FEED:
        return "bank"
    if kind == NodeKind.PLATFORM:
        return "vasp"
    if kind == NodeKind.BRIDGE:
        return "bridge"
    return kind.value
