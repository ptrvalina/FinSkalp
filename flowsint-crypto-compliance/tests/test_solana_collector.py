"""Tests for Solana live collector (mocked RPC)."""

from unittest.mock import AsyncMock, patch

import pytest

from flowsint_crypto_compliance.osint_core.live_collectors import collect_solana_chain
from flowsint_crypto_compliance.services.wallet_screening import infer_chain


@pytest.mark.asyncio
async def test_collect_solana_chain_parses_signatures():
    mock_result = {
        "status": 200,
        "chain": "solana",
        "address": "7EqQdE8uK9X9X9X9X9X9X9X9X9X9X9X9X9X9X9X9X9",
        "tx_count": 2,
        "counterparties": [],
        "transfers": [
            {
                "from": "7EqQdE8uK9X9X9X9X9X9X9X9X9X9X9X9X9X9X9X9X9",
                "tx_hash": "sig1",
                "asset": "SOL",
                "timestamp": 1_700_000_000_000,
            }
        ],
    }
    with patch(
        "flowsint_crypto_compliance.chains.solana.fetch_address_activity",
        new=AsyncMock(return_value=mock_result),
    ):
        out = await collect_solana_chain("7EqQdE8uK9X9X9X9X9X9X9X9X9X9X9X9X9X9X9X9X9")
    assert out["chain"] == "solana"
    assert out["transfers"][0]["asset"] == "SOL"
    assert out["tx_count"] == 2


def test_infer_chain_solana_base58():
    addr = "7EqQdE8uK9X9X9X9X9X9X9X9X9X9X9X9X9X9X9X9X9"
    # infer_chain returns Chain enum — solana uses string slug in collectors;
    # wallet infer raises or we extend with string helper
    from flowsint_crypto_compliance.services.wallet_screening import infer_chain_slug

    assert infer_chain_slug(addr) == "solana"
