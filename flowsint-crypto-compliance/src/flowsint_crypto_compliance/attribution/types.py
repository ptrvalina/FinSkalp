from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EntityLabel:
    address: str
    chain: str
    label: str
    category: str
    confidence: float
    source: str
    tier: int = 2
    risk_score: float = 0.0
    sanctioned: bool = False
    cluster_ref: str | None = None
    added_at: datetime = field(default_factory=utc_now)
    evidence: str | None = None
    status: str = "active"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None

    @property
    def rejected(self) -> bool:
        return self.status == "rejected" or self.source == "analyst_rejected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "chain": self.chain,
            "label": self.label,
            "category": self.category,
            "confidence": self.confidence,
            "source": self.source,
            "tier": self.tier,
            "risk_score": self.risk_score,
            "sanctioned": self.sanctioned,
            "cluster_ref": self.cluster_ref,
            "added_at": self.added_at.isoformat(),
            "evidence": self.evidence,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


# Lower tier number = higher priority
TIER_SANCTIONS = 1
TIER_CONFIRMED_IMPORT = 1
TIER_OPEN_DATASET = 2
TIER_COSPEND = 2
TIER_HEURISTIC = 3

SOURCE_PRIORITY: dict[str, int] = {
    "ofac_sdn": 10,
    "opensanctions": 20,
    "sovereign_registry": 15,
    "kyt_import": 12,
    "analyst_confirmed": 3,
    "graphsense": 30,
    "tronscan": 35,
    "cospend_cluster": 40,
    "pattern_heuristic": 50,
    "analyst_rejected": 99,
}

TIER_ANALYST_CONFIRMED = 1
