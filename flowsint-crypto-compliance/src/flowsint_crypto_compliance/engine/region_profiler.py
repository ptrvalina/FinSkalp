from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Optional

from flowsint_types.fiat_crypto import Chain, CryptoCluster, EvidenceSource


class RegionProfiler:
    """
    Infer regional affinity of addresses/clusters from fiat-side and platform signals.

  Example: many Mumbai OTC addresses send to cluster X → cluster X gets IN weight.
    """

    def __init__(self) -> None:
        self._flows: list[tuple[str, str, float]] = []  # from_region, to_address_key, weight

    def record_flow(
        self,
        *,
        from_region: str,
        chain: Chain,
        to_address: str,
        weight: float = 1.0,
        source: EvidenceSource = EvidenceSource.BLOCKCHAIN,
    ) -> None:
        key = self._address_key(chain, to_address)
        # Licensed platform and control purchases carry higher weight
        multiplier = {
            EvidenceSource.LICENSED_PLATFORM: 1.5,
            EvidenceSource.CONTROL_PURCHASE: 2.0,
            EvidenceSource.FIU_ALERT: 1.2,
            EvidenceSource.BANK_ALERT: 1.2,
        }.get(source, 1.0)
        self._flows.append((from_region.upper(), key, weight * multiplier))

    def profile_address(self, chain: Chain, address: str) -> dict[str, float]:
        key = self._address_key(chain, address)
        counter: Counter[str] = Counter()
        for region, target, weight in self._flows:
            if target == key:
                counter[region] += weight
        return _normalize(counter)

    def apply_to_cluster(self, cluster: CryptoCluster, chain: Chain) -> CryptoCluster:
        if not cluster.member_addresses:
            return cluster

        aggregate: Counter[str] = Counter()
        for member in cluster.member_addresses:
            for region, weight in self.profile_address(chain, member).items():
                aggregate[region] += weight

        merged = dict(cluster.region_weights or {})
        for region, weight in _normalize(aggregate).items():
            merged[region] = round((merged.get(region, 0) + weight) / 2, 3)

        cluster.region_weights = merged or cluster.region_weights
        if merged:
            top_region = max(merged, key=merged.get)
            cluster.confidence = min(
                1.0, round(cluster.confidence + merged[top_region] * 0.15, 3)
            )
        return cluster

    def infer_exit_region(
        self,
        chain: Chain,
        address: str,
        known_platform_regions: dict[str, str],
    ) -> Optional[str]:
        """If address matches a licensed platform deposit, return platform region."""
        key = self._address_key(chain, address)
        for platform_addr, region in known_platform_regions.items():
            if self._address_key(chain, platform_addr) == key:
                return region
        profile = self.profile_address(chain, address)
        if not profile:
            return None
        return max(profile, key=profile.get)

    @staticmethod
    def _address_key(chain: Chain, address: str) -> str:
        normalized = address.lower() if chain == Chain.ETH else address
        return f"{chain.value}:{normalized}"


def _normalize(counter: Counter[str]) -> dict[str, float]:
    total = sum(counter.values())
    if total <= 0:
        return {}
    return {region: round(count / total, 3) for region, count in counter.items()}
