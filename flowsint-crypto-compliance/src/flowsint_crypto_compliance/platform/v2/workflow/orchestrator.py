"""RFC-0011 — workflow orchestrator (event-driven interaction logic)."""

from __future__ import annotations

import os
import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace
from flowsint_crypto_compliance.platform.v2.workflow.manifest import INVESTIGATION_LIFECYCLE
from flowsint_crypto_compliance.platform.v2.workflow.recommendations import build_recommendations
from flowsint_crypto_compliance.services.case_workflow import WORKFLOW_STATUSES

_service: "WorkflowOrchestrator | None" = None

_STAGE_TO_PIPELINE: dict[str, list[str]] = {
    "case_creation": ["case_creation"],
    "object_definition": ["object_definition"],
    "auto_collection": ["source", "event"],
    "normalization": ["normalize"],
    "fusion": ["fusion"],
    "knowledge_graph": ["knowledge_graph", "entity_resolution"],
    "link_search": ["analytics"],
    "hypothesis_building": ["analytics"],
    "hypothesis_validation": ["analytics"],
    "risk_assessment": ["analytics"],
    "evidence_formation": ["evidence"],
    "report": ["report"],
    "archiving": ["archiving"],
}


def default_tenant_id() -> uuid.UUID:
    return uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


class WorkflowOrchestrator:
    """Drives Observe→Investigate→Correlate→Decide and mandatory lifecycle stages."""

    def get_first_login_briefing(self) -> dict[str, Any]:
        return {
            "ok": True,
            "checks": [
                {"id": "new_events", "label_ru": "Проверка новых событий", "status": "ready"},
                {"id": "recent_cases", "label_ru": "Последние расследования", "status": "ready"},
                {"id": "priorities", "label_ru": "Список приоритетов", "status": "ready"},
                {"id": "recommendations", "label_ru": "Рекомендации ИИ", "status": "ready"},
                {"id": "risk_changes", "label_ru": "Изменения риска", "status": "ready"},
                {"id": "new_evidence", "label_ru": "Новые доказательства", "status": "ready"},
            ],
            "message_ru": "Аналитик сразу видит, где требуется внимание",
        }

    def _resolve_stage_progress(
        self,
        *,
        case_ref: str,
        workflow_status: str,
        stages_completed: list[str],
    ) -> list[dict[str, Any]]:
        completed_ids: set[str] = set()
        for stage_id, markers in _STAGE_TO_PIPELINE.items():
            if any(m in stages_completed for m in markers):
                completed_ids.add(stage_id)
        if case_ref:
            completed_ids.add("case_creation")
        status_index = WORKFLOW_STATUSES.index(workflow_status) if workflow_status in WORKFLOW_STATUSES else 0
        if status_index >= 2:
            completed_ids.update({"auto_collection", "normalization", "fusion", "knowledge_graph"})
        if status_index >= 3:
            completed_ids.update({"link_search", "hypothesis_building", "risk_assessment", "evidence_formation"})
        if workflow_status in ("filed", "archived"):
            completed_ids.add("report")
        if workflow_status == "archived":
            completed_ids.add("archiving")

        out: list[dict[str, Any]] = []
        for stage in INVESTIGATION_LIFECYCLE:
            sid = stage["id"]
            out.append(
                {
                    **stage,
                    "completed": sid in completed_ids,
                    "current": sid not in completed_ids and (not out or out[-1]["completed"]),
                }
            )
        return out

    def get_workflow_state(self, *, case_ref: str | None = None, tenant_id: uuid.UUID | None = None) -> dict[str, Any]:
        if not case_ref:
            return {"ok": False, "message_ru": "Укажите case_ref"}

        from flowsint_crypto_compliance.platform.v2.investigation_platform import get_investigation_platform_service

        tid = tenant_id or default_tenant_id()
        platform = get_investigation_platform_service()
        ws = platform.get_workspace(case_ref=case_ref)
        workflow = ws.get("workflow") or {}
        workflow_status = str(workflow.get("workflow_status") or "new")
        evidence = platform.list_evidence(case_ref=case_ref, tenant_id=tid)
        evidence_count = len(evidence.get("items") or [])
        timeline = platform.get_timeline(case_ref=case_ref)
        stages_completed = [str(e.get("event_type") or "") for e in (timeline.get("events") or [])]

        risk_score = None
        intel = ws.get("intelligence") or {}
        if isinstance(intel, dict):
            scores = intel.get("scores") or {}
            if scores:
                risk_score = max(float(v) for v in scores.values() if isinstance(v, (int, float)))

        lifecycle = self._resolve_stage_progress(
            case_ref=case_ref,
            workflow_status=workflow_status,
            stages_completed=stages_completed,
        )
        current = next((s for s in lifecycle if s.get("current")), lifecycle[0] if lifecycle else None)
        oicd_phase = "observe"
        if current:
            cid = current["id"]
            if cid in ("link_search", "hypothesis_building", "hypothesis_validation"):
                oicd_phase = "correlate"
            elif cid in ("risk_assessment", "report", "archiving"):
                oicd_phase = "decide"
            elif cid not in ("case_creation", "object_definition"):
                oicd_phase = "investigate"

        return {
            "ok": True,
            "case_ref": case_ref,
            "workflow_status": workflow_status,
            "oicd_phase": oicd_phase,
            "lifecycle": lifecycle,
            "counts": {
                "evidence": evidence_count,
                "timeline_events": len(timeline.get("events") or []),
                "entities": len(ws.get("entities") or []),
            },
            "risk_score": risk_score,
            "background_tasks_active": True,
        }

    def get_recommendations(self, *, case_ref: str, tenant_id: uuid.UUID | None = None) -> dict[str, Any]:
        state = self.get_workflow_state(case_ref=case_ref, tenant_id=tenant_id)
        if not state.get("ok"):
            return state
        current = next((s for s in state["lifecycle"] if s.get("current")), None)
        stage_id = current["id"] if current else "case_creation"
        recs = build_recommendations(
            case_ref=case_ref,
            workflow_stage=stage_id,
            risk_score=state.get("risk_score"),
            entity_count=state["counts"].get("entities", 0),
            evidence_count=state["counts"].get("evidence", 0),
        )
        return {"ok": True, "case_ref": case_ref, "recommendations": recs, "count": len(recs)}

    async def start_workflow(
        self,
        *,
        case_ref: str,
        seed_type: str,
        seed_value: str,
        chain: str = "tron",
        tenant_id: uuid.UUID | None = None,
        investigation_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Ch.4 — auto-start collectors after seed confirmation."""
        tid = tenant_id or default_tenant_id()
        inv_id = investigation_id or uuid.uuid4()

        ws = InvestigationWorkspace()
        opened = ws.open_case(case_ref=case_ref, tenant_id=tid, investigation_id=inv_id)

        bus = get_platform_event_bus()
        bus.publish(
            PlatformEvent(
                event_type=EventType.CASE_OPENED,
                source="workflow.start",
                tenant_id=tid,
                investigation_id=inv_id,
                payload={"case_ref": case_ref, "seed_type": seed_type, "seed_value": seed_value},
            )
        )

        pipeline_result: dict[str, Any] = {"ok": True, "stages_completed": []}
        if seed_type == "wallet" and seed_value:
            from flowsint_crypto_compliance.platform.v2.pipeline_chain import get_pipeline_chain_orchestrator

            orch = get_pipeline_chain_orchestrator()
            pr = await orch.run_investigation_chain(
                tenant_id=tid,
                investigation_id=inv_id,
                case_ref=case_ref,
                address=seed_value,
                chain=chain,
                screening={"risk_score": 50},
                mentions=[],
            )
            pipeline_result = pr.to_dict()

        bus.publish(
            PlatformEvent(
                event_type=EventType.RECOMMENDATION_CREATED,
                source="workflow.start",
                tenant_id=tid,
                investigation_id=inv_id,
                payload={"case_ref": case_ref, "ui_event": "RecommendationCreated"},
            )
        )

        return {
            "ok": True,
            "case_ref": case_ref,
            "investigation_id": str(inv_id),
            "entity_id": opened.get("entity_id"),
            "seed_type": seed_type,
            "seed_value": seed_value,
            "auto_collectors_started": True,
            "pipeline": pipeline_result,
            "message_ru": "Автоматически запущены collectors, fusion и entity resolution",
        }


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    global _service
    if _service is None:
        _service = WorkflowOrchestrator()
    return _service
