"""#8 Reverse WHOIS / DNS — RDAP, Google DNS."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlparse

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.api_cache import cached_fetch
from flowsint_crypto_compliance.osint_core.scalpel.collector_base import (
    CollectorResult,
    ScalpelCollector,
)
from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import acquire
from flowsint_types.fiat_crypto import Chain


class ReverseWhoisDnsCollector(ScalpelCollector):
    collector_id = "reverse_whois_dns"
    name_ru = "Reverse WHOIS / DNS"
    legal_basis_ru = "Публичные RDAP/WHOIS записи регистраторов"
    inspired_by = "RDAP / DNS"

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

        domains = _domains_from_context(address, chain, context)
        hits: list[OpenMentionHit] = []

        for domain in domains[:3]:
            dns_url = f"https://dns.google/resolve?name={quote(domain)}&type=A"
            code, body, _ = await cached_fetch(
                self._gw, dns_url, cache_key=f"dns:{domain}", category="dns"
            )
            if code == 200 and "Answer" in body:
                hits.append(
                    OpenMentionHit(
                        source_type="web",
                        source_name="DNS (Google)",
                        title_ru=f"DNS A · {domain}",
                        excerpt_ru=f"Публичная DNS-запись для {domain}.",
                        url=f"https://dns.google/query?name={domain}&type=A",
                        risk_tag="dns_intel",
                        confidence=0.56,
                        address=address,
                        chain=chain.value,
                    )
                )
            rdap_url = f"https://rdap.org/domain/{quote(domain)}"
            rcode, rbody, _ = await cached_fetch(
                self._gw, rdap_url, cache_key=f"rdap:{domain}", category="dns"
            )
            if rcode == 200 and domain in rbody:
                hits.append(
                    OpenMentionHit(
                        source_type="web",
                        source_name="RDAP",
                        title_ru=f"RDAP · {domain}",
                        excerpt_ru="Публичная RDAP-запись домена (rdap.org).",
                        url=rdap_url,
                        risk_tag="whois_rdap",
                        confidence=0.58,
                        address=address,
                        chain=chain.value,
                    )
                )

        return CollectorResult(
            collector_id=self.collector_id,
            hits=hits,
            status="ok" if hits else "miss",
            detail=f"domains:{len(domains)}",
        )


def _domains_from_context(
    address: str, chain: Chain, context: dict[str, Any] | None
) -> list[str]:
    domains: list[str] = []
    from flowsint_crypto_compliance.osint_core.open_osint_corpus import OPEN_OSINT_CORPUS

    if context:
        for raw in context.get("domains") or []:
            host = str(raw).strip().lower()
            if host and host not in domains:
                domains.append(host)
        for mention in context.get("mentions") or []:
            url = (mention.get("url") or "") if isinstance(mention, dict) else ""
            if "://" in url:
                host = urlparse(url).hostname or ""
                host = host.lower()
                if host and host not in domains:
                    domains.append(host)

    norm = address.lower() if chain.value == "eth" else address
    for row in OPEN_OSINT_CORPUS:
        key = row.address.lower() if chain.value == "eth" else row.address
        if key != norm:
            continue
        url = row.url or ""
        if "://" in url:
            host = urlparse(url).hostname or ""
            if host and host not in domains:
                domains.append(host)
    return domains
