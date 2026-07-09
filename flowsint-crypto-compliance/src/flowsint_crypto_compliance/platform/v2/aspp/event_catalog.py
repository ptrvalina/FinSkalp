"""RFC-0019 Ch.7 — platform event catalog with version + schema refs."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.versioning import PLATFORM_API_VERSION
from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION, EventType


def _event_entry(event_type: EventType, *, layer: str, schema_ref: str) -> dict[str, Any]:
    return {
        "event_type": event_type.value,
        "version": SCHEMA_VERSION,
        "schema_ref": schema_ref,
        "layer": layer,
        "envelope": "PlatformEvent",
    }


def event_catalog() -> dict[str, Any]:
    entries: list[dict[str, Any]] = [
        _event_entry(EventType.WALLET_DETECTED, layer="acquisition", schema_ref="events/acquisition/WalletDetected.json"),
        _event_entry(EventType.TRANSACTION_IMPORTED, layer="acquisition", schema_ref="events/acquisition/TransactionImported.json"),
        _event_entry(EventType.DOCUMENT_UPLOADED, layer="acquisition", schema_ref="events/acquisition/DocumentUploaded.json"),
        _event_entry(EventType.OCR_COMPLETED, layer="acquisition", schema_ref="events/acquisition/OCRCompleted.json"),
        _event_entry(EventType.OSINT_MENTION_FOUND, layer="acquisition", schema_ref="events/acquisition/OsintMentionFound.json"),
        _event_entry(EventType.REGISTRY_RECORD_IMPORTED, layer="acquisition", schema_ref="events/acquisition/RegistryRecordImported.json"),
        _event_entry(EventType.SANCTION_HIT_DETECTED, layer="acquisition", schema_ref="events/acquisition/SanctionHitDetected.json"),
        _event_entry(EventType.RAW_DATA_VALIDATED, layer="fusion", schema_ref="events/fusion/RawDataValidated.json"),
        _event_entry(EventType.DATA_NORMALIZED, layer="fusion", schema_ref="events/fusion/DataNormalized.json"),
        _event_entry(EventType.DUPLICATE_SUPPRESSED, layer="fusion", schema_ref="events/fusion/DuplicateSuppressed.json"),
        _event_entry(EventType.ENTITY_ENRICHED, layer="fusion", schema_ref="events/fusion/EntityEnriched.json"),
        _event_entry(EventType.ATTRIBUTION_APPLIED, layer="fusion", schema_ref="events/fusion/AttributionApplied.json"),
        _event_entry(EventType.CONFIDENCE_CALCULATED, layer="fusion", schema_ref="events/fusion/ConfidenceCalculated.json"),
        _event_entry(EventType.FUSED_INTELLIGENCE_READY, layer="fusion", schema_ref="events/fusion/FusedIntelligenceReady.json"),
        _event_entry(EventType.ENTITY_CREATED, layer="knowledge", schema_ref="events/knowledge/EntityCreated.json"),
        _event_entry(EventType.ENTITY_MERGED, layer="knowledge", schema_ref="events/knowledge/EntityMerged.json"),
        _event_entry(EventType.RELATION_ESTABLISHED, layer="knowledge", schema_ref="events/knowledge/RelationEstablished.json"),
        _event_entry(EventType.GRAPH_EXPANDED, layer="knowledge", schema_ref="events/knowledge/GraphExpanded.json"),
        _event_entry(EventType.ENTITY_VERSION_COMMITTED, layer="knowledge", schema_ref="events/knowledge/EntityVersionCommitted.json"),
        _event_entry(EventType.RISK_UPDATED, layer="analytics", schema_ref="events/analytics/RiskUpdated.json"),
        _event_entry(EventType.PATTERN_DETECTED, layer="analytics", schema_ref="events/analytics/PatternDetected.json"),
        _event_entry(EventType.TIMELINE_UPDATED, layer="analytics", schema_ref="events/analytics/TimelineUpdated.json"),
        _event_entry(EventType.AI_COMPLETED, layer="analytics", schema_ref="events/analytics/AICompleted.json"),
        _event_entry(EventType.CASE_OPENED, layer="investigation", schema_ref="events/investigation/CaseOpened.json"),
        _event_entry(EventType.EVIDENCE_CREATED, layer="investigation", schema_ref="events/investigation/EvidenceCreated.json"),
        _event_entry(EventType.CASE_TRANSITION, layer="investigation", schema_ref="events/investigation/CaseTransition.json"),
        _event_entry(EventType.REVIEW_SUBMITTED, layer="investigation", schema_ref="events/investigation/ReviewSubmitted.json"),
        _event_entry(EventType.REPORT_GENERATED, layer="investigation", schema_ref="events/investigation/ReportGenerated.json"),
        _event_entry(EventType.WALLET_OPENED, layer="ui", schema_ref="events/ui/WalletOpened.json"),
        _event_entry(EventType.GRAPH_LOADED, layer="ui", schema_ref="events/ui/GraphLoaded.json"),
        _event_entry(EventType.EVIDENCE_LINKED, layer="ui", schema_ref="events/ui/EvidenceLinked.json"),
        _event_entry(EventType.RISK_CALCULATED, layer="ui", schema_ref="events/ui/RiskCalculated.json"),
        _event_entry(EventType.RECOMMENDATION_CREATED, layer="ui", schema_ref="events/ui/RecommendationCreated.json"),
        _event_entry(EventType.REPORT_UPDATED, layer="ui", schema_ref="events/ui/ReportUpdated.json"),
    ]
    by_layer: dict[str, list[str]] = {}
    for e in entries:
        by_layer.setdefault(e["layer"], []).append(e["event_type"])
    return {
        "rfc": "RFC-0019",
        "chapter": 7,
        "schema_version": PLATFORM_API_VERSION,
        "event_schema_version": SCHEMA_VERSION,
        "total_events": len(entries),
        "events": entries,
        "events_by_layer": by_layer,
        "bus": "platform/v2/event_bus.py",
        "principle_ru": "Event Bus — единый каталог событий с версией и схемой",
    }
