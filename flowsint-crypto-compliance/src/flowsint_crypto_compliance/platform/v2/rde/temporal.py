"""RFC-0016 Ch.11 — temporal analysis (in-memory)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AssessmentSnapshot:
    entity_key: str
    case_ref: str | None
    composite_score: float
    risk_level: str
    factor_scores: dict[str, float]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_key": self.entity_key,
            "case_ref": self.case_ref,
            "composite_score": self.composite_score,
            "risk_level": self.risk_level,
            "factor_scores": self.factor_scores,
            "timestamp": self.timestamp,
        }


class TemporalStore:
    """In-memory snapshots, period compare, trends, spike detection."""

    def __init__(self) -> None:
        self._snapshots: dict[str, list[AssessmentSnapshot]] = {}

    def save_snapshot(self, snapshot: AssessmentSnapshot) -> None:
        key = snapshot.entity_key
        self._snapshots.setdefault(key, []).append(snapshot)

    def get_snapshots(self, entity_key: str) -> list[AssessmentSnapshot]:
        return list(self._snapshots.get(entity_key, []))

    def compare_periods(self, entity_key: str) -> dict[str, Any]:
        snaps = self.get_snapshots(entity_key)
        if len(snaps) < 2:
            return {"entity_key": entity_key, "comparison": None, "reason_ru": "Недостаточно снимков"}
        prev, curr = snaps[-2], snaps[-1]
        delta = curr.composite_score - prev.composite_score
        return {
            "entity_key": entity_key,
            "previous": prev.to_dict(),
            "current": curr.to_dict(),
            "delta_score": round(delta, 2),
            "trend": "rising" if delta > 5 else ("falling" if delta < -5 else "stable"),
            "risk_level_changed": prev.risk_level != curr.risk_level,
        }

    def detect_spike(self, entity_key: str, *, threshold: float = 15.0) -> dict[str, Any]:
        snaps = self.get_snapshots(entity_key)
        if len(snaps) < 2:
            return {"spike_detected": False, "entity_key": entity_key}
        prev, curr = snaps[-2], snaps[-1]
        delta = curr.composite_score - prev.composite_score
        return {
            "spike_detected": delta >= threshold,
            "entity_key": entity_key,
            "delta_score": round(delta, 2),
            "threshold": threshold,
            "activity_spike": delta >= threshold,
        }

    def get_trends(self, entity_key: str) -> dict[str, Any]:
        snaps = self.get_snapshots(entity_key)
        if not snaps:
            return {"entity_key": entity_key, "trend": "unknown", "data_points": 0}
        scores = [s.composite_score for s in snaps]
        if len(scores) >= 2:
            avg_delta = (scores[-1] - scores[0]) / (len(scores) - 1)
        else:
            avg_delta = 0.0
        return {
            "entity_key": entity_key,
            "data_points": len(scores),
            "scores": scores,
            "avg_delta": round(avg_delta, 2),
            "trend": "rising" if avg_delta > 3 else ("falling" if avg_delta < -3 else "stable"),
        }


_store: TemporalStore | None = None


def get_temporal_store() -> TemporalStore:
    global _store
    if _store is None:
        _store = TemporalStore()
    return _store
