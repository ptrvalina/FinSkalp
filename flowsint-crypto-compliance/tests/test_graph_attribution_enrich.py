"""Graph node enrichment from attribution labels and connections."""

from flowsint_crypto_compliance.attribution.attribution_engine import AttributionEngine, AttributionResult
from flowsint_crypto_compliance.attribution.types import EntityLabel


def test_from_dict_rebuilds_labels():
    data = {
        "labels": {
            "TXbinance": {
                "address": "TXbinance",
                "chain": "tron",
                "label": "Binance Hot",
                "category": "exchange",
                "confidence": 0.85,
                "source": "tronscan",
                "tier": 2,
                "risk_score": 22,
            }
        },
        "connections": [],
    }
    attr = AttributionResult.from_dict(data)
    assert "TXbinance" in attr.labels
    assert attr.labels["TXbinance"].category == "exchange"


def test_enrich_graph_uses_connections_when_no_label():
    engine = AttributionEngine()
    graph = {
        "nodes": [
            {"id": "tron:subj", "address": "TSubj", "hop": 0, "chain": "tron"},
            {"id": "tron:cp", "address": "TXcp", "hop": 1, "chain": "tron", "role": "counterparty"},
        ],
        "edges": [],
    }
    attr = AttributionResult(
        connections=[
            {
                "address": "TXcp",
                "entity_name": "Huobi",
                "category": "exchange",
                "risk_pct": 35,
                "tier": 2,
                "confidence": 0.7,
                "source": "graphsense",
            }
        ]
    )
    out = engine.enrich_graph(graph, attr)
    cp = next(n for n in out["nodes"] if n["address"] == "TXcp")
    assert cp["category"] == "exchange"
    assert cp["label"] == "Huobi"
    assert cp["risk_score"] == 35.0


def test_enrich_graph_sparkline_from_edges():
    engine = AttributionEngine()
    graph = {
        "nodes": [{"id": "tron:a", "address": "Ta", "hop": 0}],
        "edges": [
            {"from": "tron:b", "to": "tron:a", "timestamp": "2026-01-01T00:00:00Z"},
            {"from": "tron:b", "to": "tron:a", "timestamp": "2026-01-02T00:00:00Z"},
        ],
    }
    out = engine.enrich_graph(graph, AttributionResult())
    assert out["nodes"][0].get("activity_sparkline")
