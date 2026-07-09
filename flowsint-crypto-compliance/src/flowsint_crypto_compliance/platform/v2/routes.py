"""Shared Platform v2 FastAPI routes — RFC-0002 M3 BFF (flowsint-api + demo stand)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from flowsint_crypto_compliance.platform.v2.gateway import (
    architecture_manifest,
    case_timeline,
    compare_entity_versions,
    create_graph_snapshot,
    emit_scalpel_collect_event,
    export_evidence_base,
    get_entity,
    get_entity_history,
    get_entity_neighbors,
    get_graph_at,
    get_intelligence_manifest,
    get_intelligence_engine_manifest,
    get_connectors_manifest,
    get_design_system_manifest,
    get_rbac_manifest,
    get_rbac_effective,
    get_workflow_manifest,
    get_workflow_state,
    get_workflow_recommendations,
    get_workflow_first_login,
    start_workflow_investigation,
    get_workflow_recovery,
    save_workflow_recovery,
    get_blockchain_intelligence_manifest,
    analyze_blockchain_address,
    run_blockchain_sync,
    get_blockchain_sync_status,
    get_analyst_workspace_manifest,
    get_analyst_workspace_state,
    analyst_workspace_search,
    analyst_workspace_add_comment,
    analyst_workspace_collaboration_activity,
    analyst_workspace_get_personalization,
    analyst_workspace_save_personalization,
    connector_health,
    run_connector_collect,
    get_icf_manifest,
    run_icf_collect,
    get_icf_scheduler_status,
    schedule_icf_job,
    get_icf_monitoring,
    get_investigation_manifest,
    get_investigation_workspace,
    get_operations_manifest,
    explain_investigation_entity,
    list_case_evidence,
    register_case_evidence,
    update_evidence_status,
    get_knowledge_model,
    get_pipeline_chain_manifest,
    get_relation_evidence,
    get_relation_history,
    ingest_record,
    list_plugins,
    run_intelligence,
    run_intelligence_engine,
)


class PlatformV2InvestigateRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=128)
    chain: str | None = None
    scenario_id: str | None = None
    depth: int = Field(2, ge=1, le=3)
    osint_depth: int = Field(2, ge=1, le=3)
    limit: int = Field(50, ge=1, le=100)
    collectors: list[str] | None = None


class PlatformV2ScalpelCollectRequest(BaseModel):
    address: str
    chain: str = "tron"
    depth: int = Field(2, ge=1, le=3)
    collectors: list[str] | None = None
    case_ref: str | None = None


class PlatformV2IngestRequest(BaseModel):
    source_type: str = Field(..., min_length=1, max_length=64)
    entity_type: str = Field(..., min_length=1, max_length=32)
    entity_value: str = Field(..., min_length=1, max_length=512)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    payload: dict[str, Any] | None = None


class PlatformV2IntelligenceAnalyzeRequest(BaseModel):
    address: str | None = None
    chain: str | None = None
    case_ref: str | None = None
    entity_id: uuid.UUID | None = None
    investigation_id: uuid.UUID | None = None
    screening: dict[str, Any] | None = None
    attribution: dict[str, Any] | None = None
    mentions: list[dict[str, Any]] | None = None
    publish: bool = True


class PlatformV2EvidenceRegisterRequest(BaseModel):
    source_type: str = Field(..., min_length=1, max_length=64)
    entity_type: str = Field(..., min_length=1, max_length=32)
    entity_value: str = Field(..., min_length=1, max_length=512)
    acquisition_method: str = "manual_upload"
    payload: dict[str, Any] | None = None


class PlatformV2EvidenceStatusRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    reason: str | None = None


class PlatformV2ConnectorCollectRequest(BaseModel):
    query: dict[str, Any] | None = None
    case_ref: str | None = None
    publish: bool = True


class PlatformV2ICFCollectRequest(BaseModel):
    connector_id: str = Field(..., min_length=1, max_length=128)
    query: dict[str, Any] | None = None
    case_ref: str | None = None
    publish: bool = True


class PlatformV2ICFScheduleRequest(BaseModel):
    connector_id: str = Field(..., min_length=1, max_length=128)
    query: dict[str, Any] | None = None
    case_ref: str | None = None
    interval_seconds: int = Field(300, ge=60, le=86_400)


class PlatformV2CollaborationCommentRequest(BaseModel):
    case_ref: str
    text: str = Field(..., min_length=1, max_length=4000)
    author: str = "analyst"


class PlatformV2PersonalizationRequest(BaseModel):
    preferences: dict[str, Any] = Field(default_factory=dict)


class PlatformV2WorkflowStartRequest(BaseModel):
    case_ref: str = Field(..., min_length=1, max_length=128)
    seed_type: str = Field(..., pattern="^(wallet|organization|person|document|transaction|group)$")
    seed_value: str = Field(..., min_length=1, max_length=512)
    chain: str = "tron"
    investigation_id: uuid.UUID | None = None


class PlatformV2WorkflowRecoveryRequest(BaseModel):
    state: dict[str, Any] = Field(default_factory=dict)


class PlatformV2BlockchainAnalyzeRequest(BaseModel):
    address: str = Field(..., min_length=4, max_length=128)
    chain: str = Field(..., min_length=2, max_length=32)
    case_ref: str | None = None
    publish: bool = True


class PlatformV2BlockchainSyncRequest(BaseModel):
    chains: list[str] | None = None
    simulate: bool | None = None


class PlatformV2AttributionBody(BaseModel):
    chain: str
    address: str
    label: str
    category: str = "manual"
    analyst_id: str = "analyst"
    case_ref: str | None = None


async def _noop_user():
    return None


def _latency_response(body: dict[str, Any]) -> JSONResponse:
    headers: dict[str, str] = {}
    if "latency_ms" in body:
        headers["X-Finskalp-Latency-Ms"] = str(body["latency_ms"])
    return JSONResponse(content=body, headers=headers)


def create_platform_v2_router(
    *,
    get_current_user: Callable | None = None,
    require_case_read: Callable | None = None,
    require_batch_screen: Callable | None = None,
    require_case_create: Callable | None = None,
    get_db: Callable | None = None,
    demo_api_token_guard: Callable | None = None,
) -> APIRouter:
    """Build router; pass auth deps for flowsint-api, omit for demo stand."""
    router = APIRouter()
    dep_user = Depends(get_current_user or _noop_user)
    dep_case_read = Depends(require_case_read or _noop_user)
    dep_batch = Depends(require_batch_screen or _noop_user)
    dep_case_create = Depends(require_case_create or _noop_user)
    dep_db = Depends(get_db) if get_db else None

    @router.get("/architecture")
    async def get_architecture(_user=dep_user):
        return architecture_manifest()

    @router.get("/knowledge-model")
    async def get_knowledge_model_manifest(_user=dep_user):
        return get_knowledge_model()

    @router.get("/entities/{entity_id}")
    async def get_entity_by_id(entity_id: uuid.UUID, _user=dep_case_read):
        result = get_entity(entity_id)
        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @router.get("/entities/{entity_id}/neighbors")
    async def get_entity_neighbors_endpoint(
        entity_id: uuid.UUID,
        direction: str = Query("both", pattern="^(both|in|out)$"),
        _user=dep_case_read,
    ):
        result = get_entity_neighbors(entity_id, direction=direction)
        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @router.get("/entities/{entity_id}/history")
    async def get_entity_history_endpoint(entity_id: uuid.UUID, _user=dep_case_read):
        return get_entity_history(entity_id)

    @router.get("/entities/{entity_id}/compare")
    async def compare_entity_versions_endpoint(
        entity_id: uuid.UUID,
        version_a: int = Query(..., ge=1),
        version_b: int = Query(..., ge=1),
        _user=dep_case_read,
    ):
        result = compare_entity_versions(entity_id, version_a, version_b)
        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @router.get("/relations/{relation_id}/history")
    async def get_relation_history_endpoint(relation_id: uuid.UUID, _user=dep_case_read):
        return get_relation_history(relation_id)

    @router.get("/graph/at")
    async def get_graph_snapshot(
        as_of: datetime = Query(..., description="ISO8601 timestamp"),
        tenant_id: uuid.UUID | None = None,
        _user=dep_case_read,
    ):
        tid = tenant_id or uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        return get_graph_at(tid, as_of)

    @router.post("/graph/snapshot")
    async def post_graph_snapshot(
        tenant_id: uuid.UUID | None = None,
        current_user=dep_batch,
    ):
        tid = tenant_id or uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        actor = str(getattr(current_user, "id", "demo")) if current_user else "demo"
        return create_graph_snapshot(tid, actor=actor)

    @router.get("/evidence/export")
    async def export_evidence_endpoint(
        tenant_id: uuid.UUID | None = None,
        case_ref: str | None = None,
        case_id: uuid.UUID | None = None,
        format: str = Query("json", pattern="^json$"),
        _user=dep_case_read,
    ):
        tid = tenant_id or uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        return export_evidence_base(tid, case_ref=case_ref, case_id=case_id, fmt=format)

    @router.get("/pipeline-chain")
    async def get_pipeline_chain(_user=dep_user):
        return get_pipeline_chain_manifest()

    @router.get("/connectors/manifest")
    async def connectors_manifest(_user=dep_user):
        return get_connectors_manifest()

    @router.get("/design-system/manifest")
    async def design_system_manifest_route(_user=dep_user):
        return get_design_system_manifest()

    @router.get("/rbac/manifest")
    async def rbac_manifest_route(_user=dep_user):
        return get_rbac_manifest()

    @router.get("/rbac/effective")
    async def rbac_effective_route(
        investigation_id: uuid.UUID | None = None,
        current_user=dep_user,
        db=dep_db,
    ):
        if get_db is None or current_user is None or not getattr(current_user, "id", None) or db is None:
            return {"ok": False, "message_ru": "Требуется авторизация и БД"}
        return get_rbac_effective(db, current_user.id, investigation_id=investigation_id)

    @router.get("/workflow/manifest")
    async def workflow_manifest_route(_user=dep_user):
        return get_workflow_manifest()

    @router.get("/workflow/first-login")
    async def workflow_first_login_route(_user=dep_user):
        return get_workflow_first_login()

    @router.get("/workflow/state")
    async def workflow_state_route(case_ref: str | None = None, _user=dep_case_read):
        return get_workflow_state(case_ref=case_ref)

    @router.get("/workflow/recommendations")
    async def workflow_recommendations_route(case_ref: str, _user=dep_case_read):
        return get_workflow_recommendations(case_ref=case_ref)

    @router.post("/workflow/start")
    async def workflow_start_route(body: PlatformV2WorkflowStartRequest, _user=dep_case_create):
        return await start_workflow_investigation(
            case_ref=body.case_ref,
            seed_type=body.seed_type,
            seed_value=body.seed_value,
            chain=body.chain,
            investigation_id=body.investigation_id,
        )

    @router.get("/workflow/recovery")
    async def workflow_recovery_get(current_user=dep_user):
        user_id = str(getattr(current_user, "id", "default")) if current_user else "default"
        return get_workflow_recovery(user_id)

    @router.put("/workflow/recovery")
    async def workflow_recovery_put(body: PlatformV2WorkflowRecoveryRequest, current_user=dep_user):
        user_id = str(getattr(current_user, "id", "default")) if current_user else "default"
        return save_workflow_recovery(user_id, body.state)

    @router.get("/blockchain-intelligence/manifest")
    async def blockchain_intelligence_manifest_route(_user=dep_user):
        return get_blockchain_intelligence_manifest()

    @router.post("/blockchain-intelligence/analyze")
    async def blockchain_intelligence_analyze(body: PlatformV2BlockchainAnalyzeRequest, _user=dep_case_read):
        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        return await analyze_blockchain_address(
            address=body.address,
            chain=body.chain,
            case_ref=body.case_ref,
            tenant_id=uuid.UUID(tenant_raw),
            publish=body.publish,
        )

    @router.get("/blockchain-intelligence/sync/status")
    async def blockchain_sync_status(_user=dep_user):
        return get_blockchain_sync_status()

    @router.post("/blockchain-intelligence/sync/run")
    async def blockchain_sync_run(body: PlatformV2BlockchainSyncRequest, _user=dep_batch):
        return await run_blockchain_sync(body.chains, simulate=body.simulate)

    @router.get("/analyst-workspace/manifest")
    async def analyst_workspace_manifest_route(_user=dep_user):
        from flowsint_crypto_compliance.platform.v2.analyst_workspace.timing import with_latency_ms

        body = with_latency_ms(lambda: {**get_analyst_workspace_manifest(), "ok": True})
        return _latency_response(body)

    @router.get("/analyst-workspace/state")
    async def analyst_workspace_state(
        case_ref: str | None = None,
        investigation_id: uuid.UUID | None = None,
        db=dep_db,
        current_user=dep_case_read,
    ):
        case = None
        if db is not None and case_ref:
            from flowsint_crypto_compliance.services.compliance_service import ComplianceService

            case = ComplianceService(db).get_case_by_ref(case_ref)
        user_id = str(getattr(current_user, "id", "default")) if current_user else "default"
        body = get_analyst_workspace_state(
            case_ref=case_ref,
            investigation_id=investigation_id,
            case=case,
            user_id=user_id,
        )
        return _latency_response(body)

    @router.get("/analyst-workspace/search")
    async def analyst_workspace_search_route(
        q: str = Query(..., min_length=1),
        case_ref: str | None = None,
        tenant_id: uuid.UUID | None = None,
        _user=dep_case_read,
    ):
        tid = tenant_id or uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        body = analyst_workspace_search(q, tenant_id=tid, case_ref=case_ref)
        return _latency_response(body)

    @router.post("/analyst-workspace/collaboration/comment")
    async def analyst_workspace_comment(
        body: PlatformV2CollaborationCommentRequest,
        current_user=dep_case_read,
    ):
        author = str(getattr(current_user, "id", body.author)) if current_user else body.author
        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        result = analyst_workspace_add_comment(
            case_ref=body.case_ref,
            text=body.text,
            author=author,
            tenant_id=tenant_raw,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message_ru", "Ошибка"))
        return _latency_response(result)

    @router.get("/analyst-workspace/collaboration/activity")
    async def analyst_workspace_activity(case_ref: str, _user=dep_case_read):
        body = analyst_workspace_collaboration_activity(case_ref)
        return _latency_response(body)

    @router.get("/analyst-workspace/personalization")
    async def analyst_workspace_personalization_get(current_user=dep_user):
        user_id = str(getattr(current_user, "id", "default")) if current_user else "default"
        body = analyst_workspace_get_personalization(user_id)
        return _latency_response(body)

    @router.put("/analyst-workspace/personalization")
    async def analyst_workspace_personalization_put(
        body: PlatformV2PersonalizationRequest,
        current_user=dep_user,
    ):
        user_id = str(getattr(current_user, "id", "default")) if current_user else "default"
        result = analyst_workspace_save_personalization(user_id, body.preferences)
        return _latency_response(result)

    @router.post("/connectors/{connector_id}/health")
    async def connectors_health(connector_id: str, _user=dep_user):
        return await connector_health(connector_id)

    @router.post("/connectors/{connector_id}/collect")
    async def connectors_collect(
        connector_id: str,
        body: PlatformV2ConnectorCollectRequest,
        _user=dep_batch,
    ):
        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        return await run_connector_collect(
            connector_id,
            tenant_id=uuid.UUID(tenant_raw),
            query=body.query,
            case_ref=body.case_ref,
            publish=body.publish,
        )

    @router.get("/icf/manifest")
    async def icf_manifest_route(_user=dep_user):
        return get_icf_manifest()

    @router.post("/icf/collect")
    async def icf_collect(body: PlatformV2ICFCollectRequest, _user=dep_batch):
        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        return await run_icf_collect(
            connector_id=body.connector_id,
            tenant_id=uuid.UUID(tenant_raw),
            query=body.query,
            case_ref=body.case_ref,
            publish=body.publish,
        )

    @router.get("/icf/scheduler/status")
    async def icf_scheduler_status(_user=dep_user):
        return get_icf_scheduler_status()

    @router.post("/icf/scheduler/schedule")
    async def icf_scheduler_schedule(body: PlatformV2ICFScheduleRequest, _user=dep_batch):
        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        return schedule_icf_job(
            connector_id=body.connector_id,
            query=body.query,
            case_ref=body.case_ref,
            tenant_id=tenant_raw,
            interval_seconds=body.interval_seconds,
        )

    @router.get("/icf/monitoring")
    async def icf_monitoring(connector_id: str | None = None, _user=dep_user):
        return get_icf_monitoring(connector_id)

    @router.get("/intelligence-engine/manifest")
    async def intelligence_engine_manifest(_user=dep_user):
        return get_intelligence_engine_manifest()

    @router.post("/intelligence-engine/run")
    async def intelligence_engine_run(body: PlatformV2IntelligenceAnalyzeRequest, _user=dep_batch):
        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        return run_intelligence_engine(
            tenant_id=uuid.UUID(tenant_raw),
            address=body.address,
            chain=body.chain,
            case_ref=body.case_ref,
            investigation_id=body.investigation_id,
            entity_id=body.entity_id,
            screening=body.screening,
            attribution=body.attribution,
            mentions=body.mentions,
            publish=body.publish,
        )

    @router.get("/intelligence/manifest")
    async def get_intelligence_platform_manifest(_user=dep_user):
        """RFC-0004 — каталог аналитических движков."""
        return get_intelligence_manifest()

    @router.post("/intelligence/analyze")
    async def analyze_intelligence(body: PlatformV2IntelligenceAnalyzeRequest, _user=dep_batch):
        """RFC-0004 — запуск всех движков поверх Knowledge Graph."""
        tid = uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
        return run_intelligence(
            tenant_id=tid,
            address=body.address,
            chain=body.chain,
            case_ref=body.case_ref,
            investigation_id=body.investigation_id,
            entity_id=body.entity_id,
            screening=body.screening,
            attribution=body.attribution,
            mentions=body.mentions,
            publish=body.publish,
        )

    @router.get("/relations/{relation_id}/evidence")
    async def get_relation_evidence_endpoint(relation_id: uuid.UUID, _user=dep_case_read):
        return get_relation_evidence(relation_id)

    @router.post("/ingest")
    async def ingest_via_mandatory_path(body: PlatformV2IngestRequest, current_user=dep_batch):
        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        actor = str(getattr(current_user, "id", "demo")) if current_user else "demo"
        result = ingest_record(
            tenant_id=uuid.UUID(tenant_raw),
            source_type=body.source_type,
            entity_type=body.entity_type,
            entity_value=body.entity_value,
            payload=body.payload,
            actor=actor,
            confidence=body.confidence,
        )
        if not result["ok"]:
            raise HTTPException(status_code=422, detail=result.get("errors") or result.get("message"))
        return result

    @router.get("/plugins")
    async def get_plugins(_user=dep_user):
        return {"plugins": list_plugins()}

    @router.get("/investigation/manifest")
    async def investigation_manifest(_user=dep_user):
        return get_investigation_manifest()

    @router.get("/operations/manifest")
    async def operations_manifest_endpoint(_user=dep_user):
        return get_operations_manifest()

    @router.get("/investigations/{case_ref}/workspace")
    async def investigation_workspace(case_ref: str, db=dep_db, _user=dep_case_read):
        case = None
        if db is not None:
            from flowsint_crypto_compliance.services.compliance_service import ComplianceService

            case = ComplianceService(db).get_case_by_ref(case_ref)
        return get_investigation_workspace(case_ref, case=case)

    @router.get("/investigations/{case_ref}/evidence")
    async def investigation_evidence_list(case_ref: str, db=dep_db, _user=dep_case_read):
        case_id = None
        if db is not None:
            from flowsint_crypto_compliance.services.compliance_service import ComplianceService

            row = ComplianceService(db).get_case_by_ref(case_ref)
            case_id = row.id if row else None
        return list_case_evidence(case_ref=case_ref, case_id=case_id)

    @router.post("/investigations/{case_ref}/evidence")
    async def investigation_evidence_register(
        case_ref: str,
        body: PlatformV2EvidenceRegisterRequest,
        db=dep_db,
        current_user=dep_case_create,
    ):
        case_id = None
        actor = str(getattr(current_user, "id", "analyst")) if current_user else "analyst"
        if db is not None:
            from flowsint_crypto_compliance.services.compliance_service import ComplianceService

            row = ComplianceService(db).get_case_by_ref(case_ref)
            case_id = row.id if row else None
        result = register_case_evidence(
            case_ref=case_ref,
            source_type=body.source_type,
            entity_type=body.entity_type,
            entity_value=body.entity_value,
            actor=actor,
            acquisition_method=body.acquisition_method,
            payload=body.payload,
            case_id=case_id,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=422, detail=result.get("error"))
        return result

    @router.patch("/evidence/{evidence_id}/status")
    async def evidence_status_update(
        evidence_id: uuid.UUID,
        body: PlatformV2EvidenceStatusRequest,
        current_user=dep_case_create,
    ):
        actor = str(getattr(current_user, "id", "analyst")) if current_user else "analyst"
        result = update_evidence_status(
            evidence_id,
            new_status=body.status,
            actor=actor,
            reason=body.reason,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result

    @router.get("/investigations/{case_ref}/explain/{entity_id}")
    async def investigation_explain(case_ref: str, entity_id: uuid.UUID, _user=dep_case_read):
        result = explain_investigation_entity(case_ref, entity_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result

    @router.get("/cases/{case_ref}/timeline")
    async def get_case_timeline(case_ref: str, limit: int = 100, _user=dep_case_read):
        return case_timeline(case_ref, limit=limit)

    @router.post("/investigate")
    async def investigate_canonical(
        body: PlatformV2InvestigateRequest,
        request: Request,
        _user=dep_batch,
    ):
        from flowsint_types.fiat_crypto import Chain

        from flowsint_crypto_compliance.services.finskalp_investigator import (
            FinSkalpInvestigationRequest,
            FinSkalpInvestigator,
        )

        if demo_api_token_guard is not None:
            demo_api_token_guard(request)

        try:
            chain = Chain(body.chain.lower()) if body.chain else None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Неподдерживаемая сеть") from exc

        investigator = FinSkalpInvestigator()
        try:
            result = await investigator.investigate(
                FinSkalpInvestigationRequest(
                    address=body.address.strip(),
                    chain=chain,
                    scenario_id=body.scenario_id,
                    depth=body.depth,
                    osint_depth=body.osint_depth,
                    limit=body.limit,
                    collectors=body.collectors,
                ),
                correlation_id=request.headers.get("X-Correlation-ID"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result.to_dict()

    @router.post("/scalpel/collect")
    async def scalpel_collect_canonical(body: PlatformV2ScalpelCollectRequest, _user=dep_batch):
        from flowsint_types.fiat_crypto import Chain

        from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine

        try:
            chain = Chain(body.chain.lower())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Неподдерживаемая сеть") from exc

        engine = ScalpelEngine()
        try:
            result = await engine.collect(
                body.address.strip(),
                chain,
                depth=body.depth,
                collectors=body.collectors,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        payload = result.to_dict()
        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        mentions = (payload.get("extracted_entities") or {}).get("mentions") or payload.get("mentions") or []
        emit_scalpel_collect_event(
            case_ref=body.case_ref,
            tenant_id=uuid.UUID(tenant_raw),
            investigation_id=None,
            mentions=mentions if isinstance(mentions, list) else [],
        )
        return payload

    @router.post("/cases")
    async def open_case_canonical(
        case_ref: str,
        investigation_id: uuid.UUID | None = None,
        db=dep_db,
        current_user=dep_case_create,
    ):
        from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace
        from flowsint_crypto_compliance.services.compliance_service import ComplianceService

        if db is None:
            raise HTTPException(status_code=501, detail="Открытие дела через API требует подключения к БД")
        svc = ComplianceService(db)
        existing = svc.get_case_by_ref(case_ref)
        actor = str(getattr(current_user, "id", "demo")) if current_user else "demo"
        if not existing:
            owner_id = current_user.id if current_user and hasattr(current_user, "id") else uuid.UUID(
                "00000000-0000-0000-0000-000000000099"
            )
            existing = svc.create_case(
                case_ref=case_ref,
                owner_id=owner_id,
                investigation_id=investigation_id,
            )
        else:
            InvestigationWorkspace().bridge_compliance_case(existing, actor=actor)
        return {
            "case_ref": case_ref,
            "compliance_case_id": str(existing.id),
            "investigation_id": str(existing.investigation_id) if existing.investigation_id else None,
        }

    @router.post("/attribution/confirm")
    async def attribution_confirm(body: PlatformV2AttributionBody, request: Request):
        if demo_api_token_guard is not None:
            demo_api_token_guard(request)
        from flowsint_crypto_compliance.attribution.postgres_entity_store import analyst_confirm_label

        el = analyst_confirm_label(
            chain=body.chain,
            address=body.address,
            label=body.label,
            category=body.category,
            analyst_id=body.analyst_id,
        )
        return {"status": "confirmed", "label": el.label, "chain": el.chain, "address": el.address}

    @router.post("/attribution/reject")
    async def attribution_reject(body: PlatformV2AttributionBody, request: Request):
        if demo_api_token_guard is not None:
            demo_api_token_guard(request)
        from flowsint_crypto_compliance.attribution.postgres_entity_store import analyst_reject_label

        el = analyst_reject_label(
            chain=body.chain,
            address=body.address,
            label=body.label,
            category=body.category,
            analyst_id=body.analyst_id,
        )
        return {"status": "rejected", "label": el.label, "chain": el.chain, "address": el.address}

    return router
