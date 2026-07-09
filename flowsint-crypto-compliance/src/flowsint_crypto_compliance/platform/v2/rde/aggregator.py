"""RFC-0016 Ch.3 — aggregate factors into score components."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.rde.types import FactorGroup

_DEFAULT_WEIGHTS: dict[str, float] = {
    FactorGroup.BLOCKCHAIN.value: 0.25,
    FactorGroup.REGISTRY.value: 0.25,
    FactorGroup.OSINT.value: 0.15,
    FactorGroup.GRAPH.value: 0.20,
    FactorGroup.EVIDENCE.value: 0.15,
}


def aggregate_factors(
    factor_results: dict[str, dict[str, Any]],
    *,
    correlations: list[dict[str, Any]] | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Aggregate per-group factor scores into composite components."""
    w = weights or _DEFAULT_WEIGHTS
    factor_scores: dict[str, float] = {}
    weighted_sum = 0.0
    weight_total = 0.0

    for group, result in factor_results.items():
        score = float(result.get("score") or 0)
        factor_scores[group] = score
        weight = w.get(group, 0.1)
        weighted_sum += score * weight
        weight_total += weight

    composite = weighted_sum / weight_total if weight_total else 0.0

    # Correlation boost — cross-domain confirmation increases score modestly
    corr_boost = 0.0
    if correlations:
        avg_conf = sum(c.get("confidence", 0) for c in correlations) / len(correlations)
        corr_boost = min(15.0, avg_conf * 20.0)
        composite = min(100.0, composite + corr_boost)

    return {
        "composite_score": round(composite, 2),
        "factor_scores": {k: round(v, 2) for k, v in factor_scores.items()},
        "weights": w,
        "correlation_boost": round(corr_boost, 2),
        "active_groups": [g for g, s in factor_scores.items() if s > 0],
    }
