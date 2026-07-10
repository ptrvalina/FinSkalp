"""Graph confidence propagation (RFC-0003 Ch.8, additive)."""

from __future__ import annotations

import uuid
from collections import deque
from typing import Any


def propagate_graph_confidence(
    graph: dict[str, Any],
    *,
    seed_entity_id: str | None = None,
    min_confidence: float = 0.0,
    decay: float = 0.85,
    max_hops: int = 4,
) -> dict[str, Any]:
    """Propagate confidence from seed entity through relation edges (multiplicative decay)."""
    entities = {str(e.get("id")): e for e in graph.get("entities") or [] if e.get("id")}
    relations = graph.get("relations") or []

    adjacency: dict[str, list[tuple[str, float, str]]] = {}
    for rel in relations:
        src = str(rel.get("from_entity_id") or "")
        dst = str(rel.get("to_entity_id") or "")
        conf = float(rel.get("confidence") or 0.5)
        rid = str(rel.get("id") or "")
        if src and dst:
            adjacency.setdefault(src, []).append((dst, conf, rid))
            adjacency.setdefault(dst, []).append((src, conf, rid))

    if not entities:
        return {"ok": True, "propagated": [], "seed_entity_id": seed_entity_id, "note": "empty graph"}

    seed = seed_entity_id
    if not seed:
        seed = next(iter(entities))
    if seed not in entities:
        return {"ok": False, "error": "seed_entity_not_found", "seed_entity_id": seed}

    scores: dict[str, float] = {seed: 1.0}
    paths: dict[str, list[str]] = {seed: [seed]}
    queue: deque[tuple[str, int]] = deque([(seed, 0)])

    while queue:
        current, depth = queue.popleft()
        if depth >= max_hops:
            continue
        base = scores[current]
        for neighbor, edge_conf, _rid in adjacency.get(current, []):
            propagated = base * edge_conf * decay
            if propagated < min_confidence:
                continue
            prev = scores.get(neighbor, 0.0)
            if propagated > prev:
                scores[neighbor] = propagated
                paths[neighbor] = paths[current] + [neighbor]
                queue.append((neighbor, depth + 1))

    propagated = [
        {
            "entity_id": eid,
            "display_name": entities[eid].get("display_name"),
            "entity_type": entities[eid].get("entity_type"),
            "propagated_confidence": round(score, 4),
            "path": paths.get(eid, []),
        }
        for eid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if score >= min_confidence
    ]

    return {
        "ok": True,
        "seed_entity_id": seed,
        "decay": decay,
        "max_hops": max_hops,
        "min_confidence": min_confidence,
        "entity_count": len(propagated),
        "propagated": propagated,
    }


def propagate_tenant_confidence(
    tenant_id: uuid.UUID,
    graph: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    result = propagate_graph_confidence(graph, **kwargs)
    result["tenant_id"] = str(tenant_id)
    return result
