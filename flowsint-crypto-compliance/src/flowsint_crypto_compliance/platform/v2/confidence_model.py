"""Confidence scoring model — RFC-0003 Ch.8."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import ConfidenceBreakdown


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def source_quality_score(source_type: str, *, trust_level: float | None = None) -> float:
    """Heuristic source quality from type and optional trust."""
    base: dict[str, float] = {
        "sanctions": 0.95,
        "registry": 0.9,
        "blockchain_explorer": 0.88,
        "court_decision": 0.92,
        "bank_statement": 0.85,
        "osint": 0.55,
        "darknet_index": 0.45,
        "forum": 0.4,
        "social_media": 0.42,
        "news": 0.5,
        "leak": 0.35,
        "unknown": 0.4,
    }
    key = (source_type or "unknown").strip().lower()
    score = base.get(key, 0.5)
    if trust_level is not None:
        score = (score + _clamp(trust_level)) / 2.0
    return _clamp(score)


def freshness_score(
    discovered_at: datetime | None,
    *,
    half_life_days: float = 180.0,
    now: datetime | None = None,
) -> float:
    """Exponential decay — fresher evidence scores higher."""
    if discovered_at is None:
        return 0.5
    ref = now or datetime.now(timezone.utc)
    if discovered_at.tzinfo is None:
        discovered_at = discovered_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (ref - discovered_at).total_seconds() / 86400.0)
    if half_life_days <= 0:
        return 1.0
    import math

    return _clamp(math.exp(-0.693 * age_days / half_life_days))


def consistency_score(signals: list[dict[str, Any]]) -> float:
    """Agreement across independent signals (0..1)."""
    if not signals:
        return 0.0
    if len(signals) == 1:
        return 0.55
    values = [str(s.get("value") or s.get("normalized_value") or "") for s in signals]
    unique = set(v for v in values if v)
    if not unique:
        return 0.4
    agreement = 1.0 - (len(unique) - 1) / max(len(values), 1)
    return _clamp(0.4 + 0.6 * agreement)


def independent_source_count(sources: list[str]) -> int:
    """Count distinct source families (dependency groups collapsed)."""
    families: set[str] = set()
    for s in sources:
        key = (s or "unknown").split(":")[0].strip().lower()
        families.add(key or "unknown")
    return len(families)


def calculate_confidence(
    *,
    sources: list[str],
    signals: list[dict[str, Any]] | None = None,
    trust_levels: list[float] | None = None,
    discovered_at: datetime | None = None,
    base_confidence: float = 0.5,
) -> ConfidenceBreakdown:
    """
    Composite confidence from independent sources, quality, freshness, consistency.
    """
    signals = signals or []
    n_indep = max(1, independent_source_count(sources))
    indep_factor = _clamp(0.35 + 0.15 * min(n_indep, 4))

    qualities = []
    for i, src in enumerate(sources):
        tl = trust_levels[i] if trust_levels and i < len(trust_levels) else None
        qualities.append(source_quality_score(src, trust_level=tl))
    quality = sum(qualities) / len(qualities) if qualities else source_quality_score("unknown")

    fresh = freshness_score(discovered_at)
    consist = consistency_score(signals) if signals else 0.55

    composite = _clamp(
        0.25 * indep_factor
        + 0.30 * quality
        + 0.20 * fresh
        + 0.15 * consist
        + 0.10 * _clamp(base_confidence)
    )

    explain: dict[str, Any] = {
        "independent_sources": n_indep,
        "independent_factor": round(indep_factor, 3),
        "source_quality": round(quality, 3),
        "freshness": round(fresh, 3),
        "consistency": round(consist, 3),
        "base": round(_clamp(base_confidence), 3),
        "formula": "0.25*indep + 0.30*quality + 0.20*fresh + 0.15*consistency + 0.10*base",
    }

    return ConfidenceBreakdown(
        composite=composite,
        independent_sources=n_indep,
        source_quality=quality,
        freshness=fresh,
        consistency=consist,
        explain=explain,
    )
