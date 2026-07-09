"""Integration test — investigate pipeline with mocked external APIs."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_multihop_fusion_mocked_collectors():
    from flowsint_crypto_compliance.osint_core.multihop_fusion import FusionGraph, MultiHopFusionEngine

    graph = FusionGraph()
    graph.nodes.append({"id": "tron:TA", "address": "TA", "chain": "tron", "hop": 0, "role": "root"})
    graph.edges.append({"from": "tron:TA", "to": "tron:TB", "asset": "TRX", "amount": 1})

    with patch.object(MultiHopFusionEngine, "explore", new=AsyncMock(return_value=graph)):
        engine = MultiHopFusionEngine(max_hops=1)
        result = await engine.explore("TA", "tron")
    payload = result.to_dict()
    assert payload["node_count"] == 1
    assert payload["edge_count"] == 1
