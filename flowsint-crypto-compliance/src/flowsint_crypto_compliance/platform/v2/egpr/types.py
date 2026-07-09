"""RFC-0022 EGPR v2.0 — enterprise governance types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StrategicPrinciple(str, Enum):
    """RFC-0022 Ch.2 — strategic architecture principles."""

    ENTITY_FIRST = "entity_first"
    EVIDENCE_FIRST = "evidence_first"
    API_FIRST = "api_first"
    PLUGIN_FIRST = "plugin_first"
    EXPLAINABILITY = "explainability"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    EVENT_DRIVEN = "event_driven"
    SOVEREIGN_BY_DESIGN = "sovereign_by_design"
    MODULARITY = "modularity"


class RFCLifecycleStage(str, Enum):
    """RFC-0022 Ch.5 — RFC lifecycle stages."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    IMPLEMENTED = "implemented"
    COMPLETE = "complete"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class TechDebtSeverity(str, Enum):
    """RFC-0022 Ch.8 — technical debt severity (maps to audit classification)."""

    CRITICAL = "critical"
    SIGNIFICANT = "significant"
    MODERATE = "moderate"
    COSMETIC = "cosmetic"


class RequirementKind(str, Enum):
    """RFC-0022 Ch.9 — requirement classification."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"


class RoadmapPhase(str, Enum):
    """RFC-0022 Ch.15 — four-stage product roadmap."""

    MVP = "mvp"
    ENTERPRISE = "enterprise"
    PLATFORM = "platform"
    NATIONAL_SCALE = "national_scale"


class TeamDomain(str, Enum):
    """RFC-0022 Ch.13 — platform team domains."""

    PLATFORM_CORE = "platform_core"
    INTELLIGENCE = "intelligence"
    INVESTIGATION = "investigation"
    COMPLIANCE = "compliance"
    BLOCKCHAIN = "blockchain"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    API_ECOSYSTEM = "api_ecosystem"
    ANALYST_UX = "analyst_ux"
    GOVERNANCE = "governance"


@dataclass
class ArchitectureDecisionRecord:
    """RFC-0022 Ch.4 — ADR record."""

    id: str
    date: str
    title: str
    context: str
    options: list[str]
    decision: str
    rationale: str
    consequences: list[str]
    related_rfc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date,
            "title": self.title,
            "context": self.context,
            "options": list(self.options),
            "decision": self.decision,
            "rationale": self.rationale,
            "consequences": list(self.consequences),
            "related_rfc": self.related_rfc,
        }


@dataclass
class RFCEntry:
    """RFC catalog entry with lifecycle metadata."""

    id: str
    number: int
    title: str
    title_ru: str
    stage: RFCLifecycleStage
    completion_doc: str | None = None
    doc_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "title_ru": self.title_ru,
            "stage": self.stage.value,
            "completion_doc": self.completion_doc,
            "doc_path": self.doc_path,
        }


@dataclass
class TechDebtEntry:
    """Technical debt item bridged from audit doc."""

    id: str
    severity: TechDebtSeverity
    problem: str
    evidence: str
    impact: str
    status: str
    owner: str = "architecture_board"
    plan: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "problem": self.problem,
            "evidence": self.evidence,
            "impact": self.impact,
            "status": self.status,
            "owner": self.owner,
            "plan": self.plan,
        }


@dataclass
class MaturityCriterion:
    """RFC-0022 Ch.16 — maturity checklist item."""

    id: str
    label: str
    label_ru: str
    met: bool
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "label_ru": self.label_ru,
            "met": self.met,
            "evidence": self.evidence,
        }


@dataclass
class BoardReviewRequest:
    """Architecture Board review workflow stub."""

    request_id: str
    subject: str
    requester: str
    status: str = "pending"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "subject": self.subject,
            "requester": self.requester,
            "status": self.status,
            "details": dict(self.details),
        }
