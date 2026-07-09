"""Tests for polygon collector via Blockscout client."""

from unittest.mock import AsyncMock, patch

import pytest

from flowsint_crypto_compliance.osint_core.live_collectors import collect_polygon_chain


@pytest.mark.asyncio
async def test_collect_polygon_chain_parses_transfers():
    mock_payload = {
        "status": 200,
        "chain": "polygon",
        "address": "0xabc",
        "tx_count": 1,
        "token_tx_count": 0,
        "counterparties": ["0xdef"],
        "transfers": [
            {
                "from": "0xabc",
                "to": "0xdef",
                "amount": "1",
                "tx_hash": "0xtx",
                "asset": "MATIC",
            }
        ],
    }
    with patch(
        "flowsint_crypto_compliance.chains.blockscout_client.fetch_evm_chain_data",
        new=AsyncMock(return_value=mock_payload),
    ):
        out = await collect_polygon_chain("0xABC")
    assert out["chain"] == "polygon"
    assert out["transfers"][0]["asset"] == "MATIC"
