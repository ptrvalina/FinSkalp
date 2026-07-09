from __future__ import annotations

import os
from typing import Optional

import httpx

from flowsint_types.fiat_crypto import Chain

from .base import AddressNeighborhood, ChainAdapter, OnChainTransfer


class EthChainAdapter(ChainAdapter):
    """EVM transfers via Etherscan-compatible API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        chain_id: int = 1,
    ):
        self._api_url = api_url or os.getenv(
            "ETHERSCAN_API_URL", "https://api.etherscan.io/v2/api"
        )
        self._api_key = api_key or os.getenv("ETHERSCAN_API_KEY", "")
        self._chain_id = chain_id

    @property
    def chain(self) -> Chain:
        return Chain.ETH

    def normalize_address(self, address: str) -> str:
        return address.lower()

    async def get_neighborhood(
        self, address: str, *, depth: int = 1, limit: int = 50
    ) -> AddressNeighborhood:
        address = self.normalize_address(address)
        params = {
            "chainid": self._chain_id,
            "module": "account",
            "action": "txlist",
            "address": address,
            "page": 1,
            "offset": limit,
            "sort": "desc",
            "apikey": self._api_key,
        }
        inbound: list[OnChainTransfer] = []
        outbound: list[OnChainTransfer] = []

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(self._api_url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("status") != "1":
                return AddressNeighborhood(
                    address=address, chain=self.chain, inbound=[], outbound=[]
                )
            for tx in payload.get("result", []):
                src = self.normalize_address(tx["from"])
                tgt = self.normalize_address(tx.get("to") or "")
                value_eth = int(tx.get("value", 0)) / 10**18
                transfer = OnChainTransfer(
                    chain=Chain.ETH,
                    tx_hash=tx["hash"],
                    source=src,
                    target=tgt,
                    asset="ETH",
                    amount=value_eth,
                    timestamp=tx.get("timeStamp"),
                )
                if tgt == address:
                    inbound.append(transfer)
                if src == address:
                    outbound.append(transfer)

        return AddressNeighborhood(
            address=address, chain=self.chain, inbound=inbound, outbound=outbound
        )
