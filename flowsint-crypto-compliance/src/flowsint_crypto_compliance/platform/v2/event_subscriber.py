"""Platform event subscribers — persist knowledge from events (RFC-0002 M4, RFC-0003)."""

from __future__ import annotations

import uuid
from typing import Any, Callable

from flowsint_crypto_compliance.platform.v2.entity_resolution import EntityResolutionEngine
from flowsint_crypto_compliance.platform.v2.evidence_center import content_hash_from_finding, osint_finding_to_evidence
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.ingest_pipeline import IngestPipeline, get_ingest_pipeline
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore, get_knowledge_graph_store
from flowsint_crypto_compliance.platform.v2.neo4j_projection import Neo4jUnifiedProjection
from flowsint_crypto_compliance.platform.v2.relation_types import RelationType

EventHandler = Callable[[PlatformEvent], None]


class PlatformEventSubscriber:
    """CQRS write-side: project PlatformEvents into Knowledge Graph via mandatory ingest path."""

    def __init__(
        self,
        *,
        knowledge: KnowledgeGraphStore | None = None,
        resolver: EntityResolutionEngine | None = None,
        neo4j: Neo4jUnifiedProjection | None = None,
        ingest: IngestPipeline | None = None,
    ) -> None:
        self._knowledge = knowledge or get_knowledge_graph_store()
        self._resolver = resolver or EntityResolutionEngine()
        self._neo4j = neo4j or Neo4jUnifiedProjection()
        self._ingest = ingest or IngestPipeline(store=self._knowledge, resolver=self._resolver)
        self._handlers: dict[EventType, list[EventHandler]] = {}

    def register(self, event_type: EventType, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch(self, event: PlatformEvent) -> dict[str, Any]:
        results: list[Any] = []
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
                results.append({"handler": handler.__name__, "ok": True})
            except Exception as exc:
                results.append({"handler": handler.__name__, "ok": False, "error": str(exc)})
        built_in = self._handle_builtin(event)
        if built_in:
            results.append(built_in)
        return {"event_id": str(event.id), "handlers": results}

    def _handle_builtin(self, event: PlatformEvent) -> dict[str, Any] | None:
        try:
            if event.event_type == EventType.CASE_OPENED:
                return self._on_case_opened(event)
            if event.event_type == EventType.EVIDENCE_CREATED:
                return self._on_evidence_created(event)
            if event.event_type == EventType.ENTITY_MERGED:
                return self._on_entity_merged(event)
            if event.event_type == EventType.OSINT_MENTION_FOUND:
                return self._on_osint_mention(event)
            if event.event_type == EventType.REVIEW_SUBMITTED:
                return self._on_review_submitted(event)
            if event.event_type == EventType.RISK_UPDATED:
                return self._on_risk_updated(event)
        except Exception as exc:
            return {"builtin": event.event_type.value, "ok": False, "error": str(exc)}
        return None

    def _on_case_opened(self, event: PlatformEvent) -> dict[str, Any]:
        tenant = event.tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
        case_ref = str(event.payload.get("case_ref") or "")
        if not case_ref:
            return {"builtin": "CaseOpened", "ok": False, "reason": "no_case_ref"}

        case_result = self._ingest.ingest(
            tenant_id=tenant,
            source_type=event.source,
            entity_type="case",
            entity_value=case_ref,
            payload=event.payload,
            actor=event.actor,
            display_name=f"Дело {case_ref}",
            confidence=0.9,
            require_relation_evidence=False,
        )
        stored_id = case_result.entity_id
        if not stored_id:
            return {"builtin": "CaseOpened", "ok": False, "errors": case_result.errors}

        case_ent = self._knowledge.get_entity(stored_id)
        if case_ent:
            self._neo4j.project_entity(case_ent, case_ref=case_ref)

        address = event.payload.get("address")
        chain = event.payload.get("chain")
        relation_id = None
        if address and case_result.evidence_id:
            wallet_result = self._ingest.ingest(
                tenant_id=tenant,
                source_type=event.source,
                entity_type="crypto_address",
                entity_value=str(address),
                payload=event.payload,
                actor=event.actor,
                chain=str(chain) if chain else None,
                relation_to=stored_id,
                relation_type=RelationType.INVESTIGATES,
                confidence=0.85,
            )
            if wallet_result.entity_id:
                wallet_ent = self._knowledge.get_entity(wallet_result.entity_id)
                if wallet_ent:
                    self._neo4j.project_entity(wallet_ent, case_ref=case_ref)
            relation_id = str(wallet_result.relation_id) if wallet_result.relation_id else None

        return {
            "builtin": "CaseOpened",
            "ok": True,
            "entity_id": str(stored_id),
            "relation_id": relation_id,
            "ingest_stages": case_result.stages_completed,
        }

    def _on_evidence_created(self, event: PlatformEvent) -> dict[str, Any]:
        tenant = event.tenant_id
        if not tenant:
            return {"builtin": "EvidenceCreated", "ok": False}
        p = event.payload
        row = {
            "id": str(event.id),
            "tenant_id": str(tenant),
            "case_id": p.get("case_id"),
            "case_ref": p.get("case_ref"),
            "entity_type": p.get("entity_type", "unknown"),
            "entity_value": p.get("entity_value", p.get("content_hash", "")),
            "source_type": p.get("source_type", event.source),
            "confidence": float(p.get("confidence") or 0.5),
            "payload": p,
        }
        evidence = osint_finding_to_evidence(row)
        stored = self._knowledge.store_evidence(evidence)
        return {"builtin": "EvidenceCreated", "ok": True, "evidence_id": str(stored.id)}

    def _on_entity_merged(self, event: PlatformEvent) -> dict[str, Any]:
        tenant = event.tenant_id
        if not tenant:
            return {"builtin": "EntityMerged", "ok": False}
        result = self._ingest.ingest(
            tenant_id=tenant,
            source_type=event.source,
            entity_type=str(event.payload.get("entity_type") or "wallet"),
            entity_value=str(event.payload.get("canonical_key") or event.payload.get("entity_value") or ""),
            payload=event.payload,
            actor=event.actor,
            chain=event.payload.get("chain"),
            confidence=float(event.payload.get("confidence") or 0.5),
            require_relation_evidence=False,
        )
        if not result.ok:
            return {"builtin": "EntityMerged", "ok": False, "errors": result.errors}
        return {
            "builtin": "EntityMerged",
            "ok": True,
            "entity_id": str(result.entity_id),
            "decision": result.merge_decision,
            "confidence": result.confidence,
            "stages": result.stages_completed,
        }

    def _on_osint_mention(self, event: PlatformEvent) -> dict[str, Any]:
        tenant = event.tenant_id
        if not tenant:
            return {"builtin": "OsintMentionFound", "ok": False}
        p = event.payload
        ev = str(p.get("entity_value") or p.get("mention") or "")
        if not ev:
            return {"builtin": "OsintMentionFound", "ok": False}

        result = self._ingest.ingest_from_event(event)
        if not result.ok:
            return {"builtin": "OsintMentionFound", "ok": False, "errors": result.errors}

        stored = self._knowledge.get_entity(result.entity_id) if result.entity_id else None
        case_ref = p.get("case_ref")
        if stored and case_ref:
            self._neo4j.project_entity(stored, case_ref=str(case_ref))

        return {
            "builtin": "OsintMentionFound",
            "ok": True,
            "entity_id": str(result.entity_id),
            "evidence_id": str(result.evidence_id),
            "merge_decision": result.merge_decision,
            "confidence": result.confidence,
            "stages": result.stages_completed,
        }

    def _on_review_submitted(self, event: PlatformEvent) -> dict[str, Any]:
        tenant = event.tenant_id
        if not tenant:
            return {"builtin": "ReviewSubmitted", "ok": False}
        p = event.payload
        address = p.get("address")
        chain = p.get("chain")
        if address:
            result = self._ingest.ingest(
                tenant_id=tenant,
                source_type=event.source,
                entity_type="crypto_address",
                entity_value=str(address),
                payload=p,
                actor=event.actor,
                chain=str(chain) if chain else None,
                confidence=float(p.get("confidence") or 0.9),
            )
            if result.entity_id:
                from flowsint_crypto_compliance.platform.v2.canonical import EntityAttribute

                ent = self._knowledge.get_entity(result.entity_id)
                if ent:
                    ent = ent.with_attribute(
                        EntityAttribute(
                            key="analyst_label",
                            value=p.get("label"),
                            source=event.actor,
                            confidence=0.95,
                        )
                    )
                    stored = self._knowledge.upsert_entity(ent)
                    return {"builtin": "ReviewSubmitted", "ok": True, "entity_id": str(stored.id)}
        return {"builtin": "ReviewSubmitted", "ok": True}

    def _on_risk_updated(self, event: PlatformEvent) -> dict[str, Any]:
        tenant = event.tenant_id
        case_ref = event.payload.get("case_ref")
        if not tenant or not case_ref:
            return {"builtin": "RiskUpdated", "ok": False}
        result = self._ingest.ingest(
            tenant_id=tenant,
            source_type=event.source,
            entity_type="case",
            entity_value=str(case_ref),
            payload=event.payload,
            actor=event.actor,
            confidence=0.8,
        )
        if result.entity_id:
            from flowsint_crypto_compliance.platform.v2.canonical import EntityAttribute

            ent = self._knowledge.get_entity(result.entity_id)
            if ent:
                ent = ent.with_attribute(
                    EntityAttribute(
                        key="risk_score",
                        value=event.payload.get("score"),
                        source=event.source,
                        confidence=0.8,
                    )
                )
                stored = self._knowledge.upsert_entity(ent)
                return {"builtin": "RiskUpdated", "ok": True, "entity_id": str(stored.id)}
        return {"builtin": "RiskUpdated", "ok": True}


_subscriber: PlatformEventSubscriber | None = None


def get_platform_event_subscriber() -> PlatformEventSubscriber:
    global _subscriber
    if _subscriber is None:
        _subscriber = PlatformEventSubscriber()
    return _subscriber
