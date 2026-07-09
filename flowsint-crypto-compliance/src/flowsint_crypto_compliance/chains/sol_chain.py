"""Solana chain adapter — JSON-RPC neighborhood."""

from __future__ import annotations

from flowsint_types.fiat_crypto import Chain

from .base import AddressNeighborhood, ChainAdapter, OnChainTransfer
from .solana import fetch_address_activity


class SolanaChainAdapter(ChainAdapter):
    @property
    def chain(self) -> Chain:
        return Chain.SOL

    async def get_neighborhood(
        self, address: str, *, depth: int = 1, limit: int = 50
    ) -> AddressNeighborhood:
        address = address.strip()
        inbound: list[OnChainTransfer] = []
        outbound: list[OnChainTransfer] = []
        try:
            data = await fetch_address_activity(address, limit=limit)
            for t in data.get("transfers") or []:
                if not isinstance(t, dict):
                    continue
                transfer = OnChainTransfer(
                    chain=Chain.SOL,
                    tx_hash=str(t.get("tx_hash") or ""),
                    source=str(t.get("from") or address),
                    target=str(t.get("to") or ""),
                    asset=str(t.get("asset") or "SOL"),
                    amount=t.get("amount"),
                    timestamp=str(t.get("timestamp")) if t.get("timestamp") else None,
                )
                outbound.append(transfer)
        except Exception:
            pass
        return AddressNeighborhood(
            address=address,
            chain=self.chain,
            inbound=inbound[:limit],
            outbound=outbound[:limit],
        )
