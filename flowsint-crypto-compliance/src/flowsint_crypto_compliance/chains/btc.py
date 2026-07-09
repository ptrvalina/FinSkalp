from __future__ import annotations

import os
from typing import Optional

import httpx

from flowsint_types.fiat_crypto import Chain

from .base import AddressNeighborhood, ChainAdapter, OnChainTransfer


class BtcChainAdapter(ChainAdapter):
    """Bitcoin transfers via Blockstream public API."""

    def __init__(self, api_url: Optional[str] = None):
        self._api_url = api_url or os.getenv(
            "BLOCKSTREAM_API_URL", "https://blockstream.info/api"
        )

    @property
    def chain(self) -> Chain:
        return Chain.BTC

    async def get_neighborhood(
        self, address: str, *, depth: int = 1, limit: int = 50
    ) -> AddressNeighborhood:
        inbound: list[OnChainTransfer] = []
        outbound: list[OnChainTransfer] = []

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{self._api_url}/address/{address}/txs")
            resp.raise_for_status()
            txs = resp.json()[:limit]
            for tx in txs:
                tx_hash = tx.get("txid", "")
                timestamp = str(tx.get("status", {}).get("block_time", ""))
                total_in_sats = 0
                total_out_sats = 0
                for vin in tx.get("vin", []):
                    prevout = vin.get("prevout") or {}
                    if prevout.get("scriptpubkey_address") == address:
                        total_out_sats += int(prevout.get("value", 0))
                for vout in tx.get("vout", []):
                    addr = vout.get("scriptpubkey_address")
                    value = int(vout.get("value", 0))
                    if addr == address:
                        total_in_sats += value
                    elif total_out_sats > 0 or any(
                        (vin.get("prevout") or {}).get("scriptpubkey_address") == address
                        for vin in tx.get("vin", [])
                    ):
                        if addr and addr != address:
                            outbound.append(
                                OnChainTransfer(
                                    chain=Chain.BTC,
                                    tx_hash=tx_hash,
                                    source=address,
                                    target=addr,
                                    asset="BTC",
                                    amount=value / 10**8,
                                    timestamp=timestamp,
                                )
                            )
                for vin in tx.get("vin", []):
                    prevout = vin.get("prevout") or {}
                    src = prevout.get("scriptpubkey_address")
                    if src and src != address:
                        for vout in tx.get("vout", []):
                            if vout.get("scriptpubkey_address") == address:
                                inbound.append(
                                    OnChainTransfer(
                                        chain=Chain.BTC,
                                        tx_hash=tx_hash,
                                        source=src,
                                        target=address,
                                        asset="BTC",
                                        amount=int(vout.get("value", 0)) / 10**8,
                                        timestamp=timestamp,
                                    )
                                )

        return AddressNeighborhood(
            address=address,
            chain=self.chain,
            inbound=inbound[:limit],
            outbound=outbound[:limit],
        )
