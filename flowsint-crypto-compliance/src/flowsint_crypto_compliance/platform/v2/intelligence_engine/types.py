"""RFC-0006 Intelligence Engine types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class IntelligenceQuestion(str, Enum):
    WHAT_HAPPENED = "what_happened"
    WHY_HAPPENED = "why_happened"
    WHO_INVOLVED = "who_involved"
    WHAT_LINKED = "what_linked"
    WHAT_TO_CHECK = "what_to_check"


@dataclass
class IntelligenceScoreBundle:
    """RFC-0006 Ch.9 — eight independent scores (0–100)."""

    identity_confidence: float = 0.0
    evidence_strength: float = 0.0
    relationship_confidence: float = 0.0
    behavior_stability: float = 0.0
    source_reliability: float = 0.0
    case_completeness: float = 0.0
    hypothesis_confidence: float = 0.0
    investigation_progress: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "identity_confidence": round(self.identity_confidence, 2),
            "evidence_strength": round(self.evidence_strength, 2),
            "relationship_confidence": round(self.relationship_confidence, 2),
            "behavior_stability": round(self.behavior_stability, 2),
            "source_reliability": round(self.source_reliability, 2),
            "case_completeness": round(self.case_completeness, 2),
            "hypothesis_confidence": round(self.hypothesis_confidence, 2),
            "investigation_progress": round(self.investigation_progress, 2),
        }

    def weakest(self) -> tuple[str, float]:
        d = self.to_dict()
        key = min(d, key=d.get)
        return key, d[key]


@dataclass
class PatternHit:
    code: str
    title_ru: str
    description_ru: str
    confidence: float
    signals: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title_ru": self.title_ru,
            "description_ru": self.description_ru,
            "confidence": self.confidence,
            "signals": self.signals,
            "explain": self.explain,
        }


@dataclass
class Hypothesis:
    code: str
    statement_ru: str
    confidence: float
    is_hypothesis: bool = True
    evidence_refs: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "statement_ru": self.statement_ru,
            "confidence": self.confidence,
            "is_hypothesis": self.is_hypothesis,
            "evidence_refs": self.evidence_refs,
            "explain": self.explain,
        }


@dataclass
class IntelligenceEngineContext:
    tenant_id: uuid.UUID
    case_ref: str | None = None
    investigation_id: uuid.UUID | None = None
    entity_id: uuid.UUID | None = None
    address: str | None = None
    chain: str | None = None
    screening: dict[str, Any] = field(default_factory=dict)
    attribution: dict[str, Any] = field(default_factory=dict)
    mentions: list[dict[str, Any]] = field(default_factory=list)
    fusion_records: list[dict[str, Any]] = field(default_factory=list)
    prior_findings: list[dict[str, Any]] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class IntelligenceEngineResult:
    ok: bool = True
    pipeline_stages: list[str] = field(default_factory=list)
    patterns: list[PatternHit] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    scores: IntelligenceScoreBundle = field(default_factory=IntelligenceScoreBundle)
    explain: dict[str, Any] = field(default_factory=dict)
    questions_answered: dict[str, str] = field(default_factory=dict)
    memory_updates: list[dict[str, Any]] = field(default_factory=list)
    published_evidence_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "rfc": "RFC-0006",
            "pipeline_stages": self.pipeline_stages,
            "patterns": [p.to_dict() for p in self.patterns],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "recommendations": self.recommendations,
            "scores": self.scores.to_dict(),
            "weakest_score": {"metric": self.scores.weakest()[0], "value": self.scores.weakest()[1]},
            "explain": self.explain,
            "questions_answered": self.questions_answered,
            "memory_updates": self.memory_updates,
            "published_evidence_ids": self.published_evidence_ids,
            "errors": self.errors,
        }
