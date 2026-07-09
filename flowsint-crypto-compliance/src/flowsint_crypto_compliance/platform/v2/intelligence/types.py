"""Intelligence Platform types — RFC-0004."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import ConfidenceBreakdown


class EngineKind(str, Enum):
    BLOCKCHAIN = "blockchain"
    OSINT = "osint"
    REGISTRY = "registry"
    BEHAVIORAL = "behavioral"
    ENTITY_RESOLUTION = "entity_resolution"
    CORRELATION = "correlation"
    ATTRIBUTION = "attribution"
    RISK = "risk"
    TIMELINE = "timeline"
    EXPLAIN = "explain"
    RECOMMENDATION = "recommendation"


@dataclass
class IntelligenceFinding:
    """Single analytic hypothesis — published to KG as evidence-backed attribute."""

    engine: EngineKind
    code: str
    title_ru: str
    description_ru: str
    confidence: float
    severity: str = "info"
    entity_type: str | None = None
    entity_value: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine.value,
            "code": self.code,
            "title_ru": self.title_ru,
            "description_ru": self.description_ru,
            "confidence": self.confidence,
            "severity": self.severity,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "evidence_refs": self.evidence_refs,
            "explain": self.explain,
            "metadata": self.metadata,
        }


@dataclass
class IntelligenceContext:
    """Read-only investigation context — engines must not call external APIs directly."""

    tenant_id: uuid.UUID
    entity_id: uuid.UUID | None = None
    address: str | None = None
    chain: str | None = None
    case_ref: str | None = None
    investigation_id: uuid.UUID | None = None
    screening: dict[str, Any] = field(default_factory=dict)
    attribution: dict[str, Any] = field(default_factory=dict)
    mentions: list[dict[str, Any]] = field(default_factory=list)
    kg_neighbors: list[dict[str, Any]] = field(default_factory=list)
    timeline_events: list[dict[str, Any]] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EngineAnalysisResult:
    engine: EngineKind
    findings: list[IntelligenceFinding] = field(default_factory=list)
    confidence: ConfidenceBreakdown | None = None
    explain: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine.value,
            "findings": [f.to_dict() for f in self.findings],
            "confidence": self.confidence.model_dump(mode="json") if self.confidence else None,
            "explain": self.explain,
            "errors": self.errors,
            "finding_count": len(self.findings),
        }


@dataclass
class IntelligenceRunResult:
    ok: bool = True
    engines_run: list[str] = field(default_factory=list)
    engine_results: list[EngineAnalysisResult] = field(default_factory=list)
    aggregate_risk_score: float = 0.0
    risk_level: str = "low"
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)
    published_evidence_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "engines_run": self.engines_run,
            "engine_results": [r.to_dict() for r in self.engine_results],
            "aggregate_risk_score": self.aggregate_risk_score,
            "risk_level": self.risk_level,
            "recommendations": self.recommendations,
            "explain": self.explain,
            "published_evidence_ids": self.published_evidence_ids,
            "errors": self.errors,
        }
