"""Статический корпус + Telegram/форумы (офлайн + расширяемый)."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import (
    OpenMentionHit,
    _search_corpus,
)
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.entity_extractor import extract_entities
from flowsint_types.fiat_crypto import Chain


class CorpusTelegramCollector(ScalpelCollector):
    collector_id = "corpus_telegram"
    name_ru = "Telegram / форумы / утечки (корпус)"
    inspired_by = "OSINT Framework + ручная разведка FIU"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        hits = _search_corpus(address, chain)
        entities: dict[str, Any] = {}
        for h in hits:
            ex = extract_entities(h.excerpt_ru, context_address=address)
            if ex.total:
                entities[h.source_name] = ex.to_dict()

        if counterparties:
            for cp in (counterparties or [])[:8]:
                if cp == address:
                    continue
                sub = _search_corpus(cp, chain)
                for m in sub[:2]:
                    hits.append(
                        OpenMentionHit(
                            source_type="correlation",
                            source_name="1-hop counterparty OSINT",
                            title_ru=f"Контрагент {cp[:10]}…",
                            excerpt_ru=m.excerpt_ru,
                            url=m.url,
                            risk_tag=m.risk_tag,
                            confidence=round(m.confidence * 0.85, 3),
                            observed_at=m.observed_at,
                            address=cp,
                            chain=chain.value,
                        )
                    )
        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok",
            entities=entities,
        )
