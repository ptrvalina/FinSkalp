"""Source-of-funds buckets and indirect entity exposure (KYT-style)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from flowsint_crypto_compliance.chains.base import OnChainTransfer
from flowsint_types.fiat_crypto import Chain, SovereignRiskLabel

_SEVERE_CATS = frozenset(
    {"sanctions", "sanction", "mixer", "tornado", "scam", "ransomware", "terror", "risky_exchange", "illicit"}
)
_HIGH_CATS = frozenset({"gambling", "darknet", "fraud", "illegal_service", "casino", "betting"})
_LOW_CATS = frozenset({"exchange", "payment", "wallet", "other", "licensed_exchange"})


@dataclass
class ExposureResult:
    source_of_funds: dict[str, float] = field(default_factory=dict)
    tag_breakdown: dict[str, float] = field(default_factory=dict)
    connections: list[dict[str, Any]] = field(default_factory=list)
    indirect_exposure: list[dict[str, Any]] = field(default_factory=list)
    connection_risk_summary: dict[str, dict[str, Any]] = field(default_factory=dict)
    total_inbound: float = 0.0
    total_outbound: float = 0.0
    connection_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_of_funds": self.source_of_funds,
            "tag_breakdown": self.tag_breakdown,
            "connections": self.connections,
            "indirect_exposure": self.indirect_exposure,
            "connection_risk_summary": self.connection_risk_summary,
            "total_inbound": self.total_inbound,
            "total_outbound": self.total_outbound,
            "connection_count": self.connection_count,
        }


def compute_exposure(
    *,
    focus_address: str,
    chain: Chain,
    inbound: list[OnChainTransfer],
    outbound: list[OnChainTransfer],
    label_lookup: Callable[[str], SovereignRiskLabel | None],
    imported_exposure: list[dict[str, Any]] | None = None,
) -> ExposureResult:
    """Build KYT-style exposure from transfers + label cache (+ optional import rows)."""
    if imported_exposure:
        return _from_imported_exposure(imported_exposure, inbound, outbound)

    tier_amounts = {"severe": 0.0, "high": 0.0, "moderate": 0.0, "low": 0.0, "unknown": 0.0}
    tag_amounts: dict[str, float] = {}
    connections: dict[str, dict[str, Any]] = {}

    total_in = sum(tx.amount or 0.0 for tx in inbound)
    total_out = sum(tx.amount or 0.0 for tx in outbound)

    for tx in inbound:
        cp = tx.source
        if not cp or cp == focus_address:
            continue
        amount = tx.amount or 0.0
        label = label_lookup(cp)
        tier, tag = _label_tier_and_tag(label)
        tier_amounts[tier] += amount
        tag_amounts[tag] = tag_amounts.get(tag, 0.0) + amount
        key = label.entity_name if label and label.entity_name else cp
        if key not in connections:
            connections[key] = {
                "entity_name": label.entity_name if label else cp[:8] + "…",
                "address": cp,
                "category": tag,
                "total_received": 0.0,
                "hops": 1,
                "behavior": "direct",
                "risk_pct": label.risk_score if label and label.risk_score else _tier_default_risk(tier),
                "risk_tier": tier,
            }
        connections[key]["total_received"] += amount

    denom = total_in or sum(tier_amounts.values()) or 1.0
    sof = {k: round(100 * v / denom, 2) for k, v in tier_amounts.items()}
    tags = {k: round(100 * v / denom, 2) for k, v in tag_amounts.items() if v > 0}

    conn_list = sorted(connections.values(), key=lambda c: c["total_received"], reverse=True)
    indirect = [
        {
            **c,
            "risk_tier": c["risk_tier"].upper() if isinstance(c["risk_tier"], str) else "LOW",
        }
        for c in conn_list
    ]
    risk_summary = _connection_risk_summary(conn_list)

    return ExposureResult(
        source_of_funds=sof,
        tag_breakdown=tags,
        connections=conn_list[:20],
        indirect_exposure=indirect[:15],
        connection_risk_summary=risk_summary,
        total_inbound=round(total_in, 6),
        total_outbound=round(total_out, 6),
        connection_count=len(connections),
    )


def _from_imported_exposure(
    rows: list[dict[str, Any]],
    inbound: list[OnChainTransfer],
    outbound: list[OnChainTransfer],
) -> ExposureResult:
    tier_amounts = {"severe": 0.0, "high": 0.0, "moderate": 0.0, "low": 0.0, "unknown": 0.0}
    tag_amounts: dict[str, float] = {}
    connections: list[dict[str, Any]] = []

    for row in rows:
        tier = str(row.get("risk_tier") or "low").lower()
        if tier not in tier_amounts:
            tier = "unknown"
        amount = float(row.get("amount") or 0.0)
        tier_amounts[tier] += amount
        tag = str(row.get("category") or "unknown")
        tag_amounts[tag] = tag_amounts.get(tag, 0.0) + amount
        connections.append(
            {
                "entity_name": row.get("entity_name"),
                "address": row.get("address"),
                "category": tag,
                "total_received": amount,
                "hops": row.get("hops"),
                "behavior": row.get("behavior", "indirect"),
                "risk_pct": row.get("risk_pct", 0),
                "risk_tier": tier,
            }
        )

    total_in = sum(tx.amount or 0.0 for tx in inbound) or sum(tier_amounts.values())
    total_out = sum(tx.amount or 0.0 for tx in outbound)
    denom = total_in or sum(tier_amounts.values()) or 1.0
    sof = {k: round(100 * v / denom, 2) for k, v in tier_amounts.items()}
    tags = {k: round(100 * v / denom, 2) for k, v in tag_amounts.items()}

    indirect = sorted(connections, key=lambda c: c.get("total_received") or 0, reverse=True)
    return ExposureResult(
        source_of_funds=sof,
        tag_breakdown=tags,
        connections=indirect[:20],
        indirect_exposure=indirect[:15],
        connection_risk_summary=_connection_risk_summary(indirect),
        total_inbound=round(total_in, 6),
        total_outbound=round(total_out, 6),
        connection_count=len(connections),
    )


def _label_tier_and_tag(label: SovereignRiskLabel | None) -> tuple[str, str]:
    if not label:
        return "unknown", "unknown"
    if label.sanctioned:
        return "severe", "sanctions"
    cat = (label.category or "").lower()
    entity = (label.entity_name or "").lower()
    text = f"{cat} {entity}"
    if any(k in text for k in _SEVERE_CATS):
        return "severe", cat or "risky_exchange"
    if any(k in text for k in _HIGH_CATS):
        return "high", cat or "gambling"
    if any(k in text for k in _LOW_CATS):
        return "low", cat or "exchange"
    if label.risk_score is not None:
        if label.risk_score >= 80:
            return "severe", cat or "high_risk"
        if label.risk_score >= 55:
            return "high", cat or "medium_risk"
        if label.risk_score >= 30:
            return "moderate", cat or "moderate_risk"
        return "low", cat or "low_risk"
    return "unknown", cat or "unknown"


def _tier_default_risk(tier: str) -> float:
    return {"severe": 75.0, "high": 50.0, "moderate": 25.0, "low": 10.0, "unknown": 0.0}.get(tier, 0.0)


def _connection_risk_summary(connections: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets = {
        "severe": {"count": 0, "pct": 0},
        "high": {"count": 0, "pct": 0},
        "moderate": {"count": 0, "pct": 0},
        "low": {"count": 0, "pct": 0},
    }
    total = max(1, len(connections))
    for c in connections:
        tier = str(c.get("risk_tier", "low")).lower()
        if tier not in buckets:
            tier = "low"
        buckets[tier]["count"] += 1
    for tier, data in buckets.items():
        data["pct"] = round(100 * data["count"] / total, 0)
    return buckets
