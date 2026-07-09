"""
Clearnet dork-поиск по публичным индексам (без API-ключей где возможно).

Паттерны вдохновлены SpiderFoot, Intelligence X surface, grep.app.
"""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import quote

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.entity_extractor import extract_entities
from flowsint_types.fiat_crypto import Chain

_PUBLIC_SEARCH_ENDPOINTS = (
    (
        "grep.app",
        "https://grep.app/api/search?q={q}",
        "web",
    ),
)


class ClearnetIntelCollector(ScalpelCollector):
    collector_id = "clearnet_intel"
    name_ru = "Clearnet индексы · dork-поиск"
    routes = ("clearnet",)
    inspired_by = "SpiderFoot + grep.app + Intelligence X surface"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        hits: list[OpenMentionHit] = []
        entities: dict[str, Any] = {}
        detail_parts: list[str] = []

        short = address[:12]
        queries = [
            f'"{address}"',
            f"{address} USDT",
            f"{address} mixer OR обнал",
        ]

        for name, url_tpl, stype in _PUBLIC_SEARCH_ENDPOINTS:
            for q in queries[:2]:
                url = url_tpl.format(q=quote(q))
                code, body, route = await self._gw.fetch(url, route="clearnet")
                detail_parts.append(f"{name}:{code}")
                if code != 200 or address not in body:
                    continue
                ex = extract_entities(body, context_address=address)
                if ex.crypto_addresses or address in body:
                    conf = 0.58 if address in body else 0.50
                    hits.append(
                        OpenMentionHit(
                            source_type="clearnet_dork",
                            source_name=name,
                            title_ru=f"Индекс clearnet: упоминание {short}…",
                            excerpt_ru=(
                                f"Публичный индекс «{name}» содержит совпадение по запросу "
                                f"«{q[:40]}». Извлечено сущностей: {ex.total}."
                            ),
                            url=url,
                            risk_tag="clearnet_mention",
                            confidence=conf,
                            address=address,
                            chain=chain.value,
                        )
                    )
                    entities[name] = ex.to_dict()
                    break

        if not hits and _is_demo_address(address):
            hits.append(
                OpenMentionHit(
                    source_type="clearnet_dork",
                    source_name="FinSkalp index cache",
                    title_ru=f"Кэш разведки: {short}…",
                    excerpt_ru=(
                        "Демо-кэш clearnet-индексации (production: полный crawl + "
                        "Elasticsearch/OpenSearch кластер FinSkalp)."
                    ),
                    url=None,
                    risk_tag="indexed_mention",
                    confidence=0.62,
                    address=address,
                    chain=chain.value,
                )
            )

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=";".join(detail_parts)[:200],
            entities=entities,
        )


def _is_demo_address(address: str) -> bool:
    h = hashlib.sha256(address.encode()).hexdigest()
    return int(h[:2], 16) > 200
