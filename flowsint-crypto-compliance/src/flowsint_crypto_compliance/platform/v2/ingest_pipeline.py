"""Mandatory ingest path — RFC-0003 Ch.5 (no bypass)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import (
    Evidence,
    KnowledgeRelation,
    RelationWithoutEvidenceError,
    normalize_entity_type,
)
from flowsint_crypto_compliance.platform.v2.confidence_model import calculate_confidence
from flowsint_crypto_compliance.platform.v2.entity_resolution import EntityResolutionEngine, MergeDecision
from flowsint_crypto_compliance.platform.v2.evidence_center import content_hash_from_finding, osint_finding_to_evidence
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.graph_history import GraphHistoryService
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore, get_knowledge_graph_store
from flowsint_crypto_compliance.platform.v2.relation_types import RelationType


@dataclass
class IngestResult:
    """Outcome of mandatory ingest pipeline."""

    entity_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None
    relation_id: uuid.UUID | None = None
    merge_decision: str = "create"
    confidence: float = 0.5
    explain: dict[str, Any] = field(default_factory=dict)
    stages_completed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and self.entity_id is not None


class IngestPipeline:
    """
    Mandatory path: Source → Event → Normalize → Entity Resolution → Knowledge Graph → Evidence.

    Direct writes to the graph bypassing this pipeline are discouraged.
    """

    def __init__(
        self,
        *,
        store: KnowledgeGraphStore | None = None,
        resolver: EntityResolutionEngine | None = None,
        history: GraphHistoryService | None = None,
    ) -> None:
        self._store = store or get_knowledge_graph_store()
        self._resolver = resolver or EntityResolutionEngine()
        self._history = history or GraphHistoryService(store=self._store)

    def ingest(
        self,
        *,
        tenant_id: uuid.UUID,
        source_type: str,
        entity_type: str,
        entity_value: str,
        payload: dict[str, Any] | None = None,
        actor: str = "system",
        case_id: uuid.UUID | None = None,
        case_ref: str | None = None,
        relation_to: uuid.UUID | None = None,
        relation_type: str | RelationType = RelationType.RELATED_TO,
        chain: str | None = None,
        confidence: float = 0.5,
        display_name: str | None = None,
        require_relation_evidence: bool = True,
    ) -> IngestResult:
        result = IngestResult()
        payload = dict(payload or {})
        stages = result.stages_completed

        # Stage 1: Source → Event
        event = PlatformEvent(
            event_type=EventType.OSINT_MENTION_FOUND,
            source=source_type,
            tenant_id=tenant_id,
            actor=actor,
            payload={
                "entity_type": entity_type,
                "entity_value": entity_value,
                "source_type": source_type,
                "confidence": confidence,
                "case_ref": case_ref,
                "case_id": str(case_id) if case_id else None,
                **payload,
            },
        )
        stages.append("source_to_event")

        # Stage 2: Normalize
        norm_et = normalize_entity_type(entity_type)
        from flowsint_crypto_compliance.platform.v2.entity_resolution import normalize_signal

        raw_et, normalized = normalize_signal(entity_type, entity_value)
        payload["normalized_value"] = normalized
        payload["canonical_entity_type"] = norm_et.value
        stages.append("normalize")

        er_context = {k: payload[k] for k in ("timestamp", "geo", "behavior") if k in payload}

        # Stage 3: Entity Resolution (scored)
        resolution = self._resolver.resolve_with_scoring(
            tenant_id=tenant_id,
            entity_type=entity_type,
            value=entity_value,
            chain=chain,
            source=source_type,
            confidence=confidence,
            display_name=display_name,
            store=self._store,
            context=er_context or None,
        )
        entity = resolution.entity
        result.merge_decision = resolution.decision.value
        result.confidence = resolution.confidence
        result.explain = resolution.explain
        stages.append("entity_resolution")

        # Stage 4: Knowledge Graph (upsert entity + version)
        stored_entity = self._store.upsert_entity(entity)
        result.entity_id = stored_entity.id
        stages.append("knowledge_graph")

        # Stage 5: Evidence
        ev_row = {
            "id": str(uuid.uuid4()),
            "tenant_id": str(tenant_id),
            "case_id": str(case_id) if case_id else None,
            "case_ref": case_ref,
            "entity_type": entity_type,
            "entity_value": entity_value,
            "source_type": source_type,
            "confidence": confidence,
            "payload": {**payload, "event_id": str(event.id)},
        }
        evidence = osint_finding_to_evidence(ev_row)
        evidence = evidence.model_copy(
            update={
                "entity_id": stored_entity.id,
                "acquisition_method": payload.get("acquisition_method", "automated_collection"),
                "original_uri": payload.get("original_uri") or payload.get("url"),
            }
        )
        cb = calculate_confidence(
            sources=[source_type],
            signals=[{"value": normalized, "entity_type": norm_et.value}],
            trust_levels=[evidence.trust_level],
            discovered_at=evidence.discovered_at,
            base_confidence=confidence,
        )
        evidence = evidence.model_copy(
            update={"explain": cb.explain, "trust": evidence.trust.model_copy()}
        )
        stored_evidence = self._store.store_evidence(evidence)
        result.evidence_id = stored_evidence.id
        stages.append("evidence")

        # Optional relation (requires evidence per RFC-0003)
        if relation_to is not None:
            rel_type = relation_type.value if isinstance(relation_type, RelationType) else str(relation_type)
            if require_relation_evidence and not stored_evidence.id:
                result.errors.append("Связь без доказательства не может считаться фактом")
            else:
                try:
                    rel = KnowledgeRelation(
                        tenant_id=tenant_id,
                        from_entity_id=stored_entity.id,
                        to_entity_id=relation_to,
                        relation_type=rel_type,
                        source=source_type,
                        confidence=cb.composite,
                        acquisition_method=payload.get("acquisition_method", "inferred"),
                        actor=actor,
                        evidence_ids=[stored_evidence.id],
                    )
                    rel_id = self._store.link_relation(rel, require_evidence=require_relation_evidence)
                    result.relation_id = rel_id
                    stages.append("relation_create")
                except RelationWithoutEvidenceError as exc:
                    result.errors.append(str(exc))

        return result

    def ingest_from_event(self, event: PlatformEvent) -> IngestResult:
        """Project a PlatformEvent through the mandatory path."""
        if not event.tenant_id:
            return IngestResult(errors=["tenant_id обязателен"])
        p = event.payload
        return self.ingest(
            tenant_id=event.tenant_id,
            source_type=str(p.get("source_type") or event.source),
            entity_type=str(p.get("entity_type") or "unknown"),
            entity_value=str(p.get("entity_value") or p.get("mention") or ""),
            payload=p,
            actor=event.actor,
            case_id=uuid.UUID(str(p["case_id"])) if p.get("case_id") else None,
            case_ref=p.get("case_ref"),
            chain=p.get("chain"),
            confidence=float(p.get("confidence") or 0.5),
            relation_to=uuid.UUID(str(p["relation_to"])) if p.get("relation_to") else None,
            relation_type=p.get("relation_type") or RelationType.RELATED_TO,
        )


_ingest_pipeline: IngestPipeline | None = None


def get_ingest_pipeline() -> IngestPipeline:
    global _ingest_pipeline
    if _ingest_pipeline is None:
        _ingest_pipeline = IngestPipeline()
    return _ingest_pipeline
