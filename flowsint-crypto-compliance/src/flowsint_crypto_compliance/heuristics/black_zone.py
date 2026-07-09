from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from flowsint_crypto_compliance.chains.base import AddressNeighborhood, OnChainTransfer


@dataclass
class HubScore:
    address: str
    score: float  # 0..1
    fan_in: int
    fan_out: int
    unique_counterparties: int
    signals: list[str] = field(default_factory=list)


@dataclass
class BlackZoneAssessment:
    address: str
    risk_score: float  # 0..1
    signals: list[str]
    likely_role: str  # hub | mixer_like | layering | unknown


class HubDetector:
    """
    Detect payment hubs without KYT labels.

    In CIS, gray/black infrastructure often appears as addresses with
    abnormal fan-in/fan-out — OTC desks, P2P aggregators, transit wallets.
    """

    def __init__(
        self,
        *,
        min_counterparties: int = 8,
        hub_score_threshold: float = 0.65,
    ):
        self._min_counterparties = min_counterparties
        self._hub_threshold = hub_score_threshold

    def score(self, neighborhood: AddressNeighborhood) -> HubScore:
        fan_in = len(neighborhood.inbound)
        fan_out = len(neighborhood.outbound)
        counterparties = _unique_counterparties(neighborhood)
        unique_count = len(counterparties)

        signals: list[str] = []
        if unique_count >= self._min_counterparties:
            signals.append("high_fan_in_fan_out")

        amounts = [
            tx.amount for tx in neighborhood.inbound + neighborhood.outbound if tx.amount
        ]
        if amounts and _round_amount_ratio(amounts) >= 0.5:
            signals.append("round_amount_bursts")

        # Score: balance between volume of connections and symmetry (hub-like)
        cp_factor = min(1.0, unique_count / 20)
        symmetry = 1.0 - abs(fan_in - fan_out) / max(fan_in + fan_out, 1)
        score = round(0.6 * cp_factor + 0.4 * symmetry, 3)

        return HubScore(
            address=neighborhood.address,
            score=score,
            fan_in=fan_in,
            fan_out=fan_out,
            unique_counterparties=unique_count,
            signals=signals,
        )

    def is_hub(self, neighborhood: AddressNeighborhood) -> bool:
        return self.score(neighborhood).score >= self._hub_threshold


class BlackZoneAnalyzer:
    """
    Structural black-zone analysis on sovereign RF/CIS signals only.

    Detects mixer-like and layering behavior from graph topology only.
    """

    def __init__(self, hub_detector: HubDetector | None = None):
        self._hub = hub_detector or HubDetector()

    def assess(
        self,
        neighborhood: AddressNeighborhood,
        *,
        extended_outbound: list[OnChainTransfer] | None = None,
    ) -> BlackZoneAssessment:
        hub = self._hub.score(neighborhood)
        signals = list(hub.signals)
        risk = hub.score * 0.5

        outbound = neighborhood.outbound
        if extended_outbound:
            outbound = outbound + extended_outbound

        if _looks_like_peel_chain(outbound):
            signals.append("peel_chain")
            risk += 0.2

        if _rapid_layering(neighborhood.inbound, outbound):
            signals.append("rapid_layering")
            risk += 0.15

        if _trc20_split_merge(neighborhood):
            signals.append("trc20_split_merge")
            risk += 0.15

        risk = min(1.0, round(risk, 3))
        role = _infer_role(signals, hub.score)

        return BlackZoneAssessment(
            address=neighborhood.address,
            risk_score=risk,
            signals=signals,
            likely_role=role,
        )


def _unique_counterparties(n: AddressNeighborhood) -> set[str]:
    peers: set[str] = set()
    for tx in n.inbound:
        peers.add(tx.source)
    for tx in n.outbound:
        peers.add(tx.target)
    peers.discard(n.address)
    return peers


def _round_amount_ratio(amounts: list[float]) -> float:
    if not amounts:
        return 0.0
    roundish = sum(1 for a in amounts if a == round(a) or a in (100, 500, 1000, 5000, 10000))
    return roundish / len(amounts)


def _looks_like_peel_chain(outbound: list[OnChainTransfer]) -> bool:
    """Single dominant outbound per step suggests peel chain."""
    if len(outbound) < 3:
        return False
    # Each tx sends most funds to one new target
    single_target_steps = sum(
        1 for tx in outbound if tx.amount and tx.amount > 0
    )
    return single_target_steps >= 3


def _rapid_layering(
    inbound: list[OnChainTransfer], outbound: list[OnChainTransfer]
) -> bool:
    if not inbound or not outbound:
        return False
    return len(inbound) + len(outbound) >= 6


def _trc20_split_merge(n: AddressNeighborhood) -> bool:
    usdt_in = [tx for tx in n.inbound if (tx.asset or "").upper() == "USDT"]
    usdt_out = [tx for tx in n.outbound if (tx.asset or "").upper() == "USDT"]
    return len(usdt_in) >= 2 and len(usdt_out) >= 2


def _infer_role(signals: list[str], hub_score: float) -> str:
    if "peel_chain" in signals or "rapid_layering" in signals:
        return "layering"
    if hub_score >= 0.65 or "high_fan_in_fan_out" in signals:
        return "hub"
    if len(signals) >= 2:
        return "mixer_like"
    return "unknown"
