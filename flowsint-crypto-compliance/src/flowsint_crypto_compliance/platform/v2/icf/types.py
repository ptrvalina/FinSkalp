"""RFC-0014 ICF core types — Ch.1–3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceCategory(str, Enum):
    """RFC-0014 Ch.2 — source categories."""

    BLOCKCHAIN = "blockchain"
    PUBLIC_WEB = "public_web"
    NEWS = "news"
    GOVERNMENT_REGISTRIES = "government_registries"
    CORPORATE_DATA = "corporate_data"
    DOCUMENTS = "documents"
    IMAGES = "images"
    USER_UPLOADED_EVIDENCE = "user_uploaded_evidence"


class CollectorLifecycle(str, Enum):
    """RFC-0014 Ch.3 — collector lifecycle stages."""

    INITIALIZE = "initialize"
    AUTHENTICATE = "authenticate"
    COLLECT = "collect"
    NORMALIZE = "normalize"
    VALIDATE = "validate"
    PUBLISH = "publish"
    SHUTDOWN = "shutdown"


class ICFStage(str, Enum):
    """RFC-0014 Ch.1 — pipeline stages."""

    SOURCE = "source"
    COLLECTOR = "collector"
    NORMALIZER = "normalizer"
    VALIDATOR = "validator"
    ENTITY_EXTRACTOR = "entity_extractor"
    EVIDENCE_GENERATOR = "evidence_generator"
    FUSION = "fusion"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class CollectorStage(str, Enum):
    """RFC-0014 Ch.16 — lifecycle management stages."""

    DRAFT = "draft"
    TESTING = "testing"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class ICFPipelineResult:
    """Outcome of full ICF pipeline run."""

    ok: bool
    connector_id: str
    source_category: str
    stages: list[str] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    normalized: list[dict[str, Any]] = field(default_factory=list)
    extracted_entities: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    fusion_events: int = 0
    kg_ingested: int = 0
    quality_score: float = 0.0
    errors: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "connector_id": self.connector_id,
            "source_category": self.source_category,
            "stages": self.stages,
            "record_count": len(self.records),
            "normalized_count": len(self.normalized),
            "extracted_entity_count": len(self.extracted_entities),
            "evidence_count": len(self.evidence),
            "fusion_events": self.fusion_events,
            "kg_ingested": self.kg_ingested,
            "quality_score": self.quality_score,
            "errors": self.errors,
            "explain": self.explain,
        }
