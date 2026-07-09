"""Normalize fusion graphs to a single UI/report format."""

from __future__ import annotations

from typing import Any


def normalize_graph_for_ui(graph: dict[str, Any] | None) -> dict[str, Any]:
    if not graph:
        return {"nodes": [], "edges": [], "risk_annotations": []}
    nodes = []
    for n in graph.get("nodes") or []:
        addr = n.get("address") or _addr_from_id(n.get("id", ""))
        chain = n.get("chain") or _chain_from_id(n.get("id", ""))
        nodes.append(
            {
                "id": n.get("id") or f"{chain}:{addr}",
                "address": addr,
                "chain": chain,
                "label": n.get("label") or (addr[:8] + "…" if len(addr) > 12 else addr),
                "hop": n.get("hop", 0),
                "role": n.get("role", "counterparty"),
                "risk_score": float(n.get("risk_score") or 15),
                "category": n.get("category") or "unknown",
                "tier": n.get("tier", 3),
                "sanctioned": bool(n.get("sanctioned")),
                "attribution_source": n.get("attribution_source"),
            }
        )
    edges = []
    for e in graph.get("edges") or []:
        edges.append(
            {
                "id": e.get("id") or f"{e.get('from')}->{e.get('to')}",
                "from": e.get("from") or e.get("source"),
                "to": e.get("to") or e.get("target"),
                "amount": e.get("amount"),
                "tx_hash": e.get("tx_hash"),
                "timestamp": e.get("timestamp"),
                "asset": e.get("asset"),
                "direction": e.get("direction") or "transfer",
                "rel_type": e.get("rel_type", "SENT_TO"),
            }
        )
    return {
        "nodes": nodes,
        "edges": edges,
        "risk_annotations": graph.get("risk_annotations") or [],
        "corridor_flagged": graph.get("corridor_flagged", False),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "max_hop_reached": graph.get("max_hop_reached", 0),
        "attribution": graph.get("attribution"),
    }


def _addr_from_id(node_id: str) -> str:
    if ":" in node_id:
        return node_id.split(":", 1)[1]
    return node_id


def _chain_from_id(node_id: str) -> str:
    if ":" in node_id:
        return node_id.split(":", 1)[0]
    return "tron"
