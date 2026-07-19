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

        # Local scam / sanctions / exchange attribution seeds (TRON-capable)
        try:
            from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store
            from flowsint_crypto_compliance.attribution.open_datasets import ensure_local_attribution_seeds

            store = get_entity_label_store()
            ensure_local_attribution_seeds(store)
            lbl = store.lookup(chain.value, address)
            if lbl:
                cat = (lbl.category or "").lower()
                if lbl.sanctioned or cat == "sanctions":
                    hits.append(
                        OpenMentionHit(
                            source_type="registry",
                            source_name=lbl.source or "ofac_local",
                            title_ru=f"Санкции · {lbl.label}",
                            excerpt_ru=f"Локальная база ({lbl.source}): {lbl.label}",
                            url=None,
                            risk_tag="sanctions_screening",
                            confidence=float(lbl.confidence or 0.9),
                            address=address,
                            chain=chain.value,
                        )
                    )
                elif cat in {"scam", "abuse", "ransomware", "darknet", "mixer", "stolen", "phishing"}:
                    hits.append(
                        OpenMentionHit(
                            source_type="registry",
                            source_name=lbl.source or "abuse_local",
                            title_ru=f"Scam/Abuse · {lbl.label}",
                            excerpt_ru=f"Категория {cat} · источник {lbl.source}",
                            url=None,
                            risk_tag="scam_report",
                            confidence=float(lbl.confidence or 0.8),
                            address=address,
                            chain=chain.value,
                        )
                    )
                elif cat in {"exchange", "vasp", "payment", "gambling", "otc"}:
                    hits.append(
                        OpenMentionHit(
                            source_type="registry",
                            source_name=lbl.source or "attribution",
                            title_ru=f"{lbl.label} ({cat})",
                            excerpt_ru=f"Атрибуция кошелька: {lbl.label}",
                            url=None,
                            risk_tag="exchange" if cat == "exchange" else "licensed_vasp",
                            confidence=float(lbl.confidence or 0.75),
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
            detail=f"hits:{len(hits)}",
        )
