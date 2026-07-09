"""
Lightweight GraphSAGE-style neighbor aggregation (numpy, no PyTorch dependency).

2-hop mean pooling over evidence graph → embedding dims fed to XGBoost/ONNX.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind

_EMBED_DIM = 3


def _node_feature_vector(node) -> np.ndarray:
    kind_map = {
        NodeKind.WALLET: 1.0,
        NodeKind.OSINT_MENTION: 0.8,
        NodeKind.SUBJECT: 0.6,
        NodeKind.PLATFORM: 0.7,
        NodeKind.REGISTRY_LABEL: 0.9,
    }
    base = kind_map.get(node.kind, 0.5)
    return np.array([base, node.confidence, len(node.payload)], dtype=np.float32)


def graph_metrics_and_embedding(
    graph: EvidenceGraph | None,
    *,
    wallet_primary_key: str | None = None,
) -> dict[str, float]:
    if graph is None or not graph.nodes:
        return {
            "graph_degree": 0.0,
            "graph_betweenness": 0.0,
            "graphsage_embedding_0": 0.0,
            "graphsage_embedding_1": 0.0,
            "graphsage_embedding_2": 0.0,
        }

    wallet = None
    if wallet_primary_key:
        wallet = graph.find_node(NodeKind.WALLET, wallet_primary_key)
    if wallet is None:
        wallets = graph.wallet_nodes()
        wallet = wallets[0] if wallets else graph.nodes[0]

    adj: dict[str, list[str]] = {}
    for edge in graph.edges:
        adj.setdefault(edge.from_id, []).append(edge.to_id)
        adj.setdefault(edge.to_id, []).append(edge.from_id)

    degree = float(len(adj.get(wallet.node_id, [])))
    betweenness = _approx_betweenness(wallet.node_id, adj, max_nodes=64)
    embedding = _graphsage_aggregate(wallet.node_id, graph, adj, hops=2)

    return {
        "graph_degree": degree,
        "graph_betweenness": betweenness,
        "graphsage_embedding_0": float(embedding[0]),
        "graphsage_embedding_1": float(embedding[1]),
        "graphsage_embedding_2": float(embedding[2]),
    }


def _graphsage_aggregate(
    center_id: str,
    graph: EvidenceGraph,
    adj: dict[str, list[str]],
    *,
    hops: int,
) -> np.ndarray:
    """Mean aggregator over h-hop neighborhood (GraphSAGE-style)."""
    center = graph.get_node(center_id)
    if center is None:
        return np.zeros(_EMBED_DIM, dtype=np.float32)

    vectors = [_node_feature_vector(center)]
    frontier = {center_id}
    visited = {center_id}

    for _ in range(hops):
        nxt: set[str] = set()
        for nid in frontier:
            for nb in adj.get(nid, []):
                if nb in visited:
                    continue
                visited.add(nb)
                nxt.add(nb)
                node = graph.get_node(nb)
                if node:
                    vectors.append(_node_feature_vector(node))
        frontier = nxt

    pooled = np.mean(vectors, axis=0)
    if pooled.shape[0] < _EMBED_DIM:
        pooled = np.pad(pooled, (0, _EMBED_DIM - pooled.shape[0]))
    return pooled[:_EMBED_DIM].astype(np.float32)


def _approx_betweenness(center_id: str, adj: dict[str, list[str]], *, max_nodes: int) -> float:
    """Local betweenness proxy: fraction of shortest paths through center (sampled)."""
    nodes = list(adj.keys())[:max_nodes]
    if center_id not in nodes or len(nodes) < 3:
        return 0.0

    through = 0
    total = 0
    for src in nodes:
        if src == center_id:
            continue
        for dst in nodes:
            if dst in (src, center_id):
                continue
            path = _bfs_path(src, dst, adj)
            if path and center_id in path[1:-1]:
                through += 1
            if path:
                total += 1
    return float(through / total) if total else 0.0


def _bfs_path(start: str, end: str, adj: dict[str, list[str]]) -> list[str] | None:
    if start == end:
        return [start]
    queue = [[start]]
    seen = {start}
    while queue:
        path = queue.pop(0)
        node = path[-1]
        for nb in adj.get(node, []):
            if nb in seen:
                continue
            npath = path + [nb]
            if nb == end:
                return npath
            seen.add(nb)
            queue.append(npath)
    return None
