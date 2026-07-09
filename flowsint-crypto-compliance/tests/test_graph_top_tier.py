from flowsint_crypto_compliance.reporting.graph_top_tier import (
    build_cluster_view,
    enrich_investigation_graph,
    graph_to_graphml,
)


def _sample_graph():
    return {
        "nodes": [
            {"id": "tron:root", "address": "TRoot", "chain": "tron", "hop": 0, "role": "root", "risk_score": 40},
            {"id": "tron:a1", "address": "TA1", "chain": "tron", "hop": 1, "label": "Binance", "category": "exchange", "risk_score": 20},
            {"id": "tron:a2", "address": "TA2", "chain": "tron", "hop": 1, "label": "Binance", "category": "exchange", "risk_score": 22},
            {"id": "tron:bad", "address": "TBAD", "chain": "tron", "hop": 2, "sanctioned": True, "category": "sanctions", "risk_score": 95},
        ],
        "edges": [
            {"from": "tron:a1", "to": "tron:root", "amount": 100},
            {"from": "tron:a2", "to": "tron:root", "amount": 50},
            {"from": "tron:bad", "to": "tron:a1", "amount": 10},
        ],
        "risk_annotations": [{"type": "illicit_hit", "address": "TBAD", "chain": "tron"}],
    }


def test_cluster_view_collapses_labeled_addresses():
    g = _sample_graph()
    cv = build_cluster_view(g, root_id="tron:root")
    assert cv["node_count"] < len(g["nodes"])
    cluster_nodes = [n for n in cv["nodes"] if n.get("node_type") == "cluster"]
    assert any(n.get("member_count", 0) >= 2 for n in cluster_nodes)


def test_enrich_adds_exposure_paths():
    enriched = enrich_investigation_graph(_sample_graph(), root_address="TRoot")
    assert enriched.get("cluster_view")
    assert enriched.get("address_view")
    paths = enriched.get("exposure_paths") or []
    assert paths
    assert any(p["hops"] >= 1 for p in paths)


def test_bridge_node_and_timeline():
    g = {
        "nodes": [
            {"id": "tron:root", "address": "TRoot", "chain": "tron", "hop": 0},
            {
                "id": "tron:bridge",
                "address": "TKzxdv2T6kk7k1a48KQvzk1sRvde9BE9Fe",
                "chain": "tron",
                "hop": 1,
            },
        ],
        "edges": [
            {
                "from": "tron:bridge",
                "to": "tron:root",
                "amount": 1000,
                "timestamp": 1_700_000_000_000,
            },
        ],
    }
    enriched = enrich_investigation_graph(g, root_address="TRoot")
    bridge = next(n for n in enriched["address_view"]["nodes"] if n["id"] == "tron:bridge")
    assert bridge.get("role") == "bridge"
    assert enriched.get("timeline")
    assert enriched["timeline"]["event_count"] == 1


def test_graphml_export():
    xml = graph_to_graphml(_sample_graph())
    assert "graphml" in xml
    assert "tron:root" in xml
