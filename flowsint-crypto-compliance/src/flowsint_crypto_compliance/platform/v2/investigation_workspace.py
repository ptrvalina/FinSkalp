"""Investigation Workspace — bridge ComplianceCase + Investigation → case Entity (RFC-0002 M2)."""

from __future__ import annotations

import os
import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import EntityType
from flowsint_crypto_compliance.platform.v2.entity_resolution import EntityResolutionEngine
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore, get_knowledge_graph_store
from flowsint_crypto_compliance.platform.v2.neo4j_projection import Neo4jUnifiedProjection


def default_tenant_id() -> uuid.UUID:
    return uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


class InvestigationWorkspace:
    """L5 workspace: unify ComplianceCase and Investigation under canonical case Entity."""

    def __init__(
        self,
        *,
        knowledge: KnowledgeGraphStore | None = None,
        resolver: EntityResolutionEngine | None = None,
        neo4j: Neo4jUnifiedProjection | None = None,
    ) -> None:
        self._knowledge = knowledge or get_knowledge_graph_store()
        self._resolver = resolver or EntityResolutionEngine()
        self._neo4j = neo4j or Neo4jUnifiedProjection()

    def open_case(
        self,
        *,
        case_ref: str,
        tenant_id: uuid.UUID | None = None,
        investigation_id: uuid.UUID | None = None,
        compliance_case_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        actor: str = "system",
        source: str = "investigation_workspace",
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create canonical case Entity and emit CaseOpened."""
        tenant = tenant_id or default_tenant_id()
        case_entity = self._resolver.resolve_signal(
            tenant_id=tenant,
            entity_type="case",
            value=case_ref,
            display_name=f"Дело {case_ref}",
            source=source,
            confidence=1.0,
        )
        stored = self._knowledge.upsert_entity(case_entity)
        self._neo4j.project_entity(stored, case_ref=case_ref)

        payload = {
            "case_ref": case_ref,
            "entity_id": str(stored.id),
            "compliance_case_id": str(compliance_case_id) if compliance_case_id else None,
            "owner_id": str(owner_id) if owner_id else None,
            **(extra_payload or {}),
        }
        bus = get_platform_event_bus()
        bus.publish(
            PlatformEvent(
                event_type=EventType.CASE_OPENED,
                source=source,
                tenant_id=tenant,
                investigation_id=investigation_id,
                actor=actor,
                payload=payload,
            )
        )
        return {
            "case_ref": case_ref,
            "entity_id": str(stored.id),
            "investigation_id": str(investigation_id) if investigation_id else None,
            "compliance_case_id": str(compliance_case_id) if compliance_case_id else None,
        }

    def bridge_compliance_case(self, case: Any, *, actor: str = "system") -> dict[str, Any]:
        """Bridge existing ComplianceCase ORM row to canonical case Entity."""
        inv_id = getattr(case, "investigation_id", None)
        return self.open_case(
            case_ref=str(case.case_ref),
            investigation_id=inv_id,
            compliance_case_id=getattr(case, "id", None),
            owner_id=getattr(case, "owner_id", None),
            actor=actor,
            source="compliance_service",
        )

    def attach_investigation(
        self,
        *,
        case_ref: str,
        investigation_id: uuid.UUID,
        address: str | None = None,
        chain: str | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Link wallet signal to case entity when investigation starts."""
        tenant = tenant_id or default_tenant_id()
        case_ent = self._resolver.resolve_signal(
            tenant_id=tenant,
            entity_type="case",
            value=case_ref,
            display_name=f"Дело {case_ref}",
        )
        case_stored = self._knowledge.upsert_entity(case_ent)
        wallet_id = None
        if address:
            wallet_ent = self._resolver.resolve_signal(
                tenant_id=tenant,
                entity_type="crypto_address",
                value=address,
                chain=chain,
            )
            wallet_stored = self._knowledge.upsert_entity(wallet_ent)
            wallet_id = str(wallet_stored.id)
            self._knowledge.link_relation(
                case_stored.id,
                wallet_stored.id,
                "INVESTIGATES",
                tenant_id=tenant,
                confidence=0.9,
            )
            self._neo4j.project_entity(wallet_stored, case_ref=case_ref)
        return {
            "case_entity_id": str(case_stored.id),
            "wallet_entity_id": wallet_id,
            "investigation_id": str(investigation_id),
        }
