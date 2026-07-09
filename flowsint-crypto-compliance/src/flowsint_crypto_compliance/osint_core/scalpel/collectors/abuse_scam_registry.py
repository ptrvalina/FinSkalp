"""#4 Abuse — live BitcoinAbuse + Chainabuse."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from flowsint_crypto_compliance.osint_core.live_collectors import collect_bitcoinabuse
from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.api_cache import cached_fetch
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.live_collector_bridge import hits_from_bitcoinabuse
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_types.fiat_crypto import Chain


class AbuseScamRegistryCollector(ScalpelCollector):
    collector_id = "abuse_scam_registry"
    name_ru = "Abuse / Scam (live)"
    legal_basis_ru = "BitcoinAbuse, Chainabuse — live API"
    inspired_by = "BitcoinAbuse / Chainabuse"

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

        hits: list[OpenMentionHit] = []

        if chain == Chain.BTC:
            abuse = await collect_bitcoinabuse(address)
            hits.extend(hits_from_bitcoinabuse(abuse, address))

        chainabuse_url = f"https://www.chainabuse.com/api/v0/reports?address={quote(address)}"
        code, body, _ = await cached_fetch(
            self._gw,
            chainabuse_url,
            cache_key=f"chainabuse:{address[:32]}",
            category="abuse_live",
        )
        if code == 200 and address[:8] in body:
            hits.append(
                OpenMentionHit(
                    source_type="web",
                    source_name="Chainabuse",
                    title_ru="Chainabuse · live match",
                    excerpt_ru="Краудсорс-реестр scam/abuse.",
                    url=f"https://www.chainabuse.com/report/{quote(address)}",
                    risk_tag="scam_report",
                    confidence=0.75,
                    address=address,
                    chain=chain.value,
                )
            )

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"hits:{len(hits)}",
        )
