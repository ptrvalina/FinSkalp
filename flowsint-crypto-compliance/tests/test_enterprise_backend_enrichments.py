"""Tests for Phase 2 enterprise backend enrichments (standalone modules)."""

from __future__ import annotations

from flowsint_crypto_compliance.services.case_display import profile_display_name, profile_name_ru
from flowsint_crypto_compliance.services.graph_timestamps import enrich_serialized_graph
from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind


class _Profile:
    def __init__(self, **kwargs):
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.email = kwargs.get("email", "analyst@example.com")


def _serialize_node_timestamp(graph: EvidenceGraph) -> dict:
    from flowsint_crypto_compliance.services.graph_timestamps import _payload_timestamp

    node = graph.nodes[0]
    ts = _payload_timestamp(node.payload or {})
    row = {"id": node.node_id, "label": node.primary_key}
    if ts:
        row["timestamp"] = ts
        row["occurred_at"] = ts
    return row


def test_profile_display_name_ru():
    profile = _Profile(first_name="Иван", last_name="Петров", email="i@x.ru")
    assert profile_display_name(profile) == "Иван Петров"
    assert profile_name_ru(profile) == "Петров И."


def test_evidence_graph_payload_timestamp():
    graph = EvidenceGraph()
    graph.upsert_node(
        kind=NodeKind.FIAT_EVENT,
        primary_key="evt-1",
        payload={"observed_at": "2026-07-01T12:00:00+00:00"},
    )
    row = _serialize_node_timestamp(graph)
    assert row["timestamp"] == "2026-07-01T12:00:00+00:00"
    assert row["occurred_at"] == "2026-07-01T12:00:00+00:00"


def test_enrich_serialized_graph_preserves_edge_timestamp():
    raw = {
        "nodes": [{"id": "a", "label": "A"}],
        "edges": [{"id": "e1", "source": "a", "target": "b", "timestamp": 1_720_000_000_000}],
    }
    enriched = enrich_serialized_graph(raw)
    assert enriched["edges"][0]["occurred_at"]


def test_risk_trend_indicator_logic():
    def indicator(history: list[dict]) -> str | None:
        if len(history) < 2:
            return None
        delta = float(history[-1]["score"]) - float(history[-2]["score"])
        if delta >= 5:
            return "↑"
        if delta <= -5:
            return "↓"
        return "→"

    assert indicator([{"score": 10}, {"score": 20}]) == "↑"
    assert indicator([{"score": 50}, {"score": 40}]) == "↓"
    assert indicator([{"score": 50}, {"score": 52}]) == "→"
    assert indicator([{"score": 50}]) is None
