"""RFC-0016 Ch.4 — factor calculators per group."""

from __future__ import annotations

from typing import Any, Callable

from flowsint_crypto_compliance.platform.v2.rde.types import FactorGroup


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def calculate_blockchain_factors(signals: dict[str, Any]) -> dict[str, Any]:
    """Score blockchain intelligence signals."""
    tx_count = int(signals.get("transaction_count") or signals.get("tx_count") or 0)
    risk_flags = signals.get("risk_flags") or signals.get("flags") or []
    mixer = bool(signals.get("mixer_exposure") or signals.get("has_mixer"))
    high_risk_counterparty = bool(signals.get("high_risk_counterparty"))
    volume_usd = float(signals.get("volume_usd") or 0)

    activity = _clamp(tx_count * 3.0 + (20.0 if volume_usd > 100_000 else 0))
    exposure = _clamp(len(risk_flags) * 15.0 + (25.0 if mixer else 0) + (20.0 if high_risk_counterparty else 0))
    score = _clamp(activity * 0.4 + exposure * 0.6)

    return {
        "group": FactorGroup.BLOCKCHAIN.value,
        "score": score,
        "components": {"activity": activity, "exposure": exposure},
        "signals_used": list(signals.keys()),
    }


def calculate_registry_factors(signals: dict[str, Any]) -> dict[str, Any]:
    """Score registry/CRIF compliance signals."""
    sanctioned = bool(signals.get("sanctioned"))
    license_status = str(signals.get("license_status") or "unknown").lower()
    org_status = str(signals.get("org_status") or "active").lower()
    check_failures = int(signals.get("check_failures") or signals.get("failed_checks") or 0)

    compliance = 0.0
    if sanctioned:
        compliance = 95.0
    elif license_status in ("revoked", "suspended"):
        compliance = 75.0
    elif org_status in ("dissolved", "liquidated"):
        compliance = 70.0
    else:
        compliance = _clamp(check_failures * 12.0)

    score = _clamp(compliance)
    return {
        "group": FactorGroup.REGISTRY.value,
        "score": score,
        "components": {"compliance_risk": compliance},
        "signals_used": list(signals.keys()),
    }


def calculate_osint_factors(signals: dict[str, Any]) -> dict[str, Any]:
    """Score OSINT/ICF mention signals."""
    mentions = signals.get("mentions") or signals.get("items") or []
    negative = int(signals.get("negative_mentions") or 0)
    sentiment = float(signals.get("avg_sentiment") or 0.5)
    source_count = int(signals.get("source_count") or len(mentions))

    volume = _clamp(len(mentions) * 8.0 + source_count * 5.0)
    negativity = _clamp(negative * 15.0 + (1.0 - sentiment) * 40.0)
    score = _clamp(volume * 0.35 + negativity * 0.65)

    return {
        "group": FactorGroup.OSINT.value,
        "score": score,
        "components": {"mention_volume": volume, "negative_signal": negativity},
        "signals_used": list(signals.keys()),
    }


def calculate_graph_factors(signals: dict[str, Any]) -> dict[str, Any]:
    """Score knowledge graph neighbor signals."""
    neighbors = signals.get("neighbors") or signals.get("relations") or []
    high_risk_links = int(signals.get("high_risk_links") or 0)
    depth = int(signals.get("depth") or 1)

    connectivity = _clamp(len(neighbors) * 6.0 + depth * 10.0)
    risk_links = _clamp(high_risk_links * 20.0)
    score = _clamp(connectivity * 0.45 + risk_links * 0.55)

    return {
        "group": FactorGroup.GRAPH.value,
        "score": score,
        "components": {"connectivity": connectivity, "risk_links": risk_links},
        "signals_used": list(signals.keys()),
    }


def calculate_evidence_factors(signals: dict[str, Any]) -> dict[str, Any]:
    """Score evidence center signals."""
    items = signals.get("items") or signals.get("evidence") or []
    verified = int(signals.get("verified_count") or 0)
    disputed = int(signals.get("disputed_count") or 0)
    avg_confidence = float(signals.get("avg_confidence") or 0.5)

    strength = _clamp(len(items) * 10.0 + verified * 8.0 + avg_confidence * 30.0)
    dispute_penalty = _clamp(disputed * 12.0)
    score = _clamp(strength - dispute_penalty * 0.3)

    return {
        "group": FactorGroup.EVIDENCE.value,
        "score": score,
        "components": {"strength": strength, "dispute_penalty": dispute_penalty},
        "signals_used": list(signals.keys()),
    }


_CALCULATORS: dict[FactorGroup, Callable[[dict[str, Any]], dict[str, Any]]] = {
    FactorGroup.BLOCKCHAIN: calculate_blockchain_factors,
    FactorGroup.REGISTRY: calculate_registry_factors,
    FactorGroup.OSINT: calculate_osint_factors,
    FactorGroup.GRAPH: calculate_graph_factors,
    FactorGroup.EVIDENCE: calculate_evidence_factors,
}


def calculate_all_factors(signals_by_group: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Calculate factors for all present signal groups."""
    results: dict[str, dict[str, Any]] = {}
    for group in FactorGroup:
        raw = signals_by_group.get(group.value) or {}
        if raw:
            results[group.value] = _CALCULATORS[group](raw)
        else:
            results[group.value] = {"group": group.value, "score": 0.0, "components": {}, "signals_used": []}
    return results


def register_calculator(group: FactorGroup, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    """SDK extension point — register custom factor calculator."""
    _CALCULATORS[group] = fn
