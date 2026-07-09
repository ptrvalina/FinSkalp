"""#7 Court/Enforcement — DOJ/Europol ingest store + публичные seizure notices."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.ingestion.enforcement_feeds import lookup_address
from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_types.fiat_crypto import Chain


class CourtEnforcementCollector(ScalpelCollector):
    collector_id = "court_enforcement"
    name_ru = "Суд / enforcement"
    legal_basis_ru = "Публичные пресс-релизы DOJ, Europol, Interpol; официальные seizure notices"
    inspired_by = "DOJ / Europol public releases"

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
        store_hits = lookup_address(address, chain.value)

        for row in store_hits:
            hits.append(
                OpenMentionHit(
                    source_type="web",
                    source_name=row.get("source", "Enforcement"),
                    title_ru=row.get("title", "Enforcement notice")[:200],
                    excerpt_ru=(row.get("excerpt") or "")[:500],
                    url=row.get("url"),
                    risk_tag="enforcement_seizure",
                    confidence=0.82,
                    observed_at=row.get("published_at"),
                    address=address,
                    chain=chain.value,
                )
            )

        if not hits:
            from flowsint_crypto_compliance.osint_core.open_osint_corpus import OPEN_OSINT_CORPUS

            norm = address.lower() if chain.value == "eth" else address
            for row in OPEN_OSINT_CORPUS:
                if row.source_type not in ("forum", "web", "explorer_tag"):
                    continue
                key = row.address.lower() if chain.value == "eth" else row.address
                if key != norm:
                    continue
                if "seizure" in row.excerpt_ru.lower() or "изъят" in row.excerpt_ru.lower():
                    hits.append(
                        OpenMentionHit(
                            source_type="web",
                            source_name=row.source_name,
                            title_ru=row.title_ru,
                            excerpt_ru=row.excerpt_ru,
                            url=row.url,
                            risk_tag="enforcement_context",
                            confidence=row.confidence * 0.9,
                            observed_at=row.observed_at,
                            address=address,
                            chain=chain.value,
                        )
                    )

        detail = f"store:{len(store_hits)};hits:{len(hits)}"
        if not hits:
            hits.append(
                OpenMentionHit(
                    source_type="web",
                    source_name="Enforcement index",
                    title_ru="Enforcement feed · нет совпадений",
                    excerpt_ru=(
                        "DOJ/Europol RSS ingest активен. "
                        "Запустите ingest_enforcement_notices для обновления."
                    ),
                    url="https://www.justice.gov/news",
                    risk_tag="enforcement_feed",
                    confidence=0.4,
                    address=address,
                    chain=chain.value,
                )
            )

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits[:5],
            status="ok" if store_hits or len(hits) > 1 else "miss",
            detail=detail,
        )
