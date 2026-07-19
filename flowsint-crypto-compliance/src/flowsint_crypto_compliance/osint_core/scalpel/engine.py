"""
FinSkalp Scalpel — суверенный OSINT-движок.

Параллельный запуск коллекторов (SpiderFoot-style), Tor/I2P шлюз,
отсев мусора, извлечение сущностей, объёмная агрегация.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.osint_core.open_source_collector import (
    OpenMentionHit,
    OpenOSINTResult,
    _dedupe_hits,
    _mentions_to_labels,
    _open_risk_score,
)
from flowsint_crypto_compliance.osint_core.scalpel.entity_dedup import dedupe_mentions_by_excerpt
from flowsint_crypto_compliance.osint_core.scalpel.legal_policy import ALLOWED_SOURCE_CATEGORIES
from flowsint_crypto_compliance.osint_core.scalpel.ml_scoring import score_risk
from flowsint_crypto_compliance.osint_core.scalpel.evidence_bridge import (
    build_scalpel_evidence_graph,
    scalpel_case_ref,
    serialize_evidence_graph,
)
from flowsint_crypto_compliance.storage.graph_store import EvidenceGraphStore
from flowsint_crypto_compliance.osint_core.scalpel.registry import (
    SCALPEL_COLLECTORS,
    registry_manifest,
)
from flowsint_crypto_compliance.osint_core.scalpel.entity_extractor import (
    ExtractedEntities,
    extract_entities,
)
from flowsint_crypto_compliance.osint_core.scalpel.network_gateway import (
    NetworkGateway,
    NetworkGatewayConfig,
)
from flowsint_crypto_compliance.osint.fusion_confidence import (
    correlation_score_from_fusion,
    fuse_mention_hits,
)
from flowsint_crypto_compliance.osint.multilingual import enrich_mention_text
from flowsint_crypto_compliance.osint.query_expansion import expand_osint_queries
from flowsint_crypto_compliance.osint.source_reliability import load_reliability_map
from flowsint_crypto_compliance.osint_core.scalpel.noise_filter import filter_osint_noise
from flowsint_types.fiat_crypto import Chain, RegistrySource, SovereignRiskLabel

_MENTION_SOURCE_TYPES = frozenset(
    {
        "telegram",
        "forum",
        "leak",
        "explorer_tag",
        "darknet_index",
        "otc_board",
        "web",
        "paste",
        "clearnet_dork",
        "username",
    }
)


@dataclass
class ScalpelResult:
    address: str
    chain: Chain
    mentions: list[OpenMentionHit] = field(default_factory=list)
    rejected_junk: list[dict[str, Any]] = field(default_factory=list)
    proposed_labels: list[SovereignRiskLabel] = field(default_factory=list)
    open_risk_score: float = 0.0
    correlation_score: float = 0.0
    source_status: dict[str, str] = field(default_factory=dict)
    independent_sources: int = 0
    risk_tags: list[str] = field(default_factory=list)
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    noise_filter: dict[str, Any] = field(default_factory=dict)
    network: dict[str, Any] = field(default_factory=dict)
    collectors_run: list[str] = field(default_factory=list)
    osint_depth: int = 1
    branch_targets: list[str] = field(default_factory=list)
    ml_risk_score: float = 0.0
    ml_detail: dict[str, Any] = field(default_factory=dict)
    graph_persist: dict[str, Any] = field(default_factory=dict)
    evidence_graph: dict[str, Any] = field(default_factory=dict)
    fusion_confidence: dict[str, Any] = field(default_factory=dict)
    query_expansion: dict[str, Any] = field(default_factory=dict)
    scalpel_version: str = "2.2.0-live"

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": "FinSkalp Scalpel",
            "scalpel_version": self.scalpel_version,
            "address": self.address,
            "chain": self.chain.value,
            "mentions_count": len(self.mentions),
            "mentions": [m.to_dict() for m in self.mentions],
            "rejected_junk_count": len(self.rejected_junk),
            "rejected_junk_sample": self.rejected_junk[:15],
            "open_risk_score": round(self.open_risk_score, 1),
            "correlation_score": round(self.correlation_score, 3),
            "independent_sources": self.independent_sources,
            "risk_tags": self.risk_tags,
            "source_status": self.source_status,
            "proposed_labels": [label.model_dump() for label in self.proposed_labels],
            "extracted_entities": self.extracted_entities,
            "noise_filter": self.noise_filter,
            "network": self.network,
            "collectors_run": self.collectors_run,
            "osint_depth": self.osint_depth,
            "branch_targets": self.branch_targets,
            "ml_risk_score": round(self.ml_risk_score, 1),
            "ml_detail": self.ml_detail,
            "graph_persist": self.graph_persist,
            "evidence_graph": self.evidence_graph,
            "fusion_confidence": self.fusion_confidence,
            "query_expansion": self.query_expansion,
            "legal_collectors": registry_manifest(),
            "open_source_stack": [
                "On-chain Explorer (TronGrid, mempool, Blockchair)",
                "Sanctions & Watchlist (OpenSanctions, OFAC)",
                "Username/Social (Maigret, Sherlock)",
                "Abuse/Scam Registry (Chainabuse, crowd reports)",
                "Darknet Index (Ahmia.fi only)",
                "VASP Registry (ЦБ РФ, NAPP, AFSA, СНГ)",
                "Court/Enforcement (DOJ, Europol public releases)",
                "Reverse WHOIS / DNS (RDAP)",
            ],
        }

    def to_open_osint_result(self) -> OpenOSINTResult:
        return OpenOSINTResult(
            address=self.address,
            chain=self.chain,
            mentions=self.mentions,
            proposed_labels=self.proposed_labels,
            open_risk_score=self.open_risk_score,
            correlation_score=self.correlation_score,
            source_status=self.source_status,
            independent_sources=self.independent_sources,
            risk_tags=self.risk_tags,
        )


class ScalpelEngine:
    """Главный OSINT-скальпель FinSkalp."""

    def __init__(
        self,
        *,
        gateway: NetworkGateway | None = None,
        timeout: float = 8.0,
    ) -> None:
        cfg = NetworkGatewayConfig.from_env()
        cfg.timeout_sec = timeout
        self._gw = gateway or NetworkGateway(config=cfg)
        self._collectors = [cls(self._gw) for cls in SCALPEL_COLLECTORS]

    def status(self) -> dict[str, Any]:
        return {
            "engine": "FinSkalp Scalpel",
            "scalpel_version": "2.2.0-live",
            "collectors": registry_manifest(),
            "legal_policy": ALLOWED_SOURCE_CATEGORIES,
            "network": self._gw.status(),
        }

    async def collect(
        self,
        address: str,
        chain: Chain,
        *,
        counterparties: list[str] | None = None,
        depth: int = 1,
        collectors: list[str] | None = None,
        usernames: list[str] | None = None,
    ) -> ScalpelResult:
        depth = max(1, min(3, int(depth)))
        active = self._select_collectors(collectors)
        if not active:
            raise ValueError("Не выбран ни один OSINT-коллектор")

        cps = list(dict.fromkeys(counterparties or [])) if depth >= 2 else []
        branch_targets: list[str] = []
        raw_hits: list[OpenMentionHit] = []
        status: dict[str, str] = {}
        all_entities: dict[str, Any] = {}
        collectors_run: list[str] = []
        expansion = expand_osint_queries(
            address=address,
            chain=chain.value,
            co_spend_aliases=cps,
            prior_usernames=usernames,
        )
        context: dict[str, Any] = {
            "usernames": expansion.get("usernames") or list(usernames or []),
            "domains": expansion.get("domains") or [],
            "mentions": [],
            "osint_depth": depth,
            "branch_wave": 0,
            "expanded_addresses": expansion.get("expanded_addresses") or [address],
        }

        async def _run_wave(
            target: str,
            wave_cps: list[str] | None,
            *,
            wave: int,
            only_ids: set[str] | None = None,
        ) -> None:
            context["branch_wave"] = wave
            wave_collectors = active
            if only_ids is not None:
                wave_collectors = [c for c in active if c.collector_id in only_ids]
            if not wave_collectors:
                return

            async def _run_one(collector: Any) -> None:
                key = collector.collector_id if wave == 0 else f"{collector.collector_id}:hop{wave}"
                collector_timeout = float(
                    os.getenv("FINSKALP_COLLECTOR_TIMEOUT_SEC", "55")
                )
                try:
                    res = await asyncio.wait_for(
                        collector.collect(
                            target,
                            chain,
                            counterparties=wave_cps if wave_cps else None,
                            context=context,
                        ),
                        timeout=collector_timeout,
                    )
                    tag = f"{collector.collector_id}@hop{wave}" if wave else collector.collector_id
                    if tag not in collectors_run:
                        collectors_run.append(tag)
                    status[key] = res.to_status()
                    raw_hits.extend(res.hits)
                    if res.entities:
                        all_entities[key] = res.entities
                    context["mentions"].extend([h.to_dict() for h in res.hits])
                except asyncio.TimeoutError:
                    status[key] = "timeout"
                except Exception as exc:
                    status[key] = f"error:{exc.__class__.__name__}"

            await asyncio.gather(*[_run_one(c) for c in wave_collectors])

        await _run_wave(address, cps[:12] if cps else None, wave=0)

        partial_wave0 = dedupe_mentions_by_excerpt(_dedupe_hits(raw_hits))
        _enrich_context_from_hits(context, partial_wave0, all_entities, address)

        # Promote on-chain counterparties into branch targets (depth≥2)
        if depth >= 2:
            for key, payload in all_entities.items():
                if not isinstance(payload, dict):
                    continue
                for cp in payload.get("counterparties") or []:
                    addr = str(cp).strip()
                    if addr and addr != address and addr not in branch_targets:
                        branch_targets.append(addr)
                for tr in payload.get("transfers") or []:
                    if not isinstance(tr, dict):
                        continue
                    for side in (tr.get("from"), tr.get("to")):
                        addr = str(side or "").strip()
                        if addr and addr != address and addr not in branch_targets:
                            branch_targets.append(addr)

        if depth >= 2:
            hop1_ids: set[str] = set()
            active_ids = {c.collector_id for c in active}
            if context.get("usernames"):
                if "username_social" in active_ids:
                    hop1_ids.add("username_social")
                if "username_probe" in active_ids:
                    hop1_ids.add("username_probe")
            if "reverse_whois_dns" in active_ids and context.get("domains"):
                hop1_ids.add("reverse_whois_dns")
            # Screen top counterparties for sanctions/abuse/VASP at hop-1
            screen_ids = {"sanctions_watchlist", "abuse_scam_registry", "vasp_registry"} & active_ids
            if hop1_ids:
                await _run_wave(address, None, wave=1, only_ids=hop1_ids)
            for cp in branch_targets[:8]:
                if screen_ids:
                    await _run_wave(cp, None, wave=1, only_ids=screen_ids)

        if depth >= 3:
            branch_ids = {
                "onchain_explorer",
                "sanctions_watchlist",
                "abuse_scam_registry",
                "vasp_registry",
            }
            for cp in cps[:8]:
                if cp != address and cp not in branch_targets:
                    branch_targets.append(cp)
            partial_hits = dedupe_mentions_by_excerpt(_dedupe_hits(raw_hits))
            merged_pre = _merge_extracted(partial_hits, all_entities, address)
            for item in merged_pre.get("aggregate", {}).get("crypto_addresses", []):
                addr = (item.get("address") or "").strip()
                if addr and addr != address and addr not in branch_targets:
                    branch_targets.append(addr)
            for bt in branch_targets[:6]:
                await _run_wave(bt, None, wave=2, only_ids=branch_ids)

        noise = filter_osint_noise(raw_hits, target_address=address)
        hits = dedupe_mentions_by_excerpt(_dedupe_hits(noise.kept))

        merged_entities = _merge_extracted(hits, all_entities, address)
        labels = _mentions_to_labels(address, chain, hits)
        tags = sorted({h.risk_tag for h in hits if h.risk_tag})
        for i, h in enumerate(hits):
            enriched = enrich_mention_text(h.to_dict())
            if enriched.get("text_ru") and enriched["text_ru"] != h.excerpt_ru:
                h.excerpt_ru = enriched["text_ru"][:500]

        reliability_map = load_reliability_map()
        fusion_out = fuse_mention_hits(hits, reliability_map=reliability_map)
        indep = fusion_out.independent_groups
        corr = correlation_score_from_fusion(fusion_out)
        if noise.quality_score > 0.7:
            corr = min(1.0, corr + 0.05)
        open_score = _open_risk_score(hits, corr)
        open_score = min(
            100.0,
            open_score * (0.75 + fusion_out.composite_confidence * 0.25),
        )
        if noise.quality_score > 0:
            open_score = min(100.0, open_score * (0.85 + noise.quality_score * 0.15))

        partial = ScalpelResult(
            address=address,
            chain=chain,
            mentions=hits,
            proposed_labels=labels,
            extracted_entities=merged_entities,
        )
        evidence_graph = build_scalpel_evidence_graph(partial)
        evidence_graph_payload = serialize_evidence_graph(evidence_graph)
        ml_out = score_risk(
            address,
            chain.value,
            hits,
            graph=evidence_graph,
            wallet_primary_key=f"{chain.value}:{address}",
        )
        case_ref = scalpel_case_ref(address, chain)
        graph_out = EvidenceGraphStore().persist(evidence_graph, case_ref=case_ref)

        return ScalpelResult(
            address=address,
            chain=chain,
            mentions=hits,
            rejected_junk=noise.rejected,
            proposed_labels=labels,
            open_risk_score=open_score,
            ml_risk_score=float(ml_out["score"]),
            ml_detail=ml_out,
            graph_persist=graph_out.to_dict(),
            evidence_graph=evidence_graph_payload,
            correlation_score=corr,
            source_status=status,
            independent_sources=indep,
            risk_tags=tags,
            extracted_entities=merged_entities,
            noise_filter=noise.to_dict(),
            network=self._gw.status(),
            collectors_run=collectors_run,
            osint_depth=depth,
            branch_targets=branch_targets[:12],
            fusion_confidence=fusion_out.to_dict(),
            query_expansion=expansion,
            scalpel_version="2.4.0-fusion",
        )

    def _select_collectors(self, collectors: list[str] | None) -> list[Any]:
        if collectors is None:
            return list(self._collectors)
        allowed = {c.strip().lower().replace("-", "_") for c in collectors if c and c.strip()}
        if not allowed:
            return []
        return [c for c in self._collectors if c.collector_id in allowed]


def _merge_extracted(
    hits: list[OpenMentionHit],
    by_collector: dict[str, Any],
    address: str,
) -> dict[str, Any]:
    agg = ExtractedEntities()
    for h in hits:
        ex = extract_entities(f"{h.title_ru} {h.excerpt_ru}", context_address=address)
        agg.crypto_addresses.extend(ex.crypto_addresses)
        agg.inn.extend(ex.inn)
        agg.phones.extend(ex.phones)
        agg.emails.extend(ex.emails)
        agg.usernames.extend(ex.usernames)
        agg.domains.extend(ex.domains)
        agg.amounts.extend(ex.amounts)

    agg.crypto_addresses = _uniq_dicts(agg.crypto_addresses, "address")[:50]
    agg.inn = list(dict.fromkeys(agg.inn))[:20]
    agg.phones = list(dict.fromkeys(agg.phones))[:15]
    agg.emails = list(dict.fromkeys(agg.emails))[:15]
    agg.usernames = list(dict.fromkeys(agg.usernames))[:10]
    agg.domains = list(dict.fromkeys(agg.domains))[:12]

    return {
        "aggregate": agg.to_dict(),
        "by_collector": by_collector,
        "extraction_id": hashlib.sha256(address.encode()).hexdigest()[:16],
    }


def _enrich_context_from_hits(
    context: dict[str, Any],
    hits: list[OpenMentionHit],
    by_collector: dict[str, Any],
    address: str,
) -> None:
    """Merge wave-0 entities into context for hop-1 username/DNS collectors."""
    from urllib.parse import urlparse

    context.setdefault("usernames", [])
    context.setdefault("domains", [])
    seen_u = {str(u).lstrip("@").lower() for u in context["usernames"]}
    seen_d = {str(d).lower() for d in context["domains"]}

    merged = _merge_extracted(hits, by_collector, address)
    agg = merged.get("aggregate", {})
    for u in agg.get("usernames") or []:
        key = str(u).lstrip("@").lower()
        if key and key not in seen_u:
            seen_u.add(key)
            context["usernames"].append(str(u).lstrip("@"))
    for d in agg.get("domains") or []:
        key = str(d).lower()
        if key and key not in seen_d:
            seen_d.add(key)
            context["domains"].append(key)

    for mention in context.get("mentions") or []:
        url = (mention.get("url") or "") if isinstance(mention, dict) else ""
        if "://" not in url:
            continue
        host = (urlparse(url).hostname or "").lower()
        if host and host not in seen_d:
            seen_d.add(host)
            context["domains"].append(host)


def _uniq_dicts(items: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for d in items:
        k = d.get(key, "")
        if k and k not in seen:
            seen.add(k)
            out.append(d)
    return out
