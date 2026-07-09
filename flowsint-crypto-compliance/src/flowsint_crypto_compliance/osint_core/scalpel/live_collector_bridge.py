"""Convert live collector payloads → OpenMentionHit for Scalpel pipeline."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit


def hits_from_tron_chain(data: dict[str, Any], address: str) -> list[OpenMentionHit]:
    hits: list[OpenMentionHit] = []
    tx_count = data.get("tx_count", 0)
    source_name = data.get("on_chain_source_ru") or "TronGrid"
    if data.get("status") == 200 or tx_count:
        hits.append(
            OpenMentionHit(
                source_type="explorer_tag",
                source_name=source_name,
                title_ru=f"TRON · {tx_count} TRX-транзакций (live)",
                excerpt_ru=f"{source_name}: {tx_count} tx, контрагентов {len(data.get('counterparties') or [])}.",
                url=f"https://tronscan.org/#/address/{address}",
                risk_tag="tron_wallet",
                confidence=0.78,
                address=address,
                chain="tron",
            )
        )
    for tr in (data.get("transfers") or [])[:5]:
        hits.append(
            OpenMentionHit(
                source_type="explorer_tag",
                source_name=source_name,
                title_ru=f"TRX transfer → {str(tr.get('to', ''))[:12]}…",
                excerpt_ru=f"tx {str(tr.get('tx_hash', ''))[:16]}… amount={tr.get('amount')}",
                url=f"https://tronscan.org/#/transaction/{tr.get('tx_hash', '')}",
                risk_tag="onchain_transfer",
                confidence=0.72,
                address=address,
                chain="tron",
            )
        )
    return hits


def hits_from_trc20(data: dict[str, Any], address: str) -> list[OpenMentionHit]:
    hits: list[OpenMentionHit] = []
    count = data.get("transfer_count", 0)
    source_name = data.get("on_chain_source_ru") or "TronGrid TRC20"
    if count:
        hits.append(
            OpenMentionHit(
                source_type="explorer_tag",
                source_name=source_name,
                title_ru=f"TRC20/USDT · {count} переводов (live)",
                excerpt_ru=f"Live TRC20 ({source_name}): {count} transfers, {len(data.get('counterparties') or [])} контрагентов.",
                url=f"https://tronscan.org/#/address/{address}/transfers",
                risk_tag="trc20_usdt",
                confidence=0.8,
                address=address,
                chain="tron",
            )
        )
    for tr in (data.get("transfers") or [])[:8]:
        hits.append(
            OpenMentionHit(
                source_type="explorer_tag",
                source_name=source_name,
                title_ru=f"USDT → {str(tr.get('to', ''))[:12]}…",
                excerpt_ru=f"tx {str(tr.get('tx_hash', ''))[:16]}…",
                url=f"https://tronscan.org/#/transaction/{tr.get('tx_hash', '')}",
                risk_tag="onchain_transfer",
                confidence=0.75,
                address=address,
                chain="tron",
            )
        )
    return hits


def hits_from_btc(data: dict[str, Any], address: str) -> list[OpenMentionHit]:
    hits: list[OpenMentionHit] = []
    tx_count = data.get("tx_count", 0)
    if tx_count:
        hits.append(
            OpenMentionHit(
                source_type="explorer_tag",
                source_name="mempool.space",
                title_ru=f"BTC · {tx_count} транзакций (live)",
                excerpt_ru=f"mempool.space live: {tx_count} tx, {len(data.get('counterparties') or [])} контрагентов.",
                url=f"https://mempool.space/address/{address}",
                risk_tag="btc_wallet",
                confidence=0.8,
                address=address,
                chain="btc",
            )
        )
    return hits


def hits_from_sanctions(data: dict[str, Any], address: str, chain: str) -> list[OpenMentionHit]:
    if not data.get("flagged"):
        return []
    hits: list[OpenMentionHit] = []
    for h in (data.get("hits") or [])[:5]:
        hits.append(
            OpenMentionHit(
                source_type="web",
                source_name="OpenSanctions",
                title_ru=f"Sanctions hit · {h.get('caption', '')[:80]}",
                excerpt_ru=f"OpenSanctions live match · schema={h.get('schema')}",
                url="https://www.opensanctions.org/",
                risk_tag="sanctions_screening",
                confidence=0.88,
                address=address,
                chain=chain,
            )
        )
    return hits


def hits_from_bitcoinabuse(data: dict[str, Any], address: str) -> list[OpenMentionHit]:
    if not data.get("flagged"):
        return []
    return [
        OpenMentionHit(
            source_type="web",
            source_name="BitcoinAbuse",
            title_ru=f"BitcoinAbuse · {data.get('report_count', 0)} репортов (live)",
            excerpt_ru="Краудсорс abuse-реестр — live API match.",
            url=f"https://www.bitcoinabuse.com/reports?address={address}",
            risk_tag="scam_report",
            confidence=0.85,
            address=address,
            chain="btc",
        )
    ]


def hits_from_maigret(data: dict[str, Any], address: str, chain: str) -> list[OpenMentionHit]:
    hits: list[OpenMentionHit] = []
    for site in (data.get("sites") or [])[:10]:
        hits.append(
            OpenMentionHit(
                source_type="username",
                source_name="Maigret",
                title_ru=f"Профиль · {site.get('site_name', site.get('name', 'site'))}",
                excerpt_ru=f"Live Maigret: {site.get('url', '')[:120]}",
                url=site.get("url"),
                risk_tag="username_match",
                confidence=0.68,
                address=address,
                chain=chain,
            )
        )
    return hits


def hits_from_ahmia(data: dict[str, Any], address: str, chain: str) -> list[OpenMentionHit]:
    hits: list[OpenMentionHit] = []
    for i, url in enumerate((data.get("onion_urls") or [])[:8]):
        hits.append(
            OpenMentionHit(
                source_type="darknet_index",
                source_name="Ahmia · .onion",
                title_ru=f".onion #{i + 1}: {url[:48]}…",
                excerpt_ru=f"Индекс Ahmia: {url}",
                url="https://ahmia.fi/",
                risk_tag="darknet_onion",
                confidence=0.62,
                address=address,
                chain=chain,
            )
        )
    for i, row in enumerate((data.get("results") or [])[:5]):
        hits.append(
            OpenMentionHit(
                source_type="darknet_index",
                source_name="Ahmia",
                title_ru=f"Ahmia index #{i + 1}",
                excerpt_ru=row[:200],
                url="https://ahmia.fi/",
                risk_tag="darknet_mention",
                confidence=0.55,
                address=address,
                chain=chain,
            )
        )
    if data.get("status") not in (200, None) and not hits and data.get("query"):
        hits.append(
            OpenMentionHit(
                source_type="darknet_index",
                source_name="Ahmia",
                title_ru="Darknet index · scan completed",
                excerpt_ru=(
                    f"Ahmia query «{data.get('query', '')[:32]}» · "
                    f"HTTP {data.get('status')} · совпадений .onion: 0"
                ),
                url="https://ahmia.fi/",
                risk_tag="darknet_scan",
                confidence=0.35,
                address=address,
                chain=chain,
            )
        )
    return hits
