from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterable, Optional

from flowsint_types.fiat_crypto import (
    Chain,
    ControlPurchaseEvent,
    CryptoCluster,
    EvidenceSource,
    FiatCryptoBridge,
    FiatLegEvent,
    LicensedPlatformEvent,
)

from ..chains.base import ChainAdapter, OnChainTransfer
from .clusterer import ClusterEngine
from .region_profiler import RegionProfiler


@dataclass
class BridgeTraceConfig:
    max_hops: int = 6
    min_bridge_confidence: float = 0.35


@dataclass
class InvestigationContext:
    fiat_events: list[FiatLegEvent] = field(default_factory=list)
    licensed_events: list[LicensedPlatformEvent] = field(default_factory=list)
    control_purchases: list[ControlPurchaseEvent] = field(default_factory=list)
    clusters: list[CryptoCluster] = field(default_factory=list)


class BridgeLinker:
    """
  Core engine: link fiat signals to on-chain paths and reduce gray-zone uncertainty.
    """

    def __init__(
        self,
        adapters: dict[Chain, ChainAdapter],
        config: Optional[BridgeTraceConfig] = None,
    ):
        self._adapters = adapters
        self._config = config or BridgeTraceConfig()
        self._cluster_engine = ClusterEngine()
        self._region_profiler = RegionProfiler()

    async def build_context(
        self,
        *,
        fiat_events: Iterable[FiatLegEvent],
        licensed_events: Iterable[LicensedPlatformEvent],
        control_purchases: Iterable[ControlPurchaseEvent],
    ) -> InvestigationContext:
        fiat_list = list(fiat_events)
        licensed_list = list(licensed_events)
        control_list = list(control_purchases)

        self._cluster_engine.ingest_licensed_events(licensed_list)
        self._cluster_engine.ingest_control_purchases(control_list)

        for event in licensed_list:
            if event.region:
                self._region_profiler.record_flow(
                    from_region=event.region,
                    chain=event.chain,
                    to_address=event.address,
                    source=EvidenceSource.LICENSED_PLATFORM,
                )

        for event in control_list:
            self._region_profiler.record_flow(
                from_region=event.region,
                chain=event.chain,
                to_address=event.target_address,
                source=EvidenceSource.CONTROL_PURCHASE,
            )
            if event.source_address:
                self._region_profiler.record_flow(
                    from_region=event.region,
                    chain=event.chain,
                    to_address=event.source_address,
                    source=EvidenceSource.CONTROL_PURCHASE,
                    weight=0.5,
                )

        for event in fiat_list:
            if event.region and event.platform_id:
                matching = [
                    le
                    for le in licensed_list
                    if le.platform_name == event.platform_id or le.platform_license_id == event.platform_id
                ]
                for le in matching:
                    self._region_profiler.record_flow(
                        from_region=event.region,
                        chain=le.chain,
                        to_address=le.address,
                        source=event.source,
                    )

        clusters = self._cluster_engine.build_clusters(
            min_confidence=self._config.min_bridge_confidence
        )
        chain_by_cluster: dict[str, Chain] = {}
        for cluster in clusters:
            if cluster.member_addresses:
                # Infer chain from cluster_id prefix
                chain_str = cluster.cluster_id.split("_", 1)[0]
                chain = Chain(chain_str)
                chain_by_cluster[cluster.cluster_id] = chain
                self._region_profiler.apply_to_cluster(cluster, chain)

        return InvestigationContext(
            fiat_events=fiat_list,
            licensed_events=licensed_list,
            control_purchases=control_list,
            clusters=clusters,
        )

    async def trace_fiat_event(
        self,
        event: FiatLegEvent,
        context: InvestigationContext,
    ) -> list[FiatCryptoBridge]:
        bridges: list[FiatCryptoBridge] = []
        candidates = _resolve_entry_addresses(event, context)

        for chain, address in candidates:
            adapter = self._adapters.get(chain)
            if not adapter:
                continue
            trace = await self._trace_from_entry(adapter, address, event.region)
            for path in trace:
                bridge = self._path_to_bridge(event, chain, path, context)
                if bridge.confidence >= self._config.min_bridge_confidence:
                    bridges.append(bridge)

        return bridges

    async def _trace_from_entry(
        self,
        adapter: ChainAdapter,
        entry: str,
        origin_region: Optional[str],
    ) -> list[list[OnChainTransfer]]:
        paths: list[list[OnChainTransfer]] = []
        frontier: list[list[OnChainTransfer]] = [[]]
        visited: set[str] = set()

        for _ in range(self._config.max_hops):
            next_frontier: list[list[OnChainTransfer]] = []
            for path in frontier:
                current = entry if not path else path[-1].target
                norm = adapter.normalize_address(current)
                if norm in visited:
                    continue
                visited.add(norm)

                neighborhood = await adapter.get_neighborhood(current, depth=1, limit=30)
                if not neighborhood.outbound:
                    if path:
                        paths.append(path)
                    continue

                for tx in neighborhood.outbound:
                    extended = path + [tx]
                    next_frontier.append(extended)
                    # Stop early at high-flow exit (licensed-looking concentration)
                    if len(extended) >= 2:
                        paths.append(extended)

            frontier = next_frontier
            if not frontier:
                break

        return paths[:50]

    def _path_to_bridge(
        self,
        event: FiatLegEvent,
        chain: Chain,
        path: list[OnChainTransfer],
        context: InvestigationContext,
    ) -> FiatCryptoBridge:
        entry = path[0].source if path else None
        exit_addr = path[-1].target if path else None
        evidence = [f"fiat:{event.event_id}"]
        confidence = 0.25

        if event.region:
            evidence.append(f"origin_region:{event.region}")
            confidence += 0.15

        if path:
            evidence.append(f"on_chain_hops:{len(path)}")
            confidence += min(0.25, len(path) * 0.05)

        cluster_id = _match_cluster(exit_addr or entry, chain, context.clusters)
        if cluster_id:
            evidence.append(f"cluster:{cluster_id}")
            confidence += 0.2

        platform_regions = {
            le.address: le.region
            for le in context.licensed_events
            if le.region and le.direction == "deposit"
        }
        dest_region = None
        if exit_addr:
            dest_region = self._region_profiler.infer_exit_region(
                chain, exit_addr, platform_regions
            )
            if dest_region:
                evidence.append(f"exit_region:{dest_region}")
                confidence += 0.15

        return FiatCryptoBridge(
            bridge_id=str(uuid.uuid4()),
            fiat_event_id=event.event_id,
            chain=chain,
            entry_address=entry,
            exit_address=exit_addr,
            cluster_id=cluster_id,
            hop_count=len(path),
            region_origin=event.region,
            region_destination=dest_region,
            confidence=min(1.0, round(confidence, 3)),
            evidence=evidence,
        )


def _resolve_entry_addresses(
    event: FiatLegEvent, context: InvestigationContext
) -> list[tuple[Chain, str]]:
    results: list[tuple[Chain, str]] = []

    if event.platform_id:
        for le in context.licensed_events:
            if le.platform_name == event.platform_id or le.platform_license_id == event.platform_id:
                results.append((le.chain, le.address))

    for cp in context.control_purchases:
        if event.region and cp.region.upper() == event.region.upper():
            results.append((cp.chain, cp.target_address))

    return results


def _match_cluster(
    address: Optional[str], chain: Chain, clusters: list[CryptoCluster]
) -> Optional[str]:
    if not address:
        return None
    normalized = address.lower() if chain == Chain.ETH else address
    for cluster in clusters:
        if not cluster.member_addresses:
            continue
        for member in cluster.member_addresses:
            member_norm = member.lower() if chain == Chain.ETH else member
            if member_norm == normalized:
                return cluster.cluster_id
    return None
