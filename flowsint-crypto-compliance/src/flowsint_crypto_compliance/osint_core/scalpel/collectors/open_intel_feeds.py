"""Публичные OSINT-фиды: санкции, mempool, DNS, открытые индексы."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_types.fiat_crypto import Chain


class OpenSanctionsCollector(ScalpelCollector):
    collector_id = "open_sanctions"
    name_ru = "OpenSanctions · глобальные списки"
    inspired_by = "OpenSanctions API"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        q = quote(address[:48])
        url = f"https://api.opensanctions.org/search/default?q={q}&limit=5"
        code, body, route = await self._gw.fetch(url, route="clearnet")
        hits: list[OpenMentionHit] = []
        if code == 200 and address[:8] in body:
            hits.append(
                OpenMentionHit(
                    source_type="web",
                    source_name="OpenSanctions",
                    title_ru="Совпадение в открытых санкционных данных",
                    excerpt_ru="OpenSanctions: возможное совпадение идентификатора/алиаса.",
                    url="https://www.opensanctions.org/",
                    risk_tag="sanctions_screening",
                    confidence=0.7,
                    address=address,
                    chain=chain.value,
                )
            )
        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"http:{code}",
        )


class MempoolBtcCollector(ScalpelCollector):
    collector_id = "mempool_space"
    name_ru = "mempool.space · BTC"
    inspired_by = "mempool.space API"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        if chain != Chain.BTC or not (
            address.startswith("bc1") or address.startswith("1") or address.startswith("3")
        ):
            return CollectorResult(collector_id=self.collector_id, hits=[], status="skip")
        url = f"https://mempool.space/api/address/{quote(address)}"
        code, body, _ = await self._gw.fetch(url, route="clearnet")
        hits: list[OpenMentionHit] = []
        if code == 200 and "chain_stats" in body:
            hits.append(
                OpenMentionHit(
                    source_type="explorer_tag",
                    source_name="mempool.space",
                    title_ru="BTC адрес · mempool.space",
                    excerpt_ru="Публичная статистика UTXO/транзакций с mempool.space.",
                    url=f"https://mempool.space/address/{address}",
                    risk_tag="btc_wallet",
                    confidence=0.64,
                    address=address,
                    chain=chain.value,
                )
            )
        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"http:{code}",
        )


class TronGridPublicCollector(ScalpelCollector):
    collector_id = "trongrid_public"
    name_ru = "TronGrid · публичный API"
    inspired_by = "TronGrid / TronScan"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        if chain != Chain.TRON or not (len(address) == 34 and address.startswith("T")):
            return CollectorResult(collector_id=self.collector_id, hits=[], status="skip")
        if "_" in address:
            return CollectorResult(collector_id=self.collector_id, hits=[], status="skip")
        url = f"https://api.trongrid.io/v1/accounts/{quote(address)}"
        code, body, _ = await self._gw.fetch(url, route="clearnet")
        hits: list[OpenMentionHit] = []
        if code == 200 and ("address" in body or "data" in body):
            hits.append(
                OpenMentionHit(
                    source_type="explorer_tag",
                    source_name="TronGrid",
                    title_ru="TRON аккаунт · TronGrid",
                    excerpt_ru="TronGrid v1: аккаунт найден в публичном реестре TRON.",
                    url=f"https://tronscan.org/#/address/{address}",
                    risk_tag="tron_wallet",
                    confidence=0.63,
                    address=address,
                    chain=chain.value,
                )
            )
        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"http:{code}",
        )


class DnsWhoisCollector(ScalpelCollector):
    collector_id = "dns_whois_hint"
    name_ru = "DNS/WHOIS подсказки (домены из OSINT)"
    inspired_by = "SpiderFoot sfp_dns / python-whois"

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> CollectorResult:
        domains: list[str] = []
        from flowsint_crypto_compliance.osint_core.open_osint_corpus import OPEN_OSINT_CORPUS

        norm = address.lower() if chain.value == "eth" else address
        for row in OPEN_OSINT_CORPUS:
            key = row.address.lower() if chain.value == "eth" else row.address
            if key != norm:
                continue
            url = row.url or ""
            if "://" in url:
                from urllib.parse import urlparse

                host = urlparse(url).hostname or ""
                if host and host not in domains:
                    domains.append(host)
        hits: list[OpenMentionHit] = []
        for domain in domains[:3]:
            url = f"https://dns.google/resolve?name={quote(domain)}&type=A"
            code, body, _ = await self._gw.fetch(url, route="clearnet")
            if code == 200 and "Answer" in body:
                hits.append(
                    OpenMentionHit(
                        source_type="web",
                        source_name="DNS Google",
                        title_ru=f"DNS A · {domain}",
                        excerpt_ru=f"Публичная DNS-запись для домена из OSINT-контекста: {domain}.",
                        url=f"https://dns.google/query?name={domain}&type=A",
                        risk_tag="dns_intel",
                        confidence=0.56,
                        address=address,
                        chain=chain.value,
                    )
                )
        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
        )
