from flowsint_crypto_compliance.demo.graph_viz_adapter import (
    ensure_investigation_graph,
    onchain_summary_to_fusion_graph,
)


def test_onchain_summary_builds_edges():
    g = onchain_summary_to_fusion_graph(
        "TTestAddress123456789012345678901234",
        "tron",
        {
            "chain": "tron",
            "sample_tx": [
                {
                    "hash": "abc",
                    "direction": "in",
                    "counterparty": "TCounterparty123456789012345678901",
                    "asset": "USDT",
                    "amount": 100.0,
                }
            ],
            "counterparty_addresses": ["TCounterparty123456789012345678901"],
        },
    )
    assert g["node_count"] >= 2
    assert g["edge_count"] >= 1


def test_ensure_graph_prefers_live_edges():
    live = {"nodes": [{"id": "tron:a"}], "edges": [], "edge_count": 0}
    onchain_summary = {
        "sample_tx": [
            {"hash": "x", "direction": "out", "counterparty": "b", "asset": "USDT", "amount": 1}
        ]
    }
    merged = ensure_investigation_graph(
        address="a",
        chain="tron",
        live_fusion=live,
        onchain=onchain_summary,
    )
    assert merged["edge_count"] >= 1
