"""RFC-0015 CRIF core types — Ch.1–3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RegistrySourceCategory(str, Enum):
    """RFC-0015 Ch.3 — registry source categories."""

    GOVERNMENT = "government"
    SANCTIONS = "sanctions"
    LICENSES = "licenses"
    CORPORATE = "corporate"


class CRIFStage(str, Enum):
    """RFC-0015 Ch.1 — pipeline stages."""

    REGISTRY_SOURCE = "registry_source"
    REGISTRY_CONNECTOR = "registry_connector"
    NORMALIZER = "normalizer"
    SCHEMA_VALIDATOR = "schema_validator"
    ENTITY_RESOLVER = "entity_resolver"
    EVIDENCE_GENERATOR = "evidence_generator"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    RISK_ENGINE = "risk_engine"
    INVESTIGATION_WORKSPACE = "investigation_workspace"


class CanonicalEntityType(str, Enum):
    """RFC-0015 — canonical compliance entity types."""

    ORGANIZATION = "Organization"
    LICENSE = "License"
    REGISTRY_RECORD = "RegistryRecord"
    SANCTION_ENTRY = "SanctionEntry"
    COUNTRY = "Country"
    JURISDICTION = "Jurisdiction"
    BENEFICIAL_OWNER = "BeneficialOwner"
    REGULATOR = "Regulator"
    COMPLIANCE_RULE = "ComplianceRule"


class ConnectorLifecycle(str, Enum):
    """RFC-0015 Ch.4 — registry connector lifecycle."""

    CONNECT = "connect"
    AUTHENTICATE = "authenticate"
    COLLECT = "collect"
    NORMALIZE = "normalize"
    VALIDATE = "validate"
    PUBLISH = "publish"
    SHUTDOWN = "shutdown"


@dataclass
class CRIFPipelineResult:
    """Outcome of full CRIF pipeline run."""

    ok: bool
    connector_id: str
    source_category: str
    organization_key: str | None = None
    stages: list[str] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    normalized: list[dict[str, Any]] = field(default_factory=list)
    resolved_entities: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    compliance_checks: list[dict[str, Any]] = field(default_factory=list)
    fusion_events: int = 0
    kg_ingested: int = 0
    risk_events: int = 0
    workspace_events: int = 0
    errors: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "connector_id": self.connector_id,
            "source_category": self.source_category,
            "organization_key": self.organization_key,
            "stages": self.stages,
            "record_count": len(self.records),
            "normalized_count": len(self.normalized),
            "resolved_entity_count": len(self.resolved_entities),
            "evidence_count": len(self.evidence),
            "compliance_check_count": len(self.compliance_checks),
            "fusion_events": self.fusion_events,
            "kg_ingested": self.kg_ingested,
            "risk_events": self.risk_events,
            "workspace_events": self.workspace_events,
            "errors": self.errors,
            "explain": self.explain,
        }
