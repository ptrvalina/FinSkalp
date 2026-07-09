"""Phase 3 graph showcase — cluster volume, exposure paths, PDF risk tokens."""

from flowsint_crypto_compliance.reporting.graph_top_tier import (
    build_cluster_view,
    enrich_investigation_graph,
)
from flowsint_crypto_compliance.reporting.svg_graph_style import (
    FS_RISK_CRITICAL,
    FS_RISK_HIGH,
    FS_RISK_MEDIUM,
    risk_node_color,
)


def _volume_graph():
    return {
        "nodes": [
            {"id": "tron:root", "address": "TRoot", "chain": "tron", "hop": 0, "risk_score": 40},
            {
                "id": "tron:a1",
                "address": "TA1",
                "chain": "tron",
                "hop": 1,
                "label": "Binance",
                "category": "exchange",
                "risk_score": 20,
                "volume_usd": 50_000,
            },
            {
                "id": "tron:a2",
                "address": "TA2",
                "chain": "tron",
                "hop": 1,
                "label": "Binance",
                "category": "exchange",
                "risk_score": 22,
                "volume_usd": 120_000,
            },
            {"id": "tron:bad", "address": "TBAD", "chain": "tron", "hop": 2, "sanctioned": True, "risk_score": 95},
        ],
        "edges": [
            {"from": "tron:a1", "to": "tron:root", "amount": 100},
            {"from": "tron:a2", "to": "tron:root", "amount": 50},
            {"from": "tron:bad", "to": "tron:a1", "amount": 10},
        ],
        "risk_annotations": [{"type": "illicit_hit", "address": "TBAD", "chain": "tron"}],
    }


def test_cluster_supernode_carries_volume_usd():
    g = _volume_graph()
    cv = build_cluster_view(g, root_id="tron:root")
    cluster = next(n for n in cv["nodes"] if n.get("node_type") == "cluster")
    assert cluster["member_count"] == 2
    assert cluster["volume_usd"] == 170_000.0


def test_exposure_path_reaches_illicit_target():
    enriched = enrich_investigation_graph(_volume_graph(), root_address="TRoot")
    paths = enriched["exposure_paths"]
    assert paths
    bad_path = next(p for p in paths if p["target_id"] == "tron:bad")
    assert bad_path["path"][0] == "tron:root"
    assert bad_path["path"][-1] == "tron:bad"
    assert bad_path["hops"] >= 2


def test_exposure_path_includes_intermediate_edge():
    enriched = enrich_investigation_graph(_volume_graph(), root_address="TRoot")
    bad_path = next(p for p in enriched["exposure_paths"] if p["target_id"] == "tron:bad")
    path = bad_path["path"]
    pairs = list(zip(path, path[1:]))
    assert ("tron:a1", "tron:bad") in pairs or ("tron:bad", "tron:a1") in pairs


def test_pdf_risk_colors_match_fs_tokens():
    assert risk_node_color(95, flagged=True) == FS_RISK_CRITICAL
    assert risk_node_color(60) == FS_RISK_HIGH
    assert risk_node_color(35) == FS_RISK_MEDIUM
    assert risk_node_color(5) == risk_node_color(0)  # muted tier
