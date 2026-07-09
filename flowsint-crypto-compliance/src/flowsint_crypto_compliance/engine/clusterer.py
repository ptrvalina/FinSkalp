from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Optional

from flowsint_types.fiat_crypto import (
    Chain,
    ControlPurchaseEvent,
    CryptoCluster,
    EntityKind,
    EvidenceSource,
    LicensedPlatformEvent,
)


@dataclass
class AddressSeed:
    address: str
    chain: Chain
    region: Optional[str] = None
    source: EvidenceSource = EvidenceSource.BLOCKCHAIN
    entity_hint: Optional[str] = None
    entity_kind: EntityKind = EntityKind.UNKNOWN


@dataclass
class ClusterGraph:
    """Co-occurrence graph: addresses that share counterparties cluster together."""

    adjacency: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    seeds: dict[str, AddressSeed] = field(default_factory=dict)

    def add_seed(self, seed: AddressSeed) -> None:
        key = _addr_key(seed.chain, seed.address)
        self.seeds[key] = seed

    def link(self, chain: Chain, a: str, b: str) -> None:
        ka, kb = _addr_key(chain, a), _addr_key(chain, b)
        if ka == kb:
            return
        self.adjacency[ka].add(kb)
        self.adjacency[kb].add(ka)


def _addr_key(chain: Chain, address: str) -> str:
    normalized = address.lower() if chain == Chain.ETH else address
    return f"{chain.value}:{normalized}"


class ClusterEngine:
    """Build probabilistic clusters from licensed events, control purchases, and graph links."""

    def __init__(self) -> None:
        self._graph = ClusterGraph()

    @property
    def graph(self) -> ClusterGraph:
        return self._graph

    def ingest_licensed_events(self, events: Iterable[LicensedPlatformEvent]) -> None:
        by_platform: dict[str, list[LicensedPlatformEvent]] = defaultdict(list)
        for event in events:
            by_platform[event.platform_name].append(event)
            self._graph.add_seed(
                AddressSeed(
                    address=event.address,
                    chain=event.chain,
                    region=event.region,
                    source=EvidenceSource.LICENSED_PLATFORM,
                    entity_hint=event.platform_name,
                    entity_kind=EntityKind.CEX,
                )
            )
        for platform, group in by_platform.items():
            addresses = [e.address for e in group]
            for i, addr in enumerate(addresses):
                for other in addresses[i + 1 :]:
                    self._graph.link(group[0].chain, addr, other)

    def ingest_control_purchases(self, events: Iterable[ControlPurchaseEvent]) -> None:
        for event in events:
            self._graph.add_seed(
                AddressSeed(
                    address=event.target_address,
                    chain=event.chain,
                    region=event.region,
                    source=EvidenceSource.CONTROL_PURCHASE,
                    entity_hint=event.channel,
                    entity_kind=EntityKind.OTC,
                )
            )
            if event.source_address:
                self._graph.link(event.chain, event.source_address, event.target_address)

    def ingest_counterparty_links(
        self,
        chain: Chain,
        center: str,
        counterparties: Iterable[str],
        *,
        region: Optional[str] = None,
    ) -> None:
        self._graph.add_seed(
            AddressSeed(
                address=center,
                chain=chain,
                region=region,
                source=EvidenceSource.BLOCKCHAIN,
            )
        )
        for cp in counterparties:
            self._graph.link(chain, center, cp)

    def build_clusters(self, min_confidence: float = 0.3) -> list[CryptoCluster]:
        visited: set[str] = set()
        clusters: list[CryptoCluster] = []

        for node in self._graph.adjacency:
            if node in visited:
                continue
            component = _connected_component(self._graph.adjacency, node)
            visited.update(component)
            if len(component) == 1 and node not in self._graph.seeds:
                continue

            cluster = self._component_to_cluster(component, min_confidence)
            if cluster.confidence >= min_confidence:
                clusters.append(cluster)

        return clusters

    def _component_to_cluster(
        self, component: set[str], min_confidence: float
    ) -> CryptoCluster:
        seeds = [self._graph.seeds[k] for k in component if k in self._graph.seeds]
        region_counter: Counter[str] = Counter()
        entity_hints: Counter[str] = Counter()
        kinds: Counter[EntityKind] = Counter()
        sources: set[EvidenceSource] = set()

        for seed in seeds:
            if seed.region:
                region_counter[seed.region] += 1
            if seed.entity_hint:
                entity_hints[seed.entity_hint] += 1
            kinds[seed.entity_kind] += 1
            sources.add(seed.source)

        total_region = sum(region_counter.values()) or 1
        region_weights = {
            region: count / total_region for region, count in region_counter.items()
        }

        claimed = entity_hints.most_common(1)[0][0] if entity_hints else None
        entity_kind = kinds.most_common(1)[0][0] if kinds else EntityKind.UNKNOWN

        # Confidence: more independent evidence sources and region agreement
        source_factor = min(1.0, len(sources) * 0.25)
        size_factor = min(1.0, len(component) / 10)
        region_factor = (
            max(region_weights.values()) if region_weights else 0.2
        )
        confidence = round(0.35 * source_factor + 0.35 * region_factor + 0.3 * size_factor, 3)

        members = [_parse_addr_key(k)[1] for k in sorted(component)[:20]]
        chain = _parse_addr_key(next(iter(component)))[0]
        cluster_id = f"{chain.value}_cluster_{hash(tuple(sorted(component))) & 0xFFFFFF:06x}"

        return CryptoCluster(
            cluster_id=cluster_id,
            label=f"{entity_kind.value}_cluster",
            entity_kind=entity_kind,
            claimed_entity=claimed,
            disputed=False,
            region_weights=region_weights or None,
            confidence=confidence,
            member_addresses=members,
            evidence_sources=sorted(sources, key=lambda s: s.value),
        )


def _connected_component(adj: dict[str, set[str]], start: str) -> set[str]:
    stack = [start]
    seen: set[str] = set()
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adj.get(node, set()) - seen)
    return seen


def _parse_addr_key(key: str) -> tuple[Chain, str]:
    chain_str, address = key.split(":", 1)
    return Chain(chain_str), address
