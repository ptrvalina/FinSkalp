from unittest.mock import AsyncMock, patch

import pytest

from flowsint_crypto_compliance.osint_core.live_collectors import collect_eth_chain


@pytest.mark.asyncio
async def test_collect_eth_chain_parses_transfers():
    tx_body = {
        "status": "1",
        "result": [
            {
                "from": "0xabc0000000000000000000000000000000000001",
                "to": "0xdef0000000000000000000000000000000000002",
                "value": "1000000000000000000",
                "timeStamp": "1700000000",
                "hash": "0xtx1",
            }
        ],
    }
    token_body = {"status": "1", "result": []}

    async def fake_get(url, **kwargs):
        if "tokentx" in url:
            return {"status": 200, "data": token_body, "source": "etherscan"}
        return {"status": 200, "data": tx_body, "source": "etherscan"}

    with patch(
        "flowsint_crypto_compliance.osint_core.live_collectors._get_json",
        new=AsyncMock(side_effect=fake_get),
    ):
        out = await collect_eth_chain("0xABC0000000000000000000000000000000000001")

    assert out["chain"] == "eth"
    assert out["tx_count"] == 1
    assert len(out["transfers"]) == 1
    assert out["transfers"][0]["asset"] == "ETH"
    assert "0xdef0000000000000000000000000000000000002" in out["counterparties"]


@pytest.mark.asyncio
async def test_multihop_fusion_eth_branch():
    from flowsint_crypto_compliance.osint_core.multihop_fusion import MultiHopFusionEngine

    engine = MultiHopFusionEngine(max_hops=0, max_concurrency=2)
    mock_data = {
        "transfers": [{"from": "0xaaa", "to": "0xbbb", "amount": 1, "tx_hash": "t1", "asset": "ETH"}],
        "counterparties": ["0xbbb"],
    }
    with patch(
        "flowsint_crypto_compliance.osint_core.multihop_fusion.collect_eth_chain",
        new=AsyncMock(return_value=mock_data),
    ):
        transfers, cps = await engine._fetch_transfers("0xaaa", "eth")
    assert len(transfers) == 1
    assert cps == ["0xbbb"]
