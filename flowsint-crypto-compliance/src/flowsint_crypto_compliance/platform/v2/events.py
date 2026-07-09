"""Platform event catalog — RFC-0002 Chapter 5 & 12."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = "2.0.0"


class EventType(str, Enum):
    # Acquisition L1
    WALLET_DETECTED = "WalletDetected"
    TRANSACTION_IMPORTED = "TransactionImported"
    DOCUMENT_UPLOADED = "DocumentUploaded"
    OCR_COMPLETED = "OCRCompleted"
    OSINT_MENTION_FOUND = "OsintMentionFound"
    REGISTRY_RECORD_IMPORTED = "RegistryRecordImported"
    SANCTION_HIT_DETECTED = "SanctionHitDetected"
    # Fusion L2
    RAW_DATA_VALIDATED = "RawDataValidated"
    DATA_NORMALIZED = "DataNormalized"
    DUPLICATE_SUPPRESSED = "DuplicateSuppressed"
    ENTITY_ENRICHED = "EntityEnriched"
    ATTRIBUTION_APPLIED = "AttributionApplied"
    CONFIDENCE_CALCULATED = "ConfidenceCalculated"
    FUSED_INTELLIGENCE_READY = "FusedIntelligenceReady"
    # Knowledge L3
    ENTITY_CREATED = "EntityCreated"
    ENTITY_MERGED = "EntityMerged"
    RELATION_ESTABLISHED = "RelationEstablished"
    GRAPH_EXPANDED = "GraphExpanded"
    ENTITY_VERSION_COMMITTED = "EntityVersionCommitted"
    # Analytics L4
    RISK_UPDATED = "RiskUpdated"
    PATTERN_DETECTED = "PatternDetected"
    TIMELINE_UPDATED = "TimelineUpdated"
    AI_COMPLETED = "AICompleted"
    # Investigation L5
    CASE_OPENED = "CaseOpened"
    EVIDENCE_CREATED = "EvidenceCreated"
    CASE_TRANSITION = "CaseTransition"
    REVIEW_SUBMITTED = "ReviewSubmitted"
    REPORT_GENERATED = "ReportGenerated"
    # UI interaction — RFC-0011 Ch.17 (TimelineUpdated = TIMELINE_UPDATED above)
    WALLET_OPENED = "WalletOpened"
    GRAPH_LOADED = "GraphLoaded"
    EVIDENCE_LINKED = "EvidenceLinked"
    RISK_CALCULATED = "RiskCalculated"
    RECOMMENDATION_CREATED = "RecommendationCreated"
    REPORT_UPDATED = "ReportUpdated"


class PlatformEvent(BaseModel):
    """Canonical event envelope — all services publish this shape."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: EventType
    schema_version: str = SCHEMA_VERSION
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    actor: str = "system"
    investigation_id: uuid.UUID | None = None
    correlation_id: str | None = None
    tenant_id: uuid.UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    def legacy_type(self) -> str:
        """Map v2 types to v1 ComplianceEventBus types where applicable."""
        mapping = {
            EventType.CASE_OPENED: "case_new",
            EventType.CASE_TRANSITION: "case_transition",
            EventType.FUSED_INTELLIGENCE_READY: "fusion_completed",
            EventType.RISK_UPDATED: "risk_score_changed",
            EventType.EVIDENCE_CREATED: "evidence_created",
            EventType.REPORT_GENERATED: "report_downloaded",
        }
        return mapping.get(self.event_type, self.event_type.value)
