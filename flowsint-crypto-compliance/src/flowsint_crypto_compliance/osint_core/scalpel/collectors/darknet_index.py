"""#5 Darknet Index — live Ahmia.fi."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.live_collectors import collect_ahmia
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.live_collector_bridge import hits_from_ahmia
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_types.fiat_crypto import Chain


class DarknetIndexCollector(ScalpelCollector):
    collector_id = "darknet_index"
    name_ru = "Darknet Index (Ahmia live)"
    legal_basis_ru = "Ahmia.fi — live clearnet-индекс .onion"
    inspired_by = "Ahmia"

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
        queries = [address[:32], f"{address[:16]} crypto", f"{address[:16]} USDT"]
        hits: list = []
        total = 0
        for q in queries[:2]:
            data = await collect_ahmia(q)
            batch = hits_from_ahmia(data, address, chain.value)
            hits.extend(batch)
            total += int(data.get("result_count") or 0)
        hits = _dedupe_darknet_hits(hits)
        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"ahmia_queries:{len(queries[:2])};results:{total}",
        )


def _dedupe_darknet_hits(hits: list) -> list:
    seen: set[str] = set()
    out = []
    for h in hits:
        key = (h.title_ru, h.excerpt_ru[:80])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out[:15]
