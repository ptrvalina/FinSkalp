"""RFC-0018 EIA core types — Ch.1–3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AITaskType(str, Enum):
    """RFC-0018 Ch.2 — supported assistant task types."""

    SUMMARY = "summary"
    EXPLAIN_RISK = "explain_risk"
    DESCRIBE_LINKS = "describe_links"
    QUESTIONS = "questions"
    REPORT_OUTLINE = "report_outline"
    EXPLAIN_CHANGES = "explain_changes"
    CONTRADICTIONS = "contradictions"
    DATA_GAPS = "data_gaps"


class EIAStage(str, Enum):
    """RFC-0018 Ch.1 — orchestrator pipeline stages."""

    CONTEXT = "context"
    PROMPT = "prompt"
    MODEL = "model"
    EXPLANATION = "explanation"
    RECOMMENDATION = "recommendation"
    SUMMARY = "summary"
    DELIVER = "deliver"


@dataclass
class Citation:
    """Evidence-backed citation with ECCF evidence ID."""

    evidence_id: str | None
    source_type: str
    label_ru: str
    confidence: float = 0.0
    excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "label_ru": self.label_ru,
            "confidence": self.confidence,
            "excerpt": self.excerpt,
        }


@dataclass
class AssistantResponse:
    """RFC-0018 Ch.3 — unified assistant response envelope."""

    ok: bool = True
    task_type: str = ""
    case_ref: str | None = None
    entity_keys: list[str] = field(default_factory=list)
    narrative_ru: str = ""
    citations: list[Citation] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    limitations: list[str] = field(default_factory=list)
    requires_analyst_confirmation: bool = True
    stages: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "task_type": self.task_type,
            "case_ref": self.case_ref,
            "entity_keys": self.entity_keys,
            "narrative_ru": self.narrative_ru,
            "citations": [c.to_dict() for c in self.citations],
            "recommendations": self.recommendations,
            "confidence": self.confidence,
            "limitations": self.limitations,
            "requires_analyst_confirmation": self.requires_analyst_confirmation,
            "stages": self.stages,
            "explain": self.explain,
            "errors": self.errors,
        }
