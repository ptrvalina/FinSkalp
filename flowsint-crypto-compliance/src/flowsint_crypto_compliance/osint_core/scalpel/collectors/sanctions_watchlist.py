"""#2 Sanctions — live OpenSanctions API."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.live_collectors import collect_sanctions
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.live_collector_bridge import hits_from_sanctions
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_types.fiat_crypto import Chain


class SanctionsWatchlistCollector(ScalpelCollector):
    collector_id = "sanctions_watchlist"
    name_ru = "Санкции (live OpenSanctions)"
    legal_basis_ru = "OpenSanctions live API"
    inspired_by = "OpenSanctions"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        if not acquire(self.collector_id):
            return CollectorResult(
                collector_id=self.collector_id, hits=[], status="rate_limited"
            )
        data = await collect_sanctions(address)
        hits = hits_from_sanctions(data, address, chain.value)
        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"hits:{data.get('hit_count', 0)}",
        )
