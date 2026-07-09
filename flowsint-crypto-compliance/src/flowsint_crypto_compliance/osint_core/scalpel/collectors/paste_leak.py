"""Paste / leak индексы (публичные зеркала)."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.entity_extractor import extract_entities
from flowsint_types.fiat_crypto import Chain


class PasteLeakCollector(ScalpelCollector):
    collector_id = "paste_leak"
    name_ru = "Paste / утечки"
    inspired_by = "SpiderFoot PasteBin modules + Intelligence X"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        from flowsint_crypto_compliance.demo.combat_mode import is_combat_mode

        if is_combat_mode():
            return CollectorResult(
                collector_id=self.collector_id,
                hits=[],
                status="miss",
                detail="combat:live_paste_feed_not_configured",
            )

        from flowsint_crypto_compliance.osint_core.open_osint_corpus import OPEN_OSINT_CORPUS

        hits: list[OpenMentionHit] = []
        norm = address.lower() if chain.value == "eth" else address
        for row in OPEN_OSINT_CORPUS:
            if row.source_type not in ("leak", "paste"):
                continue
            key = row.address.lower() if chain.value == "eth" else row.address
            if key != norm and norm not in row.excerpt_ru:
                continue
            hits.append(
                OpenMentionHit(
                    source_type="paste" if row.source_type == "leak" else row.source_type,
                    source_name=row.source_name,
                    title_ru=row.title_ru,
                    excerpt_ru=row.excerpt_ru,
                    url=row.url,
                    risk_tag=row.risk_tag,
                    confidence=row.confidence * 0.95,
                    observed_at=row.observed_at,
                    address=address,
                    chain=chain.value,
                )
            )

        entities = {}
        for h in hits:
            ex = extract_entities(h.excerpt_ru, context_address=address)
            if ex.total:
                entities[h.source_name] = ex.to_dict()

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            entities=entities,
        )
