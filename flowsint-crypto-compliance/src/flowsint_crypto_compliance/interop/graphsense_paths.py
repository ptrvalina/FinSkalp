"""Path-finding on FinSkalp fusion graphs (GraphSense-style API, no GS server)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from flowsint_crypto_compliance.reporting.graph_top_tier import _bfs_path


def _resolve_node_id(graph: dict[str, Any], ref: str) -> str | None:
    """Match node id, address, or chain:address shorthand."""
    ref = ref.strip()
    base = graph.get("address_view") or graph
    nodes = base.get("nodes") or []
    for n in nodes:
        nid = str(n.get("id") or "")
        addr = str(n.get("address") or "")
        chain = str(n.get("chain") or "")
        if ref == nid or ref == addr or ref == f"{chain}:{addr}":
            return nid
    return None


def _build_adjacency(graph: dict[str, Any]) -> dict[str, list[str]]:
    base = graph.get("address_view") or graph
    adj: dict[str, list[str]] = defaultdict(list)
    for e in base.get("edges") or []:
        fr, to = str(e.get("from")), str(e.get("to"))
        if fr and to:
            adj[fr].append(to)
            adj[to].append(fr)
    return adj


def find_paths(
    graph: dict[str, Any],
    source_id: str,
    target_id: str,
    max_hops: int = 4,
) -> list[list[str]]:
    """Find simple paths between two nodes up to max_hops (inclusive)."""
    src = _resolve_node_id(graph, source_id) or source_id
    tgt = _resolve_node_id(graph, target_id) or target_id
    if src == tgt:
        return [[src]]

    adj = _build_adjacency(graph)
    paths: list[list[str]] = []
    stack: list[tuple[str, list[str]]] = [(src, [src])]

    while stack:
        node, path = stack.pop()
        if len(path) - 1 > max_hops:
            continue
        if node == tgt and len(path) > 1:
            paths.append(path)
            continue
        for nxt in adj.get(node, []):
            if nxt in path:
                continue
            stack.append((nxt, path + [nxt]))

    if not paths:
        shortest = _bfs_path(adj, src, tgt)
        if shortest:
            paths = [shortest]

    paths.sort(key=len)
    return paths[:20]


def _addr_for_node(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    base = graph.get("address_view") or graph
    for n in base.get("nodes") or []:
        if str(n.get("id")) == node_id:
            return {
                "id": node_id,
                "address": n.get("address"),
                "chain": n.get("chain"),
                "label": n.get("label"),
            }
    return {"id": node_id}


def graphsense_path_result(
    graph: dict[str, Any],
    source_id: str,
    target_id: str,
    *,
    max_hops: int = 4,
) -> dict[str, Any]:
    """GraphSense-style path payload for API consumers."""
    paths = find_paths(graph, source_id, target_id, max_hops=max_hops)
    formatted = []
    for path in paths:
        nodes = [_addr_for_node(graph, nid) for nid in path]
        formatted.append(
            {
                "length": max(0, len(path) - 1),
                "node_ids": path,
                "nodes": nodes,
            }
        )
    return {
        "source": source_id,
        "target": target_id,
        "max_hops": max_hops,
        "path_count": len(formatted),
        "paths": formatted,
        "engine": "finskalp_local",
    }
