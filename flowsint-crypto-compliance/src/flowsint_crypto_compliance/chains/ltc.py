"""Litecoin chain adapter — Blockstream-compatible API."""

from __future__ import annotations

import os
from typing import Optional

import httpx

from flowsint_types.fiat_crypto import Chain

from .base import AddressNeighborhood, ChainAdapter, OnChainTransfer


class LtcChainAdapter(ChainAdapter):
    """Litecoin transfers via litecoinspace.org (Blockstream-style API)."""

    def __init__(self, api_url: Optional[str] = None):
        self._api_url = (api_url or os.getenv("LITECOIN_API_URL", "https://litecoinspace.org/api")).rstrip("/")

    @property
    def chain(self) -> Chain:
        return Chain.LTC

    async def get_neighborhood(
        self, address: str, *, depth: int = 1, limit: int = 50
    ) -> AddressNeighborhood:
        address = address.strip()
        inbound: list[OnChainTransfer] = []
        outbound: list[OnChainTransfer] = []
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(f"{self._api_url}/address/{address}/txs")
                if resp.status_code != 200:
                    return AddressNeighborhood(address=address, chain=self.chain, inbound=[], outbound=[])
                txs = resp.json()
                if not isinstance(txs, list):
                    return AddressNeighborhood(address=address, chain=self.chain, inbound=[], outbound=[])
                for tx in txs[:limit]:
                    if not isinstance(tx, dict):
                        continue
                    txid = tx.get("txid") or ""
                    for vout in tx.get("vout") or []:
                        if not isinstance(vout, dict):
                            continue
                        spk = vout.get("scriptpubkey_address") or ""
                        val = (vout.get("value") or 0) / 1e8
                        if spk == address:
                            inbound.append(
                                OnChainTransfer(
                                    chain=Chain.LTC,
                                    tx_hash=txid,
                                    source="",
                                    target=address,
                                    asset="LTC",
                                    amount=val,
                                )
                            )
                    for vin in tx.get("vin") or []:
                        if not isinstance(vin, dict):
                            continue
                        prev = vin.get("prevout") or {}
                        spk = prev.get("scriptpubkey_address") or ""
                        val = (prev.get("value") or 0) / 1e8
                        if spk == address:
                            outbound.append(
                                OnChainTransfer(
                                    chain=Chain.LTC,
                                    tx_hash=txid,
                                    source=address,
                                    target="",
                                    asset="LTC",
                                    amount=val,
                                )
                            )
        except Exception:
            pass
        return AddressNeighborhood(
            address=address,
            chain=self.chain,
            inbound=inbound[:limit],
            outbound=outbound[:limit],
        )
