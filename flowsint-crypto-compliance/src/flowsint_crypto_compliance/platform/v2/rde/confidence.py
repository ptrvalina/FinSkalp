"""RFC-0016 Ch.6 — confidence scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfidenceScore:
    """Multi-dimensional confidence assessment."""

    independent_sources: float = 0.0
    quality: float = 0.0
    completeness: float = 0.0
    consistency: float = 0.0
    freshness: float = 0.0
    composite: float = 0.0
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "independent_sources": round(self.independent_sources, 3),
            "quality": round(self.quality, 3),
            "completeness": round(self.completeness, 3),
            "consistency": round(self.consistency, 3),
            "freshness": round(self.freshness, 3),
            "composite": round(self.composite, 3),
            "composite_pct": round(self.composite * 100, 1),
            "explain": self.explain,
        }


def calculate_confidence(
    signals: dict[str, dict[str, Any]],
    *,
    correlations: list[dict[str, Any]] | None = None,
    factor_results: dict[str, dict[str, Any]] | None = None,
) -> ConfidenceScore:
    """Calculate confidence from signal coverage, quality, and cross-domain consistency."""
    active_groups = [g for g, s in signals.items() if s]
    independent_sources = min(1.0, len(active_groups) / 5.0)

    quality_vals: list[float] = []
    for group, data in signals.items():
        if not data:
            continue
        if group == "evidence":
            quality_vals.append(float(data.get("avg_confidence") or 0.5))
        elif group == "osint":
            quality_vals.append(float(data.get("avg_sentiment") or 0.5))
        elif group == "graph":
            neighbors = data.get("neighbors") or []
            if neighbors:
                confs = [float(n.get("confidence") or 0.5) for n in neighbors]
                quality_vals.append(sum(confs) / len(confs))
        else:
            quality_vals.append(0.6)
    quality = sum(quality_vals) / len(quality_vals) if quality_vals else 0.3

    completeness = min(1.0, len(active_groups) / 3.0)
    if factor_results:
        non_zero = sum(1 for r in factor_results.values() if (r.get("score") or 0) > 0)
        completeness = max(completeness, min(1.0, non_zero / 5.0))

    consistency = 0.5
    if correlations:
        consistency = min(1.0, 0.4 + sum(c.get("confidence", 0) for c in correlations) / len(correlations) * 0.5)
    elif len(active_groups) >= 2:
        scores = [float((factor_results or {}).get(g, {}).get("score") or 0) for g in active_groups]
        if scores:
            spread = max(scores) - min(scores)
            consistency = max(0.3, 1.0 - spread / 100.0)

    freshness = 0.7
    for data in signals.values():
        if data.get("freshness") is not None:
            freshness = max(freshness, float(data["freshness"]))
        if data.get("last_updated"):
            freshness = max(freshness, 0.8)

    composite = (
        independent_sources * 0.25
        + quality * 0.25
        + completeness * 0.20
        + consistency * 0.20
        + freshness * 0.10
    )

    return ConfidenceScore(
        independent_sources=independent_sources,
        quality=quality,
        completeness=completeness,
        consistency=consistency,
        freshness=freshness,
        composite=composite,
        explain={
            "active_groups": active_groups,
            "correlation_count": len(correlations or []),
            "method": "multi_dimensional_weighted",
        },
    )
