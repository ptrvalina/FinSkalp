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

        # Local OFAC / OpenSanctions dump fallback (especially for hop-1 CPs)
        try:
            from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store
            from flowsint_crypto_compliance.attribution.open_datasets import ensure_local_attribution_seeds
            from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
            from flowsint_crypto_compliance.osint_core.scalpel.seed_query import bare_seed_query, is_named_seed

            store = get_entity_label_store()
            ensure_local_attribution_seeds(store)
            lookup_key = bare_seed_query(address) if is_named_seed(address) else address
            lbl = store.lookup(chain.value, lookup_key)
            if lbl and (lbl.sanctioned or (lbl.category or "").lower() == "sanctions"):
                if not any(h.risk_tag == "sanctions_screening" for h in hits):
                    hits.append(
                        OpenMentionHit(
                            source_type="registry",
                            source_name=lbl.source or "ofac_local",
                            title_ru=f"Санкции · {lbl.label}",
                            excerpt_ru=f"Локальная санкционная база ({lbl.source}): {lbl.label}",
                            url=None,
                            risk_tag="sanctions_screening",
                            confidence=float(lbl.confidence or 0.92),
                            address=address,
                            chain=chain.value,
                        )
                    )
        except Exception:
            pass

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"hits:{data.get('hit_count', 0)};flagged:{bool(data.get('flagged'))}",
        )
