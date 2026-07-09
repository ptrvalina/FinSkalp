from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, Optional

from flowsint_types.fiat_crypto import Chain


@dataclass(frozen=True)
class OnChainTransfer:
    chain: Chain
    tx_hash: str
    source: str
    target: str
    asset: Optional[str] = None
    amount: Optional[float] = None
    timestamp: Optional[str] = None


@dataclass
class AddressNeighborhood:
    """Inbound and outbound counterparties for an address."""

    address: str
    chain: Chain
    inbound: list[OnChainTransfer] = field(default_factory=list)
    outbound: list[OnChainTransfer] = field(default_factory=list)


class ChainAdapter(ABC):
  @property
  @abstractmethod
  def chain(self) -> Chain:
      ...

  @abstractmethod
  async def get_neighborhood(
      self, address: str, *, depth: int = 1, limit: int = 50
  ) -> AddressNeighborhood:
      """Fetch direct transfers for clustering and bridge tracing."""

  def normalize_address(self, address: str) -> str:
      if self.chain == Chain.ETH:
          return address.lower()
      return address.strip()


class InMemoryChainAdapter(ChainAdapter):
    """Test adapter backed by an in-memory transfer list."""

    def __init__(self, chain: Chain, transfers: Iterable[OnChainTransfer]):
        self._chain = chain
        self._transfers = list(transfers)

    @property
    def chain(self) -> Chain:
        return self._chain

    async def get_neighborhood(
        self, address: str, *, depth: int = 1, limit: int = 50
    ) -> AddressNeighborhood:
        address = self.normalize_address(address)
        inbound: list[OnChainTransfer] = []
        outbound: list[OnChainTransfer] = []
        for tx in self._transfers:
            src = self.normalize_address(tx.source)
            tgt = self.normalize_address(tx.target)
            if tgt == address:
                inbound.append(tx)
            if src == address:
                outbound.append(tx)
        return AddressNeighborhood(
            address=address,
            chain=self._chain,
            inbound=inbound[:limit],
            outbound=outbound[:limit],
        )
