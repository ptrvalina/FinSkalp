"""GraphSense TagPack + local path-finding tests."""

from flowsint_crypto_compliance.interop.graphsense_paths import find_paths, graphsense_path_result
from flowsint_crypto_compliance.interop.graphsense_tagpack import load_tagpack, parse_tagpack_csv


_TAGPACK_CSV = """address,currency,label,category,confidence,risk_score
TQn9Yz2r8p7bLSEz7K8vJ3mN4pQ2wR5tYX,trx,Test Exchange,exchange,0.85,12
0x3f5ce5fbfe3e9ee397108865aa489f795bb6ff99,eth,Binance,exchange,0.9,10
"""


def test_parse_tagpack_csv():
    labels = parse_tagpack_csv(_TAGPACK_CSV)
    assert len(labels) == 2
    assert labels[0].chain == "tron"
    assert labels[0].source == "graphsense"
    assert labels[1].chain == "eth"


def test_load_bundled_tagpack():
    labels = load_tagpack()
    assert len(labels) >= 1
    assert all(l.source == "graphsense" for l in labels)


def _sample_graph():
    return {
        "nodes": [
            {"id": "tron:root", "address": "TRoot", "chain": "tron", "hop": 0},
            {"id": "tron:a1", "address": "TA1", "chain": "tron", "hop": 1},
            {"id": "tron:bad", "address": "TBAD", "chain": "tron", "hop": 2, "sanctioned": True},
        ],
        "edges": [
            {"from": "tron:a1", "to": "tron:root"},
            {"from": "tron:bad", "to": "tron:a1"},
        ],
    }


def test_find_paths_shortest():
    paths = find_paths(_sample_graph(), "tron:root", "tron:bad", max_hops=4)
    assert paths
    assert paths[0][0] == "tron:root"
    assert paths[0][-1] == "tron:bad"
    assert len(paths[0]) == 3


def test_graphsense_path_result_by_address():
    result = graphsense_path_result(_sample_graph(), "TRoot", "TBAD", max_hops=4)
    assert result["path_count"] >= 1
    assert result["engine"] == "finskalp_local"
    assert result["paths"][0]["length"] == 2
