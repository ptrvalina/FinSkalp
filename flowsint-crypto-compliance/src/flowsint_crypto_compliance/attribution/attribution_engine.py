"""Main autonomous attribution engine — resolves labels and builds exposure connections."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.attribution.cospend_cluster import (
    build_cospend_clusters,
    propagate_cluster_labels,
)
from flowsint_crypto_compliance.attribution.entity_label_store import EntityLabelStore, get_entity_label_store
from flowsint_crypto_compliance.attribution.open_datasets import bootstrap_open_datasets, lookup_tronscan_tag
from flowsint_crypto_compliance.attribution.types import TIER_HEURISTIC, EntityLabel
from flowsint_crypto_compliance.chains.base import OnChainTransfer
from flowsint_crypto_compliance.engine.exposure_engine import ExposureResult, compute_exposure
from flowsint_crypto_compliance.osint_core.live_collectors import collect_sanctions
from flowsint_crypto_compliance.storage.label_cache import LabelCache
from flowsint_types.fiat_crypto import Chain


@dataclass
class AttributionResult:
    labels: dict[str, EntityLabel] = field(default_factory=dict)
    connections: list[dict[str, Any]] = field(default_factory=list)
    exposure: ExposureResult | None = None
    sanctions_hits: list[dict[str, Any]] = field(default_factory=list)
    source_status: dict[str, str] = field(default_factory=dict)
    tier_summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "labels": {k: v.to_dict() for k, v in self.labels.items()},
            "connections": self.connections,
            "exposure": self.exposure.to_dict() if self.exposure else {},
            "sanctions_hits": self.sanctions_hits,
            "source_status": self.source_status,
            "tier_summary": self.tier_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AttributionResult":
        """Rebuild from wallet screening / onchain_summary attribution payload."""
        if not data:
            return cls()
        labels: dict[str, EntityLabel] = {}
        for addr, raw in (data.get("labels") or {}).items():
            if isinstance(raw, EntityLabel):
                labels[addr] = raw
                continue
            if not isinstance(raw, dict):
                continue
            labels[addr] = EntityLabel(
                address=raw.get("address") or addr,
                chain=raw.get("chain") or "tron",
                label=raw.get("label") or raw.get("entity_name") or "",
                category=(raw.get("category") or "unknown").lower(),
                confidence=float(raw.get("confidence") or 0),
                source=raw.get("source") or "",
                tier=int(raw.get("tier") or 2),
                risk_score=float(raw.get("risk_score") or raw.get("risk_pct") or 15),
                sanctioned=bool(raw.get("sanctioned")),
                evidence=raw.get("evidence"),
                status=raw.get("status") or "active",
            )
        exposure = None
        exp_raw = data.get("exposure")
        if isinstance(exp_raw, dict) and exp_raw:
            exposure = ExposureResult(
                source_of_funds=exp_raw.get("source_of_funds") or {},
                tag_breakdown=exp_raw.get("tag_breakdown") or {},
                connections=list(exp_raw.get("connections") or []),
                indirect_exposure=list(exp_raw.get("indirect_exposure") or []),
                connection_risk_summary=exp_raw.get("connection_risk_summary") or {},
                total_inbound=float(exp_raw.get("total_inbound") or 0),
                total_outbound=float(exp_raw.get("total_outbound") or 0),
                connection_count=int(exp_raw.get("connection_count") or 0),
            )
        return cls(
            labels=labels,
            connections=list(data.get("connections") or []),
            exposure=exposure,
            sanctions_hits=list(data.get("sanctions_hits") or []),
            source_status=dict(data.get("source_status") or {}),
            tier_summary=dict(data.get("tier_summary") or {}),
        )


class AttributionEngine:
    def __init__(
        self,
        store: EntityLabelStore | None = None,
        label_cache: LabelCache | None = None,
    ) -> None:
        self._store = store or get_entity_label_store()
        self._label_cache = label_cache
        self._bootstrapped = False

    async def ensure_bootstrap(self) -> dict[str, Any]:
        if self._bootstrapped:
            return {"status": "ok", "total": self._store.count()}
        stats = await bootstrap_open_datasets(self._store)
        self._bootstrapped = True
        stats["ofac_bootstrap"] = "ok"
        return stats

    async def attribute_wallet(
        self,
        *,
        address: str,
        chain: str,
        inbound: list[OnChainTransfer],
        outbound: list[OnChainTransfer],
        transfers_raw: list[dict[str, Any]] | None = None,
    ) -> AttributionResult:
        await self.ensure_bootstrap()
        result = AttributionResult()
        chain_enum = Chain(chain)

        # Tier-1: sanctions on focus + counterparties (parallel, rate-limited)
        await self._check_sanctions(address, chain, result)
        cps = self._counterparties(address, inbound, outbound)
        sem = asyncio.Semaphore(8)

        async def _screen_cp(cp: str) -> None:
            async with sem:
                await self._check_sanctions(cp, chain, result)

        await asyncio.gather(*[_screen_cp(cp) for cp in cps[:40]], return_exceptions=True)

        # Open dataset + store lookups
        for cp in [address, *cps]:
            lbl = self._store.lookup(chain, cp)
            if lbl:
                result.labels[cp] = lbl
            elif chain == "tron" and cp == address:
                live = await lookup_tronscan_tag(cp)
                if live:
                    self._store.upsert(live)
                    result.labels[cp] = live
                    result.source_status["tronscan"] = "hit"

        # Sovereign / KYT cache merge
        if self._label_cache:
            for cp in [address, *cps]:
                sl = self._label_cache.lookup(chain_enum, cp)
                if sl and (sl.entity_name or sl.category):
                    el = EntityLabel(
                        address=cp,
                        chain=chain,
                        label=sl.entity_name or sl.category or "registry",
                        category=(sl.category or "other").lower(),
                        confidence=sl.confidence,
                        source="sovereign_registry" if sl.source.value != "internal_osint" else "kyt_import",
                        tier=1 if sl.sanctioned else 2,
                        risk_score=sl.risk_score or 30.0,
                        sanctioned=sl.sanctioned,
                        evidence=f"registry:{sl.source.value}",
                    )
                    self._store.upsert(el)
                    result.labels[cp] = el

        # Co-spend clustering propagation
        raw = transfers_raw or self._transfers_to_raw(inbound, outbound)
        from flowsint_crypto_compliance.infrastructure.feature_flags import FlagContext, get_feature_flags

        flags = get_feature_flags()
        ctx = FlagContext(user_id=address, properties={"chain": chain})
        cospend_v2 = flags.is_enabled("finskalp.cospend_v2", ctx)
        clusters = build_cospend_clusters(
            raw,
            chain=chain,
            focus_address=address,
            use_evm_v2=cospend_v2,
            block_window=1 if cospend_v2 else None,
        )
        propagated = propagate_cluster_labels(clusters, result.labels, chain=chain)
        for lbl in propagated:
            if self._store.upsert(lbl):
                result.labels[lbl.address] = lbl
        if propagated:
            result.source_status["cospend_cluster"] = f"clusters:{len(clusters)}"

        # Build connections for exposure (direct + 1-hop indirect via labeled intermediaries)
        result.connections = self._build_connections(address, chain, inbound, outbound, result.labels)

        # Exposure from real labels (no imported sample required)
        result.exposure = compute_exposure(
            focus_address=address,
            chain=chain_enum,
            inbound=inbound,
            outbound=outbound,
            label_lookup=lambda a: self._label_for_exposure(chain_enum, a, result.labels),
            imported_exposure=None,
        )
        # Override connections in exposure with richer attribution data
        if result.connections:
            result.exposure.indirect_exposure = result.connections[:15]
            result.exposure.connection_count = len(result.connections)

        result.tier_summary = {
            "tier_1": sum(1 for l in result.labels.values() if l.tier == 1),
            "tier_2": sum(1 for l in result.labels.values() if l.tier == 2),
            "tier_3": sum(1 for l in result.labels.values() if l.tier >= 3),
        }
        return result

    async def _check_sanctions(self, address: str, chain: str, result: AttributionResult) -> None:
        store_hit = self._store.lookup(chain, address)
        if store_hit and store_hit.sanctioned:
            result.labels[address] = store_hit
            result.sanctions_hits.append(
                {"address": address, "source": store_hit.source, "label": store_hit.label}
            )
            if "ofac" in str(store_hit.source).lower():
                result.source_status["ofac_store"] = "hit"
            return
        if self._bootstrapped:
            result.source_status.setdefault("ofac_store", "no_match")
        try:
            data = await collect_sanctions(address)
            if data.get("degraded") or data.get("status") not in (200, None):
                st = data.get("status", 0)
                result.source_status["opensanctions_api"] = (
                    f"degraded:{st}" if st else "degraded:network"
                )
            else:
                result.source_status["opensanctions_api"] = "ok"
            if not data.get("flagged"):
                return
            hits = data.get("hits") or []
            matched = [h for h in hits if _address_in_sanctions_hit(address, h)]
            if not matched and hits:
                # Weak match — do not auto-sanction, tier-3 note only
                return
            for h in matched:
                lbl = EntityLabel(
                    address=address,
                    chain=chain,
                    label=h.get("caption") or "Sanctions hit",
                    category="sanctions",
                    confidence=0.95,
                    source="opensanctions",
                    tier=1,
                    risk_score=95.0,
                    sanctioned=True,
                    evidence=f"opensanctions:{h.get('id', '')}",
                )
                self._store.upsert(lbl, force=True)
                result.labels[address] = lbl
                result.sanctions_hits.append(
                    {"address": address, "caption": h.get("caption"), "id": h.get("id")}
                )
        except Exception as exc:
            result.source_status["opensanctions_api"] = f"error:{exc.__class__.__name__}"

    def _build_connections(
        self,
        focus: str,
        chain: str,
        inbound: list[OnChainTransfer],
        outbound: list[OnChainTransfer],
        labels: dict[str, EntityLabel],
    ) -> list[dict[str, Any]]:
        conns: dict[str, dict[str, Any]] = {}
        for tx in inbound:
            cp = tx.source
            if not cp or cp == focus:
                continue
            lbl = labels.get(cp)
            key = lbl.label if lbl else cp
            tier = lbl.tier if lbl else 3
            cat = lbl.category if lbl else "unknown"
            risk = lbl.risk_score if lbl else 0.0
            if key not in conns:
                conns[key] = {
                    "entity_name": lbl.label if lbl else cp[:8] + "…",
                    "address": cp,
                    "category": cat,
                    "total_received": 0.0,
                    "hops": 1,
                    "behavior": "direct",
                    "risk_pct": risk,
                    "risk_tier": _tier_name(tier, cat, risk),
                    "tier": tier,
                    "confidence": lbl.confidence if lbl else 0.0,
                    "source": lbl.source if lbl else "unattributed",
                }
            conns[key]["total_received"] += tx.amount or 0.0

        # Indirect: labeled intermediary one hop away
        for tx in inbound:
            cp = tx.source
            if not cp:
                continue
            for tx2 in inbound:
                mid = tx2.source
                if mid and mid != focus and mid != cp and labels.get(mid):
                    lbl = labels[mid]
                    key = f"indirect:{lbl.label}"
                    amt = min(tx.amount or 0, tx2.amount or 0) * 0.5
                    if key not in conns:
                        conns[key] = {
                            "entity_name": lbl.label,
                            "address": mid,
                            "category": lbl.category,
                            "total_received": 0.0,
                            "hops": 2,
                            "behavior": "indirect",
                            "risk_pct": lbl.risk_score,
                            "risk_tier": _tier_name(lbl.tier, lbl.category, lbl.risk_score),
                            "tier": lbl.tier,
                            "confidence": lbl.confidence,
                            "source": lbl.source,
                        }
                    conns[key]["total_received"] += amt

        return sorted(conns.values(), key=lambda c: c["total_received"], reverse=True)

    def enrich_graph(self, graph: dict[str, Any], attribution: AttributionResult) -> dict[str, Any]:
        """Attach label, risk_score, category to each node."""
        labels = dict(attribution.labels)
        conn_by_addr = {
            c["address"]: c for c in (attribution.connections or []) if c.get("address")
        }
        for node in graph.get("nodes") or []:
            addr = (node.get("address") or "").strip()
            chain = (node.get("chain") or "tron").lower()
            lbl = labels.get(addr)
            if not lbl:
                lbl = self._store.lookup(chain, addr)
            conn = conn_by_addr.get(addr)
            if lbl:
                node["label"] = lbl.label or node.get("label")
                node["category"] = lbl.category or "other"
                node["risk_score"] = float(lbl.risk_score or 15)
                node["tier"] = lbl.tier
                node["sanctioned"] = lbl.sanctioned
                node["attribution_source"] = lbl.source
                node["confidence_pct"] = round(float(lbl.confidence or 0) * 100, 1)
            elif conn:
                node["label"] = conn.get("entity_name") or node.get("label")
                node["category"] = (conn.get("category") or _category_from_entity(conn)).lower()
                node["risk_score"] = float(conn.get("risk_pct") or conn.get("risk_score") or 20)
                node["tier"] = conn.get("tier") or 2
                node["attribution_source"] = conn.get("source") or "ledger"
                node["confidence_pct"] = round(float(conn.get("confidence") or 0) * 100, 1)
            elif node.get("hop") == 0:
                node.setdefault("category", "subject")
                node.setdefault("risk_score", 15.0)
            else:
                node.setdefault("risk_score", 15.0)
                node.setdefault("category", "eoa")
        _attach_node_activity_sparklines(graph)
        graph["attribution"] = attribution.to_dict()
        return graph

    def _label_for_exposure(self, chain: Chain, address: str, labels: dict[str, EntityLabel]):
        lbl = labels.get(address)
        if not lbl:
            return None
        return self._store.to_sovereign_dict(lbl)

    def sync_to_label_cache(self, attribution: AttributionResult) -> int:
        if not self._label_cache:
            return 0
        n = 0
        for lbl in attribution.labels.values():
            self._label_cache.put(self._store.to_sovereign_dict(lbl))
            n += 1
        return n

    @staticmethod
    def _counterparties(
        focus: str, inbound: list[OnChainTransfer], outbound: list[OnChainTransfer]
    ) -> list[str]:
        cps: set[str] = set()
        for tx in inbound:
            if tx.source and tx.source != focus:
                cps.add(tx.source)
        for tx in outbound:
            if tx.target and tx.target != focus:
                cps.add(tx.target)
        return sorted(cps)

    @staticmethod
    def _transfers_to_raw(
        inbound: list[OnChainTransfer], outbound: list[OnChainTransfer]
    ) -> list[dict[str, Any]]:
        raw = []
        for tx in [*inbound, *outbound]:
            raw.append(
                {
                    "from": tx.source,
                    "to": tx.target,
                    "tx_hash": tx.tx_hash,
                    "amount": tx.amount,
                    "timestamp": tx.timestamp,
                }
            )
        return raw

    def _to_sovereign_lookup(self, chain: Chain, lbl: EntityLabel | None):
        if not lbl:
            return None
        return self._store.to_sovereign_dict(lbl)


def _category_from_entity(conn: dict[str, Any]) -> str:
    name = str(conn.get("entity_name") or "").lower()
    tier = conn.get("tier")
    risk_tier = str(conn.get("risk_tier") or "").lower()
    if tier == 1 or risk_tier in ("severe", "critical"):
        return "sanctions"
    if "binance" in name or "exchange" in name or "okx" in name:
        return "exchange"
    if "gambl" in name or "casino" in name:
        return "gambling"
    if "mixer" in name or "tornado" in name:
        return "mixer"
    if conn.get("behavior") == "indirect":
        return "indirect"
    return "counterparty"


def _attach_node_activity_sparklines(graph: dict[str, Any]) -> None:
    """Mini sparkline buckets from edge timestamps per node."""
    buckets: dict[str, list[int]] = {}
    for e in graph.get("edges") or []:
        ts = e.get("timestamp")
        if not ts:
            continue
        try:
            if isinstance(ts, (int, float)):
                bucket = int(ts) // 86400
            else:
                from datetime import datetime

                bucket = int(datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp() // 86400)
        except (ValueError, TypeError, OSError):
            continue
        for nid in (e.get("from"), e.get("to"), e.get("source"), e.get("target")):
            if nid:
                buckets.setdefault(str(nid), []).append(bucket)
    for node in graph.get("nodes") or []:
        nid = node.get("id")
        if not nid or nid not in buckets:
            continue
        hist: dict[int, int] = {}
        for b in buckets[nid]:
            hist[b] = hist.get(b, 0) + 1
        ordered = [hist[k] for k in sorted(hist.keys())[-12:]]
        if ordered:
            node["activity_sparkline"] = ordered


def _tier_name(tier: int, category: str, risk: float) -> str:
    if tier == 1 or category == "sanctions":
        return "severe"
    if risk >= 65 or category in ("gambling", "mixer"):
        return "high"
    if risk >= 35:
        return "moderate"
    return "low"


def _address_in_sanctions_hit(address: str, hit: dict[str, Any]) -> bool:
    cap = str(hit.get("caption") or "").lower()
    if address.lower() in cap:
        return True
    # OpenSanctions search may return entity names — require explicit wallet property match elsewhere
    return False
