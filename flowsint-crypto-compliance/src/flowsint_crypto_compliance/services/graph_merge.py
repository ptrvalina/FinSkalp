"""Merge serialized evidence graphs for investigation pipeline."""

from __future__ import annotations

from typing import Any


def merge_evidence_graphs(
    base: dict[str, Any] | None,
    incoming: dict[str, Any],
    merge_mode: str = "append",
) -> dict[str, Any]:
    if merge_mode == "replace" or not base:
        return {
            "nodes": list(incoming.get("nodes") or []),
            "edges": list(incoming.get("edges") or []),
        }

    nodes: dict[str, dict[str, Any]] = {}
    for row in base.get("nodes") or []:
        if isinstance(row, dict) and row.get("id"):
            nodes[str(row["id"])] = row
    for row in incoming.get("nodes") or []:
        if isinstance(row, dict) and row.get("id"):
            nodes[str(row["id"])] = row

    edges: dict[str, dict[str, Any]] = {}
    for row in base.get("edges") or []:
        key = str(row.get("id") or f"{row.get('source')}->{row.get('target')}")
        if isinstance(row, dict):
            edges[key] = row
    for row in incoming.get("edges") or []:
        key = str(row.get("id") or f"{row.get('source')}->{row.get('target')}")
        if isinstance(row, dict):
            edges[key] = row

    return {"nodes": list(nodes.values()), "edges": list(edges.values())}
