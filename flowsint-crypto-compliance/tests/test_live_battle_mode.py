from unittest.mock import AsyncMock, patch

import pytest

from flowsint_crypto_compliance.osint_core.live_collectors import (
    collect_sanctions,
    collect_tron_trc20_transfers,
)
from flowsint_crypto_compliance.osint_core.multihop_fusion import (
    FusionGraph,
    MultiHopFusionEngine,
    is_live_address,
)


def test_is_live_address():
    assert is_live_address("TUVHw4wBAwGEMRx2q4AXymX7FWLKXAqWJE", "tron")
    assert not is_live_address("TRU_HUB_MSK", "tron")


@pytest.mark.asyncio
async def test_collect_sanctions_parses_hits():
    mock_response = {
        "status": 200,
        "data": {"results": [{"id": "test-wallet-1", "caption": "Test Entity test-wallet", "schema": "Person"}]},
    }
    with patch(
        "flowsint_crypto_compliance.osint_core.live_collectors._get_json",
        new=AsyncMock(return_value=mock_response),
    ):
        out = await collect_sanctions("test-wallet")
    assert out["hit_count"] == 1
    assert out["flagged"] is True


@pytest.mark.asyncio
async def test_multihop_engine_with_mock_transfers():
    engine = MultiHopFusionEngine(max_hops=1, max_concurrency=5)

    async def fake_fetch(address, chain):
        if address == "ROOT":
            return (
                [{"from": "ROOT", "to": "CP1", "amount": 100, "tx_hash": "tx1", "asset": "USDT"}],
                ["CP1"],
            )
        return [], []

    async def fake_screen(address, chain):
        return {"flagged": address == "CP1", "sanctioned_confirmed": address == "CP1", "sources": ["opensanctions"]}

    engine._fetch_transfers = fake_fetch  # type: ignore[method-assign]
    engine._screen_address = fake_screen  # type: ignore[method-assign]

    graph = await engine.explore("ROOT", "tron")
    assert graph.corridor_flagged
    assert len(graph.nodes) >= 2


def test_live_collector_registry_lists_expected():
    from flowsint_crypto_compliance.osint_core.live_collector_registry import (
        LIVE_COLLECTOR_REGISTRY,
        list_live_collectors,
    )

    assert len(LIVE_COLLECTOR_REGISTRY) == 11
    ids = {c["id"] for c in list_live_collectors()}
    assert ids == set(LIVE_COLLECTOR_REGISTRY)
    for expected in (
        "collect_tron_chain",
        "collect_eth_chain",
        "collect_bitcoinabuse",
        "collect_ahmia",
        "collect_maigret",
    ):
        assert expected in ids


def test_fusion_graph_to_dict():
    g = FusionGraph()
    g.nodes.append({"id": "tron:A", "address": "A", "chain": "tron", "hop": 0})
    d = g.to_dict()
    assert d["node_count"] == 1


def test_graph_section_includes_png_data_uri():
    from flowsint_crypto_compliance.reporting.graph_report import graph_section_for_report

    graph = {
        "nodes": [
            {"id": "tron:A", "address": "A", "chain": "tron", "hop": 0, "label": "A"},
            {"id": "tron:B", "address": "B", "chain": "tron", "hop": 1, "label": "B"},
        ],
        "edges": [{"from": "tron:A", "to": "tron:B", "asset": "USDT"}],
        "risk_annotations": [],
    }
    sec = graph_section_for_report(graph)
    if sec.get("has_png"):
        assert sec.get("png_data_uri", "").startswith("data:image/png;base64,")

    g = FusionGraph()
    g.nodes.append({"id": "tron:A", "address": "A", "chain": "tron", "hop": 0})
    d = g.to_dict()
    assert d["node_count"] == 1
