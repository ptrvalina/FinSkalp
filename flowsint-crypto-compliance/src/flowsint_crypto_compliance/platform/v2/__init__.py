"""FinSkalp platform v2 — canonical investigation architecture (RFC-0002, RFC-0003)."""

from flowsint_crypto_compliance.platform.v2.canonical import (
    ConfidenceBreakdown,
    Entity,
    EntityAttribute,
    EntityRelation,
    EntityType,
    Evidence,
    KnowledgeRelation,
    RelationWithoutEvidenceError,
    TrustLevel,
    normalize_entity_type,
)
from flowsint_crypto_compliance.platform.v2.confidence_model import calculate_confidence
from flowsint_crypto_compliance.platform.v2.entity_resolution import (
    EntityResolutionEngine,
    MatchSignal,
    MergeDecision,
)
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.event_bus import PlatformEventBus, get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.evidence_center import dual_write_osint_finding
from flowsint_crypto_compliance.platform.v2.fusion_pipeline import FusionPipeline, FusionStage
from flowsint_crypto_compliance.platform.v2.graph_history import GraphHistoryService
from flowsint_crypto_compliance.platform.v2.ingest_pipeline import IngestPipeline, get_ingest_pipeline
from flowsint_crypto_compliance.platform.v2.intelligence import (
    get_intelligence_orchestrator,
    intelligence_platform_manifest,
    run_intelligence_analysis,
)
from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace
from flowsint_crypto_compliance.platform.v2.knowledge_graph import KnowledgeGraphService, get_knowledge_graph_service
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore, get_knowledge_graph_store
from flowsint_crypto_compliance.platform.v2.plugin_registry import PluginKind, PluginRegistry, get_plugin_registry
from flowsint_crypto_compliance.platform.v2.relation_types import RelationType

__all__ = [
    "Entity",
    "EntityAttribute",
    "EntityRelation",
    "KnowledgeRelation",
    "EntityType",
    "Evidence",
    "TrustLevel",
    "ConfidenceBreakdown",
    "RelationWithoutEvidenceError",
    "normalize_entity_type",
    "RelationType",
    "MatchSignal",
    "MergeDecision",
    "EventType",
    "PlatformEvent",
    "PlatformEventBus",
    "get_platform_event_bus",
    "FusionPipeline",
    "FusionStage",
    "PluginKind",
    "PluginRegistry",
    "get_plugin_registry",
    "EntityResolutionEngine",
    "KnowledgeGraphStore",
    "get_knowledge_graph_store",
    "KnowledgeGraphService",
    "get_knowledge_graph_service",
    "InvestigationWorkspace",
    "dual_write_osint_finding",
    "IngestPipeline",
    "get_ingest_pipeline",
    "GraphHistoryService",
    "calculate_confidence",
    "get_intelligence_orchestrator",
    "intelligence_platform_manifest",
    "run_intelligence_analysis",
]
