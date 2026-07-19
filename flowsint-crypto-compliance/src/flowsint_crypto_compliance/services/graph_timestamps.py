"""Attach temporal metadata to serialized evidence graphs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1_000_000_000_000:
            ts /= 1000.0
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return _normalize_timestamp(int(text))
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    except ValueError:
        return text


def _payload_timestamp(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    for key in (
        "timestamp",
        "occurred_at",
        "observed_at",
        "block_timestamp",
        "discovered_at",
        "event_time",
        "created_at",
    ):
        ts = _normalize_timestamp(payload.get(key))
        if ts:
            return ts
    return None


def enrich_serialized_graph(graph: dict[str, Any] | None) -> dict[str, Any]:
    """Add `timestamp` / `occurred_at` on nodes and edges when derivable from payload."""
    if not graph:
        return {"nodes": [], "edges": []}

    nodes_out: list[dict[str, Any]] = []
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        enriched = dict(node)
        ts = (
            _normalize_timestamp(enriched.get("timestamp"))
            or _normalize_timestamp(enriched.get("occurred_at"))
            or _normalize_timestamp(enriched.get("ts"))
            or _payload_timestamp(enriched.get("payload") if isinstance(enriched.get("payload"), dict) else enriched)
        )
        if ts:
            enriched.setdefault("timestamp", ts)
            enriched.setdefault("occurred_at", ts)
        nodes_out.append(enriched)

    edges_out: list[dict[str, Any]] = []
    for edge in graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        enriched = dict(edge)
        ts = (
            _normalize_timestamp(enriched.get("timestamp"))
            or _normalize_timestamp(enriched.get("occurred_at"))
            or _normalize_timestamp(enriched.get("ts"))
        )
        if ts:
            enriched.setdefault("timestamp", ts)
            enriched.setdefault("occurred_at", ts)
        edges_out.append(enriched)

    return {**graph, "nodes": nodes_out, "edges": edges_out}
