from __future__ import annotations

from flowsint_types.fiat_crypto import Chain, SovereignRiskLabel


class LabelCache:
    """In-memory cache for the sovereign risk-label registry."""

    def __init__(self) -> None:
        self._store: dict[str, SovereignRiskLabel] = {}

    def _key(self, chain: Chain, address: str) -> str:
        normalized = address.lower() if chain == Chain.ETH else address
        return f"{chain.value}:{normalized}"

    def put(self, label: SovereignRiskLabel) -> None:
        key = self._key(label.chain, label.address)
        existing = self._store.get(key)
        if existing and existing.confidence >= label.confidence and not label.sanctioned:
            return
        self._store[key] = label

    def lookup(self, chain: Chain, address: str) -> SovereignRiskLabel | None:
        return self._store.get(self._key(chain, address))

    def size(self) -> int:
        return len(self._store)

    def count(self) -> int:
        return self.size()

    def bulk_upsert(self, labels: list[SovereignRiskLabel]) -> int:
        for label in labels:
            self.put(label)
        return len(labels)

    def all_labels(self) -> list[SovereignRiskLabel]:
        return list(self._store.values())
