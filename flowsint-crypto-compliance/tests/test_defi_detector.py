from flowsint_crypto_compliance.engine.defi_detector import annotate_defi, lookup_defi
from flowsint_crypto_compliance.reporting.graph_top_tier import enrich_investigation_graph


def test_lookup_pancakeswap():
    meta = lookup_defi("0x10ed43c718714eb63d5aa57b78b54704e256024e")
    assert meta and meta["defi_type"] == "dex_router"


def test_annotate_defi_tags_node():
    g = {
        "nodes": [
            {"id": "bsc:router", "address": "0x10ed43c718714eb63d5aa57b78b54704e256024e", "chain": "bsc", "hop": 1},
            {"id": "bsc:user", "address": "0xabc", "chain": "bsc", "hop": 0},
        ],
        "edges": [{"from": "bsc:user", "to": "bsc:router", "amount": 1}],
    }
    out = annotate_defi(g)
    router = next(n for n in out["nodes"] if n["id"] == "bsc:router")
    assert router["category"] == "defi"
    assert out["defi_detected"] is True


def test_enrich_includes_defi_hits():
    g = {
        "nodes": [
            {"id": "eth:root", "address": "0xroot", "chain": "eth", "hop": 0},
            {
                "id": "eth:dex",
                "address": "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
                "chain": "eth",
                "hop": 1,
            },
        ],
        "edges": [{"from": "eth:dex", "to": "eth:root", "amount": 100}],
    }
    enriched = enrich_investigation_graph(g, root_address="0xroot")
    assert enriched.get("defi_detected") and len(enriched.get("defi_hits") or []) >= 1
