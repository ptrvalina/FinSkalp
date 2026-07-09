from __future__ import annotations

from dataclasses import dataclass, field

from flowsint_types.fiat_crypto import (
    Chain,
    ControlPurchaseEvent,
    CryptoCluster,
    EntityKind,
    EvidenceSource,
    FiatLegEvent,
    LicensedPlatformEvent,
)

from ..cis.coverage import (
    CIS_ONRAMP_CHANNELS,
    DomesticEvidenceSource,
    REGION_ANCHOR_THRESHOLD,
)
from ..heuristics.black_zone import BlackZoneAssessment
from .corridor_analyzer import CorridorAnalyzer, CorridorMatch


@dataclass
class SovereignAttribution:
    """
    Attribution result built without international KYT.

    All claims are probabilistic with explicit domestic evidence chain.
    """

    address: str
    chain: Chain
    primary_region: str | None
    region_weights: dict[str, float]
    entity_kind: EntityKind
    entity_label: str | None  # e.g. "OTC_hub_RU" (sovereign label, not a foreign exchange name)
    confidence: float
    gray_zone: bool
    black_zone: bool
    black_signals: list[str] = field(default_factory=list)
    corridor: CorridorMatch | None = None
    evidence: list[str] = field(default_factory=list)


class SovereignAttributor:
    """
    Fuse domestic feeds + blockchain heuristics for RU/CIS coverage.

    Sovereign attribution built only on RF/CIS sources:
      1. Regulatory anchors (FIU, banks, licensed VASP)
      2. Control purchases
      3. Regional co-occurrence profiling
      4. Corridor templates
      5. Structural black-zone signals
    """

    def __init__(self) -> None:
        self._corridor = CorridorAnalyzer()

    def attribute_address(
        self,
        *,
        address: str,
        chain: Chain,
        region_weights: dict[str, float],
        cluster: CryptoCluster | None = None,
        black_assessment: BlackZoneAssessment | None = None,
        corridor_regions: list[str] | None = None,
    ) -> SovereignAttribution:
        weights = {k.upper(): v for k, v in region_weights.items()}
        primary = max(weights, key=weights.get) if weights else None
        confidence = cluster.confidence if cluster else 0.2

        if primary and weights.get(primary, 0) >= REGION_ANCHOR_THRESHOLD:
            confidence = min(1.0, confidence + 0.2)

        entity_kind = cluster.entity_kind if cluster else EntityKind.UNKNOWN
        entity_label = cluster.label if cluster else None

        black_zone = False
        black_signals: list[str] = []
        if black_assessment:
            black_signals = black_assessment.signals
            black_zone = black_assessment.risk_score >= 0.55
            if black_zone:
                entity_kind = EntityKind.OTC if entity_kind == EntityKind.UNKNOWN else entity_kind
                entity_label = entity_label or f"black_zone_{black_assessment.likely_role}"

        corridor = None
        if corridor_regions:
            corridor = self._corridor.best_corridor(corridor_regions)
            if corridor:
                confidence = min(1.0, confidence + corridor.confidence * 0.15)

        gray_zone = not black_zone and confidence < 0.6

        evidence = _build_evidence(
            weights=weights,
            cluster=cluster,
            black_signals=black_signals,
            corridor=corridor,
        )

        return SovereignAttribution(
            address=address,
            chain=chain,
            primary_region=primary,
            region_weights=weights,
            entity_kind=entity_kind,
            entity_label=entity_label,
            confidence=round(confidence, 3),
            gray_zone=gray_zone,
            black_zone=black_zone,
            black_signals=black_signals,
            corridor=corridor,
            evidence=evidence,
        )

    def ingest_domestic_context(
        self,
        *,
        fiat_events: list[FiatLegEvent],
        licensed_events: list[LicensedPlatformEvent],
        control_purchases: list[ControlPurchaseEvent],
    ) -> dict[str, float]:
        """Aggregate region weights from all domestic anchors."""
        from collections import Counter

        counter: Counter[str] = Counter()

        for e in fiat_events:
            if e.region:
                counter[e.region.upper()] += 1.2

        for e in licensed_events:
            if e.region:
                w = 1.5 if e.direction == "deposit" else 1.0
                counter[e.region.upper()] += w

        for e in control_purchases:
            counter[e.region.upper()] += 2.0
            if e.channel in CIS_ONRAMP_CHANNELS:
                counter[e.region.upper()] += 0.5

        total = sum(counter.values()) or 1
        return {r: round(c / total, 3) for r, c in counter.items()}


def _build_evidence(
    *,
    weights: dict[str, float],
    cluster: CryptoCluster | None,
    black_signals: list[str],
    corridor: CorridorMatch | None,
) -> list[str]:
    evidence: list[str] = []

    for region, w in sorted(weights.items(), key=lambda x: -x[1]):
        evidence.append(f"{DomesticEvidenceSource.BLOCKCHAIN_PUBLIC.value}:region_{region}={w}")

    if cluster and cluster.evidence_sources:
        for src in cluster.evidence_sources:
            if src != EvidenceSource.OSINT:
                evidence.append(f"domestic:{src.value}")

    for sig in black_signals:
        evidence.append(f"{DomesticEvidenceSource.BEHAVIORAL_HEURISTIC.value}:{sig}")

    if corridor:
        evidence.extend(corridor.evidence)

    return evidence
