"""RFC-0016 RDE core types — Ch.1–3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RDEStage(str, Enum):
    """RFC-0016 Ch.1 — pipeline stages."""

    FACT_ACQUISITION = "fact_acquisition"
    NORMALIZE = "normalize"
    CORRELATE = "correlate"
    AGGREGATE_FACTORS = "aggregate_factors"
    CALCULATE_SCORES = "calculate_scores"
    RULE_CHECK = "rule_check"
    EXPLAIN = "explain"
    DELIVER = "deliver"


class FactorGroup(str, Enum):
    """RFC-0016 Ch.3 — risk factor groups."""

    BLOCKCHAIN = "blockchain"
    REGISTRY = "registry"
    OSINT = "osint"
    GRAPH = "graph"
    EVIDENCE = "evidence"


class RiskLevel(str, Enum):
    """RFC-0016 Ch.7 — risk levels."""

    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DecisionRecommendation:
    """RFC-0016 Ch.9 — analyst recommendation (NOT a decision)."""

    id: str
    action: str
    priority: str
    rationale_ru: str
    requires_analyst: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "priority": self.priority,
            "rationale_ru": self.rationale_ru,
            "requires_analyst": self.requires_analyst,
            "metadata": self.metadata,
        }


@dataclass
class RDEAssessmentResult:
    """Outcome of full RDE assessment pipeline."""

    ok: bool
    entity_key: str
    case_ref: str | None = None
    stages: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.INFORMATIONAL
    composite_score: float = 0.0
    factor_scores: dict[str, float] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)
    correlations: list[dict[str, Any]] = field(default_factory=list)
    rule_events: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[DecisionRecommendation] = field(default_factory=list)
    priorities: list[dict[str, Any]] = field(default_factory=list)
    temporal: dict[str, Any] = field(default_factory=dict)
    explain: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "entity_key": self.entity_key,
            "case_ref": self.case_ref,
            "stages": self.stages,
            "risk_level": self.risk_level.value,
            "composite_score": round(self.composite_score, 2),
            "factor_scores": {k: round(v, 2) for k, v in self.factor_scores.items()},
            "confidence": self.confidence,
            "correlation_count": len(self.correlations),
            "correlations": self.correlations,
            "rule_event_count": len(self.rule_events),
            "rule_events": self.rule_events,
            "recommendation_count": len(self.recommendations),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "priorities": self.priorities,
            "temporal": self.temporal,
            "explain": self.explain,
            "errors": self.errors,
            "auto_decision": False,
            "source_mutation": False,
        }
