"""RFC-0017 ECCF core types — Ch.1–4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EvidenceCategory(str, Enum):
    """RFC-0017 Ch.2 — evidence categories."""

    BLOCKCHAIN = "blockchain"
    REGISTRY = "registry"
    DOCUMENT = "document"
    OSINT = "osint"
    USER = "user"


class ECCFStage(str, Enum):
    """RFC-0017 Ch.1 — pipeline stages."""

    SOURCE = "source"
    COLLECTOR = "collector"
    EVIDENCE_GENERATOR = "evidence_generator"
    REPOSITORY = "repository"
    INTEGRITY = "integrity"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    TIMELINE = "timeline"
    REPORT = "report"
    ARCHIVE = "archive"


class EvidenceLifecycle(str, Enum):
    """RFC-0017 Ch.4 — evidence lifecycle states."""

    DRAFT = "draft"
    REGISTERED = "registered"
    VALIDATED = "validated"
    LINKED = "linked"
    IN_REPORT = "in_report"
    ARCHIVED = "archived"


@dataclass
class ECCFRecord:
    """Canonical ECCF evidence record — immutable content after registration."""

    evidence_id: str
    tenant_id: str
    category: EvidenceCategory
    version: int
    content_hash: str
    size_bytes: int
    mime_type: str
    lifecycle: EvidenceLifecycle
    source_type: str
    entity_type: str
    entity_value: str
    case_ref: str | None = None
    kg_evidence_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    prior_version_id: str | None = None
    immutable: bool = False
    archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "tenant_id": self.tenant_id,
            "category": self.category.value,
            "version": self.version,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "lifecycle": self.lifecycle.value,
            "source_type": self.source_type,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "case_ref": self.case_ref,
            "kg_evidence_id": self.kg_evidence_id,
            "payload": self.payload,
            "provenance": self.provenance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "prior_version_id": self.prior_version_id,
            "immutable": self.immutable,
            "archived": self.archived,
        }


@dataclass
class ECCFPipelineResult:
    """Outcome of full ECCF pipeline run."""

    ok: bool
    evidence_id: str | None = None
    stages: list[str] = field(default_factory=list)
    record: dict[str, Any] | None = None
    deduplicated: bool = False
    integrity_ok: bool = False
    kg_linked: bool = False
    errors: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "evidence_id": self.evidence_id,
            "stages": self.stages,
            "record": self.record,
            "deduplicated": self.deduplicated,
            "integrity_ok": self.integrity_ok,
            "kg_linked": self.kg_linked,
            "errors": self.errors,
            "explain": self.explain,
        }
