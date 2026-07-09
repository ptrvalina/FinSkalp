"""EVM chain adapter via Blockscout-compatible API — BNB Chain, Polygon."""

from __future__ import annotations

import os
from typing import Optional

import httpx

from flowsint_types.fiat_crypto import Chain

from .base import AddressNeighborhood, ChainAdapter, OnChainTransfer
from .blockscout_client import account_txlist_url, account_tokentx_url, parse_evm_transfers

_EVM_CHAIN_MAP = {
    "bsc": Chain.BSC,
    "bnb": Chain.BSC,
    "polygon": Chain.POLYGON,
}


class EvmBlockscoutAdapter(ChainAdapter):
    """Shared adapter for EVM chains using Blockscout REST API."""

    def __init__(self, chain_key: str, *, api_key: Optional[str] = None):
        key = chain_key.lower()
        if key == "bnb":
            key = "bsc"
        if key not in _EVM_CHAIN_MAP:
            raise ValueError(f"Unsupported EVM chain: {chain_key}")
        self._chain_key = key
        self._chain = _EVM_CHAIN_MAP[key]
        self._api_key = api_key or os.getenv("BLOCKSCOUT_API_KEY", "")

    @property
    def chain(self) -> Chain:
        return self._chain

    async def get_neighborhood(
        self, address: str, *, depth: int = 1, limit: int = 50
    ) -> AddressNeighborhood:
        addr = self.normalize_address(address)
        inbound: list[OnChainTransfer] = []
        outbound: list[OnChainTransfer] = []
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                tx_resp = await client.get(account_txlist_url(self._chain_key, addr, offset=limit, api_key=self._api_key))
                tok_resp = await client.get(account_tokentx_url(self._chain_key, addr, offset=limit, api_key=self._api_key))
                tx_body = tx_resp.json() if tx_resp.status_code == 200 else {}
                tok_body = tok_resp.json() if tok_resp.status_code == 200 else {}
            parsed = parse_evm_transfers(self._chain_key, addr, tx_body=tx_body, token_body=tok_body, native_limit=limit)
            for t in parsed.get("transfers") or []:
                if not isinstance(t, dict):
                    continue
                transfer = OnChainTransfer(
                    chain=self._chain,
                    tx_hash=str(t.get("tx_hash") or ""),
                    source=str(t.get("from") or ""),
                    target=str(t.get("to") or ""),
                    asset=str(t.get("asset") or "NATIVE"),
                    amount=float(t.get("amount") or 0) if t.get("amount") else None,
                    timestamp=str(t.get("timestamp")) if t.get("timestamp") else None,
                )
                if transfer.target == addr:
                    inbound.append(transfer)
                if transfer.source == addr:
                    outbound.append(transfer)
        except Exception:
            pass
        return AddressNeighborhood(
            address=addr,
            chain=self._chain,
            inbound=inbound[:limit],
            outbound=outbound[:limit],
        )
