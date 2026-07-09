"""RFC-0005 Investigation Platform service — workspace, evidence, timeline, explain."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.evidence_center import content_hash_from_finding
from flowsint_crypto_compliance.platform.v2.gateway import case_timeline
from flowsint_crypto_compliance.platform.v2.investigation_platform.types import (
    EvidenceRecord,
    EvidenceStatus,
    InvestigationWorkspaceView,
    ReportKind,
    WorkspacePanel,
)
from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace
from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service
from flowsint_crypto_compliance.services.case_workflow import RFC_0005_LIFECYCLE, workflow_payload


def default_tenant_id() -> uuid.UUID:
    return uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


class InvestigationPlatformService:
    """Unified investigation-first operations layer (RFC-0005)."""

    def __init__(self) -> None:
        self._kg = get_knowledge_graph_service()
        self._workspace = InvestigationWorkspace(knowledge=self._kg.store)

    def get_workspace(self, case_ref: str, *, case: Any | None = None) -> dict[str, Any]:
        """Analyst workspace — all tools in investigation context."""
        workflow: dict[str, Any] = {}
        compliance_case_id = None
        investigation_id = None
        if case is not None:
            workflow = workflow_payload(case)
            workflow["lifecycle_ru"] = RFC_0005_LIFECYCLE.get(
                workflow.get("workflow_status", "new"), {}
            )
            compliance_case_id = getattr(case, "id", None)
            investigation_id = getattr(case, "investigation_id", None)

        bridge = self._workspace.open_case(
            case_ref=case_ref,
            investigation_id=investigation_id,
            compliance_case_id=compliance_case_id,
            actor="investigation_platform",
        )
        evidence = self.list_evidence(case_ref=case_ref, case_id=compliance_case_id)
        timeline = self.get_timeline(case_ref=case_ref, investigation_id=investigation_id)

        view = InvestigationWorkspaceView(
            case_ref=case_ref,
            compliance_case_id=compliance_case_id,
            investigation_id=investigation_id,
            entity_id=uuid.UUID(bridge["entity_id"]) if bridge.get("entity_id") else None,
            workflow=workflow,
            panels=[p.value for p in WorkspacePanel],
            evidence_count=len(evidence.get("items") or []),
            timeline_count=timeline.get("count") or 0,
            collaboration=self._collaboration_stub(case_ref, case),
        )
        return {
            **view.model_dump(mode="json"),
            "reports_available": [r.value for r in ReportKind],
            "report_api_base": f"/api/compliance/cases/{compliance_case_id}" if compliance_case_id else None,
        }

    def list_evidence(
        self,
        *,
        case_ref: str | None = None,
        case_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        tid = tenant_id or default_tenant_id()
        exported = self._kg.export_evidence_base(tid, case_ref=case_ref, case_id=case_id)
        items: list[dict[str, Any]] = []
        for row in exported.get("evidence") or []:
            payload = row.get("payload") or {}
            status_raw = payload.get("status") or EvidenceStatus.REGISTERED.value
            trust_raw = row.get("trust_level")
            if trust_raw is None and isinstance(row.get("trust"), dict):
                trust_raw = row["trust"].get("composite") or row["trust"].get("information_credibility")
            items.append(
                EvidenceRecord(
                    id=uuid.UUID(str(row["id"])),
                    source_type=str(row.get("source_type") or "unknown"),
                    content_hash=str(row.get("content_hash") or ""),
                    discovered_at=datetime.fromisoformat(str(row.get("discovered_at")).replace("Z", "+00:00"))
                    if row.get("discovered_at")
                    else datetime.now(timezone.utc),
                    acquisition_method=str(row.get("acquisition_method") or "automated_collection"),
                    author=str(payload.get("author") or row.get("actor") or "system"),
                    trust_level=float(trust_raw or 0.5),
                    status=EvidenceStatus(status_raw) if status_raw in EvidenceStatus._value2member_map_ else EvidenceStatus.REGISTERED,
                    entity_id=uuid.UUID(str(row["entity_id"])) if row.get("entity_id") else None,
                    case_id=uuid.UUID(str(row["case_id"])) if row.get("case_id") else None,
                    payload=payload,
                    status_history=list(payload.get("status_history") or []),
                ).model_dump(mode="json")
            )
        return {"case_ref": case_ref, "count": len(items), "items": items, "delete_forbidden": True}

    def register_evidence(
        self,
        *,
        case_ref: str,
        source_type: str,
        entity_type: str,
        entity_value: str,
        actor: str = "analyst",
        acquisition_method: str = "manual_upload",
        payload: dict[str, Any] | None = None,
        case_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Register evidence — RFC-0005 Ch.3; deletion forbidden."""
        from flowsint_crypto_compliance.platform.v2.canonical import Evidence, TrustLevel

        tid = tenant_id or default_tenant_id()
        content_hash = content_hash_from_finding(
            entity_type=entity_type,
            entity_value=entity_value,
            source_type=source_type,
            payload=payload,
        )
        now = datetime.now(timezone.utc)
        full_payload = {
            **(payload or {}),
            "entity_type": entity_type,
            "entity_value": entity_value,
            "case_ref": case_ref,
            "author": actor,
            "status": EvidenceStatus.REGISTERED.value,
            "status_history": [
                {"status": EvidenceStatus.REGISTERED.value, "at": now.isoformat(), "actor": actor}
            ],
        }
        evidence = Evidence(
            tenant_id=tid,
            case_id=case_id,
            source_type=source_type,
            content_hash=content_hash,
            discovered_at=now,
            acquisition_method=acquisition_method,
            digital_signature=content_hash,
            trust=TrustLevel(source_reliability=0.7, information_credibility=0.6),
            payload=full_payload,
        )
        stored = self._kg.store_evidence(evidence)
        return {"ok": True, "evidence_id": str(stored.id), "content_hash": content_hash, "status": EvidenceStatus.REGISTERED.value}

    def update_evidence_status(
        self,
        evidence_id: uuid.UUID,
        *,
        new_status: str,
        actor: str = "analyst",
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Status change only — full history preserved (RFC-0005 Ch.3)."""
        if new_status not in EvidenceStatus._value2member_map_:
            return {"ok": False, "error": f"Недопустимый статус: {new_status}"}
        ev = self._kg.get_evidence(evidence_id)
        if not ev:
            return {"ok": False, "error": "Доказательство не найдено"}
        now = datetime.now(timezone.utc)
        payload = dict(ev.payload or {})
        history = list(payload.get("status_history") or [])
        history.append({
            "status": new_status,
            "at": now.isoformat(),
            "actor": actor,
            "reason": reason,
            "previous": payload.get("status"),
        })
        payload["status"] = new_status
        payload["status_history"] = history
        from flowsint_crypto_compliance.platform.v2.canonical import Evidence

        updated = ev.model_copy(update={"payload": payload})
        stored = self._kg.store_evidence(updated)
        return {"ok": True, "evidence_id": str(stored.id), "status": new_status, "history_len": len(history)}

    def get_timeline(
        self,
        *,
        case_ref: str,
        investigation_id: uuid.UUID | None = None,
        at: datetime | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Merged timeline — platform events + optional temporal replay filter."""
        base = case_timeline(case_ref, limit=limit)
        events = list(base.get("events") or [])
        if investigation_id:
            events = [
                e for e in events
                if not e.get("investigation_id") or e.get("investigation_id") == str(investigation_id)
            ]
        if at is not None:
            at_utc = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
            filtered = []
            for e in events:
                raw = e.get("occurred_at")
                if not raw:
                    continue
                try:
                    ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                    if ts <= at_utc:
                        filtered.append(e)
                except ValueError:
                    continue
            events = filtered
        return {
            "case_ref": case_ref,
            "investigation_id": str(investigation_id) if investigation_id else None,
            "replay_at": at.isoformat() if at else None,
            "events": events,
            "count": len(events),
            "sources": ["finskalp_platform_events", "fusion", "intelligence", "audit"],
        }

    def explain_object(self, case_ref: str, entity_id: uuid.UUID) -> dict[str, Any]:
        """Explainable investigation — RFC-0005 Ch.6."""
        entity = self._kg.get_entity(entity_id)
        if entity is None:
            return {"ok": False, "error": "Сущность не найдена"}
        entity_data = entity.model_dump(mode="json")
        history = self._kg.get_entity_history(entity_id)
        neighbors = self._kg.get_neighbors(entity_id)
        related_entities = [n.get("entity") for n in neighbors if n.get("entity")]
        return {
            "ok": True,
            "case_ref": case_ref,
            "entity": entity_data,
            "provenance": {
                "sources": entity_data.get("sources") or [],
                "first_seen": entity_data.get("created_at"),
                "version": entity_data.get("version"),
            },
            "history": history,
            "related_evidence": [],
            "risk_chain": [],
            "rules_applied": (entity_data.get("explain") or {}).get("rules_fired") or [],
            "related_entities": related_entities,
        }

    def _collaboration_stub(self, case_ref: str, case: Any | None) -> dict[str, Any]:
        return {
            "case_ref": case_ref,
            "assignee_id": str(case.assignee_id) if case and getattr(case, "assignee_id", None) else None,
            "owner_id": str(case.owner_id) if case and getattr(case, "owner_id", None) else None,
            "comments_enabled": True,
            "tasks_enabled": True,
            "audit_replay": True,
        }


_service: InvestigationPlatformService | None = None


def get_investigation_platform_service() -> InvestigationPlatformService:
    global _service
    if _service is None:
        _service = InvestigationPlatformService()
    return _service
