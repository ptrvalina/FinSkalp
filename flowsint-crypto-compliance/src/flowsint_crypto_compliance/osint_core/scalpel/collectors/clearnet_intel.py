"""
Clearnet dork-поиск по публичным индексам (без API-ключей где возможно).

Паттерны вдохновлены SpiderFoot, Intelligence X surface, grep.app.
Person/org → web/OSINT индексы; wallet → code/leak индексы.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import quote

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.entity_extractor import extract_entities
from flowsint_crypto_compliance.osint_core.scalpel.seed_query import (
    bare_seed_query,
    seed_kind,
)
from flowsint_types.fiat_crypto import Chain

# (name, url_template, source_type, kinds) — kinds empty = all
_PUBLIC_SEARCH_ENDPOINTS: tuple[tuple[str, str, str, frozenset[str]], ...] = (
    (
        "DuckDuckGo",
        "https://html.duckduckgo.com/html/?q={q}",
        "web",
        frozenset({"person", "org", "user", "unknown", "wallet"}),
    ),
    (
        "OpenSanctionsWeb",
        "https://html.duckduckgo.com/html/?q={q}",
        "sanctions_index",
        frozenset({"person", "org", "user", "unknown"}),
    ),
    (
        "grep.app",
        "https://grep.app/api/search?q={q}",
        "web",
        frozenset({"wallet", "user"}),
    ),
)


class ClearnetIntelCollector(ScalpelCollector):
    collector_id = "clearnet_intel"
    name_ru = "Clearnet индексы · dork-поиск"
    routes = ("clearnet",)
    inspired_by = "SpiderFoot + DuckDuckGo + OpenSanctions + grep.app"

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

        query = bare_seed_query(address)
        kind = seed_kind(address)
        short = query[:24] if kind != "wallet" else query[:12]
        queries = _build_queries(query, kind)

        for name, url_tpl, stype, kinds in _PUBLIC_SEARCH_ENDPOINTS:
            if kinds and kind not in kinds:
                continue
            rate_limited = False
            source_queries = (
                [q for q in queries if "opensanctions" in q.lower()]
                if name == "OpenSanctionsWeb"
                else queries[:2]
            ) or queries[:2]
            for q in source_queries[:2]:
                url = url_tpl.format(q=quote(q))
                code, body, route = await self._gw.fetch(url, route="clearnet")
                detail_parts.append(f"{name}:{code}")
                if code in (429, 403):
                    rate_limited = True
                    break
                if code != 200 or not body:
                    continue
                if not _body_matches(body, query, kind, name):
                    continue

                ex = extract_entities(body, context_address=query)
                conf = 0.62 if name == "OpenSanctionsWeb" else 0.55
                label = {
                    "person": "ФИО",
                    "org": "организация",
                    "user": "username",
                    "wallet": "адрес",
                }.get(kind, "seed")
                hits.append(
                    OpenMentionHit(
                        source_type="clearnet_dork",
                        source_name=name,
                        title_ru=f"Индекс clearnet · {label}: {short}",
                        excerpt_ru=(
                            f"Публичный индекс «{name}» содержит совпадение по запросу "
                            f"«{q[:48]}». Извлечено сущностей: {ex.total}."
                        ),
                        url=_public_result_url(name, q, url),
                        risk_tag="sanctions_screening" if name == "OpenSanctionsWeb" else "clearnet_mention",
                        confidence=conf,
                        address=address,
                        chain=chain.value,
                    )
                )
                entities[name] = ex.to_dict()
                break
            if rate_limited:
                continue

        if not hits and _is_demo_address(query):
            from flowsint_crypto_compliance.demo.combat_mode import is_combat_mode

            if not is_combat_mode():
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


def _build_queries(query: str, kind: str) -> list[str]:
    if kind == "person":
        return [
            f'"{query}"',
            f'"{query}" site:opensanctions.org',
            f"{query} telegram OR vk OR linkedin",
        ]
    if kind == "org":
        return [
            f'"{query}"',
            f'"{query}" site:opensanctions.org OR ИНН OR ОГРН',
            f"{query} sanctions OR санкции OR OFAC",
        ]
    if kind == "user":
        return [f'"{query}"', f"{query} site:github.com OR site:t.me"]
    return [
        f'"{query}"',
        f"{query} USDT",
        f"{query} mixer OR обнал",
    ]


def _body_matches(body: str, query: str, kind: str, source: str) -> bool:
    q = query.strip()
    if not q:
        return False
    lower = body.lower()
    q_lower = q.lower()

    if source in {"DuckDuckGo", "OpenSanctionsWeb"}:
        if "no-results" in lower and "result__a" not in body:
            return False
        tokens = [t for t in re.split(r"\s+", q_lower) if len(t) >= 3]
        if source == "OpenSanctionsWeb":
            return "opensanctions.org" in lower and (
                any(t in lower for t in tokens) if tokens else True
            )
        if tokens and any(t in lower for t in tokens):
            return True
        return q_lower in lower

    # grep.app / generic
    return q in body or (kind == "wallet" and q[:12] in body)


def _public_result_url(name: str, q: str, fetch_url: str) -> str:
    if name == "OpenSanctionsWeb":
        return f"https://www.opensanctions.org/search/?q={quote(q)}"
    if name == "DuckDuckGo":
        return f"https://duckduckgo.com/?q={quote(q)}"
    return fetch_url


def _is_demo_address(address: str) -> bool:
    h = hashlib.sha256(address.encode()).hexdigest()
    return int(h[:2], 16) > 200
