"""
Darknet / Tor индексация (.onion поисковики).

Live: Ahmia.fi (clearnet API). При наличии Tor SOCKS — дополнительный маршрут для .onion.
FINSKALP_TOR_SOCKS=socks5://127.0.0.1:9050 (автоопределение порта 9050).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from flowsint_crypto_compliance.osint_core.live_collectors import collect_ahmia
from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.live_collector_bridge import hits_from_ahmia
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_types.fiat_crypto import Chain

_ONION_SEARCH = (
    "ahmia",
    "https://ahmia.fi/search/?q={q}",
)


class DarknetTorCollector(ScalpelCollector):
    collector_id = "darknet_tor"
    name_ru = "Darknet · Tor индексы"
    legal_basis_ru = "Ahmia.fi · индекс .onion · clearnet + Tor SOCKS"
    routes = ("tor", "clearnet")
    inspired_by = "SpiderFoot TOR + Ahmia"

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

        tor_on = self._gw.config.tor_enabled()
        hits: list[OpenMentionHit] = []

        # Ahmia clearnet — основной live-путь (работает без Tor)
        data = await collect_ahmia(address[:32])
        hits.extend(hits_from_ahmia(data, address, chain.value))

        # Дополнительный HTTP-проход через gateway (Tor SOCKS если настроен)
        q = quote(address[:24])
        name, url_tpl = _ONION_SEARCH
        url = url_tpl.format(q=q)
        route = self._gw.pick_route_for_url(url)
        if tor_on and route == "clearnet":
            route = "tor" if ".onion" in url.lower() else "clearnet"
        code, body, route_used = await self._gw.fetch(url, route=route)

        if code == 200 and (address in body or address[:10] in body):
            hits.append(
                OpenMentionHit(
                    source_type="darknet_index",
                    source_name=f"{name} ({'Tor' if route_used == 'tor' else 'Clearnet'})",
                    title_ru=f"Darknet индекс: {address[:12]}…",
                    excerpt_ru=(
                        f"Поисковый индекс «{name}» (маршрут {route_used}) "
                        f"содержит совпадение по криптоадресу."
                    ),
                    url=url,
                    risk_tag="darknet_mention",
                    confidence=0.68,
                    address=address,
                    chain=chain.value,
                )
            )

        hits = _dedupe_hits(hits)
        if hits:
            mode = "tor" if tor_on else "clearnet"
            return CollectorResult(
                collector_id=self.collector_id,
                hits=hits,
                status="ok",
                detail=f"{mode};ahmia;http:{code}",
            )

        corpus_hit = _darknet_corpus_hit(address, chain)
        if corpus_hit:
            from flowsint_crypto_compliance.demo.combat_mode import is_combat_mode

            if is_combat_mode():
                return CollectorResult(
                    collector_id=self.collector_id,
                    hits=[],
                    status="miss",
                    detail="live:miss;combat:no_corpus",
                )
            return CollectorResult(
                collector_id=self.collector_id,
                hits=[corpus_hit],
                status="ok",
                detail="corpus_fallback",
            )

        return CollectorResult(
            collector_id=self.collector_id,
            hits=[],
            status="miss",
            detail=f"ahmia;http:{code};tor:{'on' if tor_on else 'off'}",
        )


def _dedupe_hits(hits: list[OpenMentionHit]) -> list[OpenMentionHit]:
    seen: set[str] = set()
    out: list[OpenMentionHit] = []
    for h in hits:
        key = (h.title_ru, h.excerpt_ru[:80])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out[:15]


def _darknet_corpus_hit(address: str, chain: Chain) -> OpenMentionHit | None:
    from flowsint_crypto_compliance.osint_core.open_osint_corpus import OPEN_OSINT_CORPUS

    norm = address.lower() if chain.value == "eth" else address
    for row in OPEN_OSINT_CORPUS:
        if row.source_type != "darknet_index":
            continue
        key = row.address.lower() if chain.value == "eth" else row.address
        if key == norm:
            return OpenMentionHit(
                source_type="darknet_index",
                source_name=row.source_name,
                title_ru=row.title_ru,
                excerpt_ru=row.excerpt_ru,
                url=row.url,
                risk_tag=row.risk_tag,
                confidence=row.confidence,
                observed_at=row.observed_at,
                address=address,
                chain=chain.value,
            )
    return None
