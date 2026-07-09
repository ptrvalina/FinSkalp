"""
Открытый OSINT: Telegram, форумы, публичные теги обозревателей, утечки, OTC-индексы.

Дополняет суверенный контур (115-ФЗ) — не заменяет. Низкий приоритет в merge, но сильный
сигнал при совпадении из ≥2 независимых открытых источников.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from flowsint_crypto_compliance.osint_core.open_osint_corpus import OPEN_OSINT_CORPUS
from flowsint_crypto_compliance.registry.cis_vasp_registry import match_vasp_for_address
from flowsint_types.fiat_crypto import Chain, RegistrySource, SovereignRiskLabel

_MENTION_SOURCE_TYPES = frozenset(
    {"telegram", "forum", "leak", "explorer_tag", "darknet_index", "otc_board", "web"}
)

_OPEN_OSINT_TRUST = 0.55


@dataclass
class OpenMentionHit:
    source_type: str
    source_name: str
    title_ru: str
    excerpt_ru: str
    url: str | None
    risk_tag: str
    confidence: float
    observed_at: str | None = None
    address: str = ""
    chain: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "title_ru": self.title_ru,
            "excerpt_ru": self.excerpt_ru,
            "url": self.url,
            "risk_tag": self.risk_tag,
            "confidence": self.confidence,
            "observed_at": self.observed_at,
            "address": self.address,
            "chain": self.chain,
        }


@dataclass
class OpenOSINTResult:
    address: str
    chain: Chain
    mentions: list[OpenMentionHit] = field(default_factory=list)
    proposed_labels: list[SovereignRiskLabel] = field(default_factory=list)
    open_risk_score: float = 0.0
    correlation_score: float = 0.0
    source_status: dict[str, str] = field(default_factory=dict)
    independent_sources: int = 0
    risk_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "chain": self.chain.value,
            "mentions_count": len(self.mentions),
            "mentions": [m.to_dict() for m in self.mentions],
            "open_risk_score": round(self.open_risk_score, 1),
            "correlation_score": round(self.correlation_score, 3),
            "independent_sources": self.independent_sources,
            "risk_tags": self.risk_tags,
            "source_status": self.source_status,
            "proposed_labels": [label.model_dump() for label in self.proposed_labels],
        }


class OpenSourceCollector:
    """Много канальный сбор открытой разведки по криптоадресу (делегирует FinSkalp Scalpel)."""

    def __init__(self, *, timeout: float = 5.0) -> None:
        self._timeout = timeout

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        depth: int = 1,
    ) -> OpenOSINTResult:
        from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine

        engine = ScalpelEngine(timeout=self._timeout)
        scalpel = await engine.collect(
            address, chain, counterparties=counterparties, depth=depth
        )
        return scalpel.to_open_osint_result()


def open_osint_findings(result: OpenOSINTResult, *, fusion: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    fusion = fusion or {}
    composite = float(fusion.get("composite_confidence") or 0.0)
    for m in result.mentions[:15]:
        sev = "high" if m.confidence >= 0.75 else ("medium" if m.confidence >= 0.5 else "low")
        findings.append(
            {
                "code": f"open_osint_{m.source_type}",
                "severity": sev,
                "title_ru": m.title_ru,
                "description_ru": m.excerpt_ru,
                "evidence": f"open_osint:{m.source_type}:{m.source_name}",
                "confidence": m.confidence,
                "source_type": m.source_type,
            }
        )
    if composite >= 0.45 or result.independent_sources >= 2:
        pct = round((composite or result.correlation_score) * 100, 1)
        findings.append(
            {
                "code": "open_osint_correlation",
                "severity": "high" if composite >= 0.65 else "medium",
                "title_ru": "Байесовская корреляция OSINT",
                "description_ru": (
                    f"Скомпонованная уверенность {pct}% из "
                    f"{result.independent_sources} независимых групп источников "
                    f"(метод: {fusion.get('method', 'bayesian_independent_groups')})."
                ),
                "evidence": "open_osint:bayesian_fusion",
                "confidence": composite or min(0.9, result.correlation_score + 0.35),
                "fusion_explain": fusion.get("explain"),
            }
        )
    return findings


def _search_corpus(address: str, chain: Chain) -> list[OpenMentionHit]:
    norm = address.lower() if chain == Chain.ETH else address
    out: list[OpenMentionHit] = []
    for row in OPEN_OSINT_CORPUS:
        if row.chain != chain:
            continue
        key = row.address.lower() if chain == Chain.ETH else row.address
        if key == norm or norm in key or key in norm:
            out.append(
                OpenMentionHit(
                    source_type=row.source_type,
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
            )
    return out


def _search_otc_registry(address: str, chain: Chain) -> list[OpenMentionHit]:
    """Кросс-реф с реестром лицензированных VASP СНГ (публичные регуляторные источники)."""
    entity = match_vasp_for_address(address, chain.value)
    if not entity:
        return []
    risk = entity.get("risk", "medium")
    if risk not in ("severe", "high", "medium", "low"):
        return []
    conf = {"severe": 0.78, "high": 0.68, "medium": 0.58, "low": 0.48}[risk]
    licensed = entity.get("licensed", True)
    tag = "licensed_vasp" if licensed else "otc_exchange"
    regulator = entity.get("regulator", "регулятор СНГ")
    return [
        OpenMentionHit(
            source_type="otc_board",
            source_name=f"{regulator} · {entity['id']}",
            title_ru=f"Реестр VASP СНГ: {entity['legal_name_ru']}",
            excerpt_ru=(
                f"Юрисдикция {entity.get('jurisdiction')}, тип «{entity.get('license_type')}», "
                f"регион {entity.get('region')}, статус {entity.get('status')}. "
                f"Источник: {entity.get('registry_source', 'публичный реестр')}."
            ),
            url=entity.get("registry_source"),
            risk_tag=tag,
            confidence=conf if licensed else conf * 0.85,
            observed_at="2026-04-01",
            address=address,
            chain=chain.value,
        )
    ]


async def _tronscan_intel(address: str, timeout: float) -> tuple[list[OpenMentionHit], str]:
    hits: list[OpenMentionHit] = []
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                "https://apilist.tronscan.org/api/accountv2",
                params={"address": address},
            )
            if resp.status_code != 200:
                return [], f"http:{resp.status_code}"
            data = resp.json()
            tags = data.get("tags") or data.get("tag") or []
            if isinstance(tags, str):
                tags = [tags]
            for tag in tags[:5]:
                hits.append(
                    OpenMentionHit(
                        source_type="explorer_tag",
                        source_name="TronScan",
                        title_ru=f"Публичная метка: {tag}",
                        excerpt_ru=f"TronScan account tag «{tag}» для {address[:12]}…",
                        url=f"https://tronscan.org/#/address/{address}",
                        risk_tag=str(tag).lower().replace(" ", "_"),
                        confidence=0.62,
                        address=address,
                        chain="tron",
                    )
                )
            tx_in = int(data.get("transactions_in", 0) or 0)
            tx_out = int(data.get("transactions_out", 0) or 0)
            if tx_in + tx_out > 100:
                hits.append(
                    OpenMentionHit(
                        source_type="explorer_tag",
                        source_name="TronScan activity",
                        title_ru="Высокая on-chain активность",
                        excerpt_ru=f"TronScan: {tx_in} in / {tx_out} out транзакций.",
                        url=f"https://tronscan.org/#/address/{address}",
                        risk_tag="high_activity",
                        confidence=0.58,
                        address=address,
                        chain="tron",
                    )
                )
            return hits, "ok" if hits else "no_tags"
    except Exception as exc:
        return [], f"error:{exc.__class__.__name__}"


async def _eth_public_intel(address: str, timeout: float) -> tuple[list[OpenMentionHit], str]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                f"https://api.ethplorer.io/getAddressInfo/{address}",
                params={"apiKey": "freekey"},
            )
            if resp.status_code != 200:
                return [], f"http:{resp.status_code}"
            data = resp.json()
            if data.get("error"):
                return [], "api_error"
            hits: list[OpenMentionHit] = []
            count = int(data.get("countTxs", 0) or 0)
            if count > 50:
                hits.append(
                    OpenMentionHit(
                        source_type="explorer_tag",
                        source_name="Ethplorer",
                        title_ru="Активный EOA",
                        excerpt_ru=f"Ethplorer: {count} транзакций по адресу.",
                        url=f"https://ethplorer.io/address/{address}",
                        risk_tag="wallet",
                        confidence=0.55,
                        address=address,
                        chain="eth",
                    )
                )
            return hits, "ok" if hits else "no_data"
    except Exception as exc:
        return [], f"error:{exc.__class__.__name__}"


def _mentions_to_labels(
    address: str, chain: Chain, hits: list[OpenMentionHit]
) -> list[SovereignRiskLabel]:
    if not hits:
        return []
    best = max(hits, key=lambda h: h.confidence)
    disputed = best.confidence < 0.7 or best.source_type in ("forum", "leak")
    category = best.risk_tag or "open_osint"
    label_id = f"open-osint-{hashlib.sha256(address.encode()).hexdigest()[:12]}"
    return [
        SovereignRiskLabel(
            label_id=label_id,
            source=RegistrySource.INTERNAL_OSINT,
            chain=chain,
            address=address,
            entity_name=f"open:{best.source_type}:{best.source_name}",
            category=category,
            risk_score=min(100.0, 40 + len(hits) * 8 + best.confidence * 30),
            confidence=round(min(0.78, _OPEN_OSINT_TRUST + best.confidence * 0.2), 3),
            disputed=disputed,
            snapshot_at=best.observed_at,
        )
    ]


def _open_risk_score(hits: list[OpenMentionHit], correlation: float) -> float:
    if not hits:
        return 0.0
    base = max(h.confidence for h in hits) * 55
    volume = min(35, len(hits) * 6)
    corr_boost = correlation * 25
    severe_tags = sum(1 for h in hits if h.risk_tag in ("mixer_like", "illegal_service", "stolen_coins"))
    return min(100.0, base + volume + corr_boost + severe_tags * 8)


def _dedupe_hits(hits: list[OpenMentionHit]) -> list[OpenMentionHit]:
    seen: set[str] = set()
    out: list[OpenMentionHit] = []
    for h in hits:
        key = f"{h.source_type}:{h.source_name}:{h.title_ru[:40]}"
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return sorted(out, key=lambda x: x.confidence, reverse=True)


def _is_real_tron_address(address: str) -> bool:
    return len(address) == 34 and address.startswith("T") and "_" not in address


def _looks_like_btc(address: str) -> bool:
    return bool(re.match(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$", address))
