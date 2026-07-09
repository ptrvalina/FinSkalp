"""RFC-0005 Investigation Platform types."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EvidenceStatus(str, Enum):
    REGISTERED = "registered"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class ReportKind(str, Enum):
    ANALYTICAL = "analytical"
    FINANCIAL_FLOWS = "financial_flows"
    ENTITIES = "entities"
    RELATIONS = "relations"
    EVIDENCE = "evidence"
    RISK = "risk"
    EXECUTIVE = "executive"
    TECHNICAL_APPENDIX = "technical_appendix"


class WorkspacePanel(str, Enum):
    CASE_CARD = "case_card"
    GRAPH = "graph"
    TIMELINE = "timeline"
    EVIDENCE = "evidence"
    FLOWS = "flows"
    HYPOTHESES = "hypotheses"
    RECOMMENDATIONS = "recommendations"
    AUDIT_LOG = "audit_log"
    SEARCH = "search"
    REPORTS = "reports"


class EvidenceRecord(BaseModel):
    id: uuid.UUID
    source_type: str
    content_hash: str
    discovered_at: datetime
    acquisition_method: str = "automated_collection"
    author: str = "system"
    trust_level: float = 0.5
    status: EvidenceStatus = EvidenceStatus.REGISTERED
    entity_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status_history: list[dict[str, Any]] = Field(default_factory=list)


class InvestigationWorkspaceView(BaseModel):
    case_ref: str
    compliance_case_id: uuid.UUID | None = None
    investigation_id: uuid.UUID | None = None
    entity_id: uuid.UUID | None = None
    workflow: dict[str, Any] = Field(default_factory=dict)
    panels: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    timeline_count: int = 0
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    collaboration: dict[str, Any] = Field(default_factory=dict)
