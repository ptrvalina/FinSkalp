from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Iterable

from flowsint_types.fiat_crypto import (
    BankRegulatorFeed,
    Chain,
    ControlPurchaseEvent,
    FiatCryptoBridge,
    FiatLegEvent,
    FusedAttribution,
    LicensedPlatformEvent,
    SovereignRiskLabel,
)

from ..engine.bridge_linker import BridgeLinker, BridgeTraceConfig, InvestigationContext
from ..engine.clusterer import ClusterEngine
from ..engine.corridor_analyzer import CorridorAnalyzer
from ..engine.sovereign_attributor import SovereignAttributor
from ..chains.base import ChainAdapter
from ..storage.label_cache import LabelCache
from ..storage.graph_store import EvidenceGraphStore
from .entity_resolver import EntityResolver, _wallet_key
from .evidence_graph import EvidenceGraph, NodeKind
from .link_scorer import LinkScorer
from .merge_engine import MergeEngine


@dataclass
class InvestigationBundle:
    """All ingested data for one regulator case."""

    case_id: str
    bank_feeds: list[BankRegulatorFeed] = field(default_factory=list)
    fiat_events: list[FiatLegEvent] = field(default_factory=list)
    licensed_events: list[LicensedPlatformEvent] = field(default_factory=list)
    control_purchases: list[ControlPurchaseEvent] = field(default_factory=list)
    registry_labels: list[SovereignRiskLabel] = field(default_factory=list)
    open_osint_mentions: list[dict[str, object]] = field(default_factory=list)
    open_osint_address: str | None = None
    open_osint_chain: Chain | None = None


@dataclass
class FusionResult:
    case_id: str
    graph: EvidenceGraph
    attributions: list[FusedAttribution]
    bridges: list[FiatCryptoBridge]
    linkage_scores: list[float]
    corridor_matches: list[dict[str, object]] = field(default_factory=list)
    merge_stats: dict[str, int] = field(default_factory=dict)
    graph_persist: dict[str, object] = field(default_factory=dict)


PhaseCallback = Callable[[str, str, dict[str, object]], Awaitable[None] | None]


class OSINTFusionEngine:
    """
    Central OSINT core: ingest → evidence graph → sovereign + registry merge → bridges.

    This is the main integration point for:
      - Bank feeds via regulator hub
      - Sovereign RF/CIS risk-label registry (115-FZ list, FIU, internal OSINT)
      - Licensed platforms & control purchases
      - Blockchain tracing
    """

    def __init__(
        self,
        *,
        chain_adapters: dict[Chain, ChainAdapter] | None = None,
        label_cache: LabelCache | None = None,
        bridge_config: BridgeTraceConfig | None = None,
    ):
        self._adapters = chain_adapters or {}
        self._cache = label_cache or LabelCache()
        self._bridge_config = bridge_config or BridgeTraceConfig()
        self._merge = MergeEngine()
        self._link_scorer = LinkScorer()
        self._sovereign = SovereignAttributor()
        self._cluster_engine = ClusterEngine()

    @property
    def label_cache(self) -> LabelCache:
        return self._cache

    def load_registry_bulk(self, path: Path) -> int:
        """Load a sovereign risk-label registry snapshot (JSONL) into the cache."""
        count = 0
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                label = _parse_registry_row(row)
                self._cache.put(label)
                count += 1
        return count

    async def fuse(
        self,
        bundle: InvestigationBundle,
        *,
        on_phase: PhaseCallback | None = None,
    ) -> FusionResult:
        graph = EvidenceGraph()
        resolver = EntityResolver(graph)

        for feed in bundle.bank_feeds:
            resolver.ingest_bank_feed(feed)
        for event in bundle.fiat_events:
            resolver.ingest_fiat_event(event)
        for event in bundle.licensed_events:
            resolver.ingest_licensed_event(event)
        for cp in bundle.control_purchases:
            resolver.ingest_control_purchase(cp)

        if bundle.open_osint_mentions and bundle.open_osint_address and bundle.open_osint_chain:
            resolver.ingest_open_osint_mentions(
                bundle.open_osint_address,
                bundle.open_osint_chain,
                bundle.open_osint_mentions,
            )

        await _emit_phase(
            on_phase,
            "ingest",
            "1. Приём и нормализация источников",
            {
                "sources": (
                    len(bundle.bank_feeds)
                    + len(bundle.fiat_events)
                    + len(bundle.licensed_events)
                    + len(bundle.control_purchases)
                ),
                "bank_feeds": len(bundle.bank_feeds),
                "licensed": len(bundle.licensed_events),
                "control_purchases": len(bundle.control_purchases),
            },
        )

        for label in bundle.registry_labels:
            self._cache.put(label)

        labels = list(bundle.registry_labels)
        seen_ids = {label.label_id for label in labels}
        for label in self._cache.all_labels():
            if label.label_id not in seen_ids:
                labels.append(label)
                seen_ids.add(label.label_id)

        for wallet in graph.wallet_nodes():
            addr, chain = _parse_wallet_key(wallet.primary_key)
            cached = self._cache.lookup(chain, addr)
            if cached and cached.label_id not in seen_ids:
                labels.append(cached)
                seen_ids.add(cached.label_id)

        await self._enrich_counterparty_labels(graph, labels, seen_ids)

        for label in labels:
            resolver.ingest_registry_label(label)

        self._infer_bank_platform_links(graph, resolver, bundle)

        await _emit_phase(
            on_phase,
            "entity",
            "2. Резолвер сущностей (кошелёк = кластер)",
            {
                "wallets": len(list(graph.wallet_nodes())),
                "registry_labels": len(labels),
                "subjects": sum(1 for n in graph.nodes if n.kind == NodeKind.SUBJECT),
            },
        )

        merge_preview = 0
        for w in graph.wallet_nodes():
            addr, chain = _parse_wallet_key(w.primary_key)
            if self._cache.lookup(chain, addr):
                merge_preview += 1
        await _emit_phase(
            on_phase,
            "merge",
            "3. Слияние: суверенные > банк > VASP > реестр",
            {
                "registry_hits": merge_preview,
                "merge_conflicts": 0,
            },
        )

        self._cluster_engine.ingest_licensed_events(bundle.licensed_events)
        self._cluster_engine.ingest_control_purchases(bundle.control_purchases)
        clusters = self._cluster_engine.build_clusters(min_confidence=0.25)

        await _emit_phase(
            on_phase,
            "graph",
            "4. Построение графа доказательств",
            {
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
                "clusters": len(clusters),
            },
        )

        region_weights = self._sovereign.ingest_domestic_context(
            fiat_events=bundle.fiat_events,
            licensed_events=bundle.licensed_events,
            control_purchases=bundle.control_purchases,
        )

        attributions: list[FusedAttribution] = []
        linkage_scores: list[float] = []
        merge_conflicts = 0

        bank_paths = graph.bank_to_wallet_paths()
        wallet_bank_links: dict[str, list] = {}
        for bank, edges, wallet in bank_paths:
            ls = self._link_scorer.score_path(bank, edges, wallet)
            linkage_scores.append(ls.score)
            wallet_bank_links.setdefault(wallet.primary_key, []).append(ls)

        strong_links = sum(1 for s in linkage_scores if s >= 0.55)
        await _emit_phase(
            on_phase,
            "link",
            "5. Склейка фиат ↔ крипто (linkage score)",
            {
                "bank_links": strong_links,
                "paths": len(bank_paths),
            },
        )

        for wallet_node in graph.wallet_nodes():
            addr, chain = _parse_wallet_key(wallet_node.primary_key)
            cluster = _find_cluster(addr, chain, clusters)
            corridor_regions = list(region_weights.keys())

            black_assessment = None
            adapter = self._adapters.get(chain)
            if adapter:
                from ..heuristics.black_zone import BlackZoneAnalyzer

                neighborhood = await adapter.get_neighborhood(addr, limit=50)
                black_assessment = BlackZoneAnalyzer().assess(neighborhood)

            sovereign = self._sovereign.attribute_address(
                address=addr,
                chain=chain,
                region_weights=region_weights,
                cluster=cluster,
                corridor_regions=corridor_regions,
                black_assessment=black_assessment,
            )

            registry = self._cache.lookup(chain, addr) or _registry_from_graph(
                graph, wallet_node.primary_key
            )
            links = wallet_bank_links.get(wallet_node.primary_key, [])
            best_link = max(links, key=lambda x: x.score) if links else None
            bank_linked = best_link is not None and best_link.score >= 0.5

            decision = self._merge.merge(
                address=addr,
                sovereign_label=sovereign.entity_label,
                sovereign_confidence=sovereign.confidence,
                sovereign_region=sovereign.primary_region,
                sovereign_kind=sovereign.entity_kind,
                sovereign_evidence=sovereign.evidence,
                registry_entity=registry.entity_name if registry else None,
                registry_source=registry.source.value if registry else None,
                registry_confidence=registry.confidence if registry else 0.0,
                registry_disputed=registry.disputed if registry else False,
                registry_category=registry.category if registry else None,
                registry_sanctioned=registry.sanctioned if registry else False,
                registry_list_reference=registry.list_reference if registry else None,
                linkage_strength=best_link.score if best_link else 0.0,
                bank_linked=bank_linked,
            )
            if registry and registry.disputed and sovereign.entity_label:
                merge_conflicts += 1
            elif any("disputed" in e for e in decision.evidence_chain):
                merge_conflicts += 1

            attributions.append(
                FusedAttribution(
                    attribution_id=str(uuid.uuid4()),
                    address=addr,
                    chain=chain,
                    primary_region=sovereign.primary_region,
                    region_weights=sovereign.region_weights,
                    entity_kind=decision.entity_kind,
                    sovereign_label=decision.sovereign_label,
                    watchlist_label=decision.watchlist_label,
                    label_source=decision.label_source,
                    sanctioned=decision.sanctioned,
                    list_reference=decision.list_reference,
                    disputed=decision.disputed,
                    confidence=decision.confidence,
                    gray_zone=sovereign.gray_zone and decision.confidence < 0.65,
                    black_zone=sovereign.black_zone,
                    bank_feed_ids=[ls.bank_feed_id for ls in links] if links else None,
                    case_id=bundle.case_id,
                    evidence_chain=decision.evidence_chain,
                    linkage_strength=best_link.score if best_link else None,
                )
            )

        black_count = sum(1 for a in attributions if a.black_zone)
        gray_count = sum(1 for a in attributions if a.gray_zone)
        await _emit_phase(
            on_phase,
            "attribute",
            "6. Суверенная атрибуция (РФ/СНГ)",
            {
                "addresses": len(attributions),
                "black_zone": black_count,
                "gray_zone": gray_count,
                "merge_conflicts": merge_conflicts,
            },
        )

        bridges: list[FiatCryptoBridge] = []
        if self._adapters:
            linker = BridgeLinker(self._adapters, self._bridge_config)
            context = await linker.build_context(
                fiat_events=bundle.fiat_events,
                licensed_events=bundle.licensed_events,
                control_purchases=bundle.control_purchases,
            )
            for fiat in bundle.fiat_events:
                bridges.extend(await linker.trace_fiat_event(fiat, context))

        observed_regions = [
            a.primary_region for a in attributions if a.primary_region
        ]
        corridor_analyzer = CorridorAnalyzer()
        corridor_matches = [
            {
                "corridor": list(m.corridor),
                "matched_regions": m.matched_regions,
                "coverage": m.coverage,
                "confidence": m.confidence,
            }
            for m in corridor_analyzer.match(observed_regions)
        ]

        await _emit_phase(
            on_phase,
            "bridge",
            "7. Трансграничные мосты и коридоры",
            {
                "bridges": len(bridges),
                "corridors": len(corridor_matches),
            },
        )

        graph_persist = EvidenceGraphStore().persist(
            graph, case_ref=bundle.case_id, investigation_id=bundle.case_id
        ).to_dict()

        return FusionResult(
            case_id=bundle.case_id,
            graph=graph,
            attributions=attributions,
            bridges=bridges,
            linkage_scores=linkage_scores,
            corridor_matches=corridor_matches,
            merge_stats={
                "conflicts": merge_conflicts,
                "registry_hits": merge_preview,
            },
            graph_persist=graph_persist,
        )

    async def _enrich_counterparty_labels(
        self,
        graph: EvidenceGraph,
        labels: list[SovereignRiskLabel],
        seen_ids: set[str],
    ) -> None:
        """Pull registry hits from on-chain counterparties (1-hop OSINT expansion)."""
        if not self._adapters:
            return
        for wallet in list(graph.wallet_nodes()):
            addr, chain = _parse_wallet_key(wallet.primary_key)
            adapter = self._adapters.get(chain)
            if not adapter:
                continue
            neighborhood = await adapter.get_neighborhood(addr, limit=30)
            counterparties = {
                tx.source for tx in neighborhood.inbound + neighborhood.outbound
            } | {tx.target for tx in neighborhood.inbound + neighborhood.outbound}
            for cp_addr in counterparties:
                if cp_addr == addr:
                    continue
                hit = self._cache.lookup(chain, cp_addr)
                if hit and hit.label_id not in seen_ids:
                    labels.append(hit)
                    seen_ids.add(hit.label_id)

    def _infer_bank_platform_links(
        self,
        graph: EvidenceGraph,
        resolver: EntityResolver,
        bundle: InvestigationBundle,
    ) -> None:
        for feed in bundle.bank_feeds:
            for pe in bundle.licensed_events:
                ls = self._link_scorer.score_bank_platform_wallet(feed, pe)
                if ls.score >= 0.55:
                    resolver.link_bank_to_wallet_by_reference(
                        feed,
                        pe.address,
                        pe.chain,
                        strength=ls.score,
                        evidence=ls.signals,
                    )


def _parse_wallet_key(key: str) -> tuple[str, Chain]:
    chain_str, address = key.split(":", 1)
    return address, Chain(chain_str)


def _find_cluster(address: str, chain: Chain, clusters: Iterable):
    from flowsint_types.fiat_crypto import CryptoCluster

    norm = address.lower() if chain == Chain.ETH else address
    for c in clusters:
        if not c.member_addresses:
            continue
        for m in c.member_addresses:
            if (m.lower() if chain == Chain.ETH else m) == norm:
                return c
    return None


def _registry_from_graph(graph: EvidenceGraph, wallet_key: str) -> SovereignRiskLabel | None:
    wallet = graph.find_node(NodeKind.WALLET, wallet_key)
    if not wallet:
        return None
    for edge in graph.neighbors(wallet.node_id):
        if edge.rel_type == "LABELS_WALLET":
            node = graph.get_node(edge.from_id)
            if node and node.kind == NodeKind.REGISTRY_LABEL:
                return SovereignRiskLabel(**node.payload)
    return None


def _parse_registry_row(row: dict) -> SovereignRiskLabel:
    from ..ingestion.sovereign_registry import parse_registry_row

    return parse_registry_row(row)


async def _emit_phase(
    on_phase: PhaseCallback | None,
    step_id: str,
    label_ru: str,
    detail: dict[str, object],
) -> None:
    if not on_phase:
        return
    result = on_phase(step_id, label_ru, detail)
    if result is not None:
        await result
