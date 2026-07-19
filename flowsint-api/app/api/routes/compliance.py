from uuid import UUID

import asyncio
import json
import os

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from flowsint_core.core.celery import celery
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from flowsint_core.core.models import Profile
from flowsint_core.core.postgre_db import get_db
from flowsint_crypto_compliance.services.compliance_service import ComplianceService
from flowsint_crypto_compliance.services.graph_timestamps import enrich_serialized_graph
from flowsint_crypto_compliance.services.wallet_screening import (
    WalletScreeningRequest,
    WalletScreeningService,
)
from flowsint_crypto_compliance.storage.postgres_label_cache import PostgresLabelCache
from flowsint_types.fiat_crypto import Chain, ControlPurchaseEvent, LicensedPlatformEvent

from flowsint_crypto_compliance.demo.chain_data import get_demo_adapters
from flowsint_crypto_compliance.demo.demo_context import get_demo_chain_adapters, get_demo_label_cache
from flowsint_crypto_compliance.demo.runner import RegulatorDemoRunner
from flowsint_crypto_compliance.reporting.pdf_report import render_regulator_html, render_pdf_bytes
from flowsint_crypto_compliance.schemas.hub import validate_bank_feed_batch
from flowsint_crypto_compliance.services.demo_compliance_service import get_demo_compliance_service
from flowsint_crypto_compliance.services.fusion_sse import fusion_sse_events
from flowsint_crypto_compliance.reporting.excel_report import render_regulator_xlsx
from flowsint_crypto_compliance.ingestion.regulator_connector import RegulatorAPIConnector
from flowsint_crypto_compliance.ingestion.hub_stream import HubStreamConsumer
from flowsint_crypto_compliance.observability.metrics import (
    COMPLIANCE_FUSION_TOTAL,
    COMPLIANCE_REGISTRY_IMPORT_TOTAL,
    COMPLIANCE_WALLET_SCREEN_TOTAL,
    metrics_payload,
)
from flowsint_crypto_compliance.services.compliance_rbac import require_permission
from flowsint_crypto_compliance.storage.neo4j_exporter import EvidenceGraphNeo4jExporter

from app.api.deps import get_current_user
from app.api.schemas.compliance import (
    BankFeedBatchIn,
    ComplianceCaseCreate,
    ComplianceCaseRead,
    DemoScenarioRead,
    FuseCaseRequest,
    FusionAsyncResponse,
    FusionResultRead,
    FusionRunRead,
    GraphMergeRequest,
    GraphMergeResponse,
    LiveFusionRequest,
    LiveFusionAsyncResponse,
    ComplianceAuditLogRead,
    MaigretScanRequest,
    OCRExtractResponse,
    RegistryImportResult,
    RegulatorReportRead,
    ScalpelAsyncResponse,
    ScalpelCollectRequest,
    ScalpelTaskStatus,
    ScoringLabelCaseRequest,
    ScoringPredictRequest,
    LiveCollectRequest,
    SpiderFootScanRequest,
    WalletScreenRequest,
    WalletScreenResultRead,
)

router = APIRouter()

COMPLIANCE_DEMO_MODE = os.getenv("COMPLIANCE_DEMO_MODE", "").lower() in ("1", "true", "yes")


def _service(db: Session) -> ComplianceService:
    return ComplianceService(db)


def _demo_service():
    return get_demo_compliance_service()


@router.post("/wallets/screen", response_model=WalletScreenResultRead)
async def screen_wallet(
    payload: WalletScreenRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    try:
        chain = Chain(payload.chain.lower()) if payload.chain else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unsupported chain") from exc

    service = (
        WalletScreeningService(
            chain_adapters=get_demo_chain_adapters(),
            label_cache=get_demo_label_cache(),
        )
        if COMPLIANCE_DEMO_MODE
        else WalletScreeningService(label_cache=PostgresLabelCache(db))
    )
    try:
        result = await service.screen(
            WalletScreeningRequest(
                address=payload.address,
                chain=chain,
                depth=payload.depth,
                limit=payload.limit,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    COMPLIANCE_WALLET_SCREEN_TOTAL.labels(risk_level=result.risk_level.value).inc()
    screen_body = result.model_dump(mode="json")
    from flowsint_crypto_compliance.platform.v2.multi_dimensional_confidence import (
        build_confidence_dimensions,
    )
    from flowsint_crypto_compliance.reporting.forensic_enrichment import build_risk_score_breakdown

    dims = build_confidence_dimensions(screen_body)
    screen_body["confidence_dimensions"] = dims.model_dump()
    screen_body["explain"] = {
        "dimensions": dims.explain_ru,
        "risk_breakdown": build_risk_score_breakdown(
            screening=screen_body,
            attribution={},
            open_osint=None,
            pattern=None,
        ),
    }
    from flowsint_crypto_compliance.platform.v2.entity_base import entity_from_label

    attr = (screen_body.get("onchain_summary") or {}).get("attribution") or {}
    primary = attr.get("primary_label") or {}
    if primary.get("label") or primary.get("entity_name"):
        screen_body["entity"] = entity_from_label(
            chain=screen_body["chain"],
            address=screen_body["address"],
            label=str(primary.get("label") or primary.get("entity_name") or screen_body["address"]),
            category=primary.get("category"),
            confidence=float(primary.get("confidence") or screen_body.get("confidence") or 0.5),
            risk_score=float(screen_body.get("risk_score") or 0),
            sources=[str(primary.get("source") or "screening")],
        )
    if not COMPLIANCE_DEMO_MODE:
        _service(db).log_audit(
            actor_id=current_user.id,
            action="wallet_screened",
            payload={
                "address": payload.address,
                "chain": payload.chain,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level.value,
            },
        )
        db.commit()
    from flowsint_crypto_compliance.platform.v2.operator_events import (
        OperatorEventType,
        publish_operator_event,
    )

    publish_operator_event(
        OperatorEventType.RISK_RECALCULATED,
        payload={
            "address": screen_body["address"],
            "chain": screen_body["chain"],
            "score": screen_body["risk_score"],
            "risk_level": screen_body["risk_level"],
        },
        actor=str(current_user.id),
    )
    return WalletScreenResultRead(**screen_body)


@router.post(
    "/cases",
    response_model=ComplianceCaseRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_compliance_case(
    payload: ComplianceCaseCreate,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:create")),
):
    service = _service(db)
    if service.get_case_by_ref(payload.case_ref):
        raise HTTPException(status_code=409, detail="case_ref already exists")
    case = service.create_case(
        case_ref=payload.case_ref,
        owner_id=current_user.id,
        investigation_id=payload.investigation_id,
    )
    from flowsint_crypto_compliance.platform.v2.operator_events import (
        OperatorEventType,
        publish_operator_event,
    )

    publish_operator_event(
        OperatorEventType.INVESTIGATION_CREATED,
        payload={"case_ref": case.case_ref, "case_id": str(case.id)},
        investigation_id=case.investigation_id,
        actor=str(current_user.id),
    )
    return case


@router.get("/cases/{case_id}", response_model=ComplianceCaseRead)
async def get_compliance_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
):
    from app.api.routes.compliance_ops import _case_read_payload

    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_read_payload(db, case)


@router.post("/cases/{case_id}/bank-feeds", status_code=status.HTTP_202_ACCEPTED)
async def ingest_bank_feeds(
    case_id: UUID,
    payload: BankFeedBatchIn,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        count = service.ingest_bank_feed_batch(case_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ingested": count, "case_id": str(case_id)}


@router.post("/registry/import", response_model=RegistryImportResult)
async def import_registry_bulk(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("watchlist:manage")),
):
    """Импорт суверенного реестра риск-меток РФ/СНГ (перечень 115-ФЗ, внутренние списки)."""
    if not file.filename or not file.filename.endswith((".jsonl", ".ndjson", ".json")):
        raise HTTPException(
            status_code=400,
            detail="Ожидается .jsonl/.ndjson (одна запись реестра на строку)",
        )
    raw = (await file.read()).decode("utf-8")
    lines = raw.splitlines()
    service = _service(db)
    try:
        imported = service.import_registry_jsonl_lines(lines)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RegistryImportResult(imported=imported, total_in_db=service._cache.count())


@router.post("/registry/import/parquet", response_model=RegistryImportResult)
async def import_registry_parquet(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("watchlist:manage")),
):
    """Bulk import sovereign registry from Parquet (air-gap handoff)."""
    import tempfile
    from pathlib import Path

    if not file.filename or not file.filename.endswith(".parquet"):
        raise HTTPException(status_code=400, detail="Ожидается .parquet")
    if COMPLIANCE_DEMO_MODE:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp.write(await file.read())
            path = Path(tmp.name)
        try:
            imported = _demo_service().import_registry_parquet(path)
        finally:
            path.unlink(missing_ok=True)
        COMPLIANCE_REGISTRY_IMPORT_TOTAL.labels(format="parquet").inc(imported)
        return RegistryImportResult(imported=imported, total_in_db=_demo_service()._cache.count())

    service = _service(db)
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp.write(await file.read())
        path = Path(tmp.name)
    try:
        imported = service.import_registry_parquet(path)
        db.commit()
    except Exception as exc:
        db.rollback()
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    path.unlink(missing_ok=True)
    COMPLIANCE_REGISTRY_IMPORT_TOTAL.labels(format="parquet").inc(imported)
    return RegistryImportResult(imported=imported, total_in_db=service._cache.count())


@router.post("/cases/{case_id}/fuse", response_model=FusionResultRead)
async def fuse_compliance_case(
    case_id: UUID,
    body: FuseCaseRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")

    licensed = [_parse_licensed(row) for row in body.licensed_events]
    controls = [_parse_control(row) for row in body.control_purchases]

    try:
        result = await service.fuse_case(
            case_id,
            licensed_events=licensed,
            control_purchases=controls,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    COMPLIANCE_FUSION_TOTAL.labels(status="completed").inc()
    return FusionResultRead(**result)


def _fuse_body_from_scenario(body: FuseCaseRequest, scenario_id: str | None) -> FuseCaseRequest:
    if not scenario_id or (body.licensed_events or body.control_purchases):
        return body
    from flowsint_crypto_compliance.demo.scenarios import get_scenario

    scenario = get_scenario(scenario_id)
    return FuseCaseRequest(
        licensed_events=[e.model_dump() for e in scenario.licensed_events],
        control_purchases=[e.model_dump() for e in scenario.control_purchases],
        scenario_id=scenario_id,
    )


async def _fuse_stream_response(
    *,
    case_id: UUID,
    body: FuseCaseRequest,
    request: Request,
    db: Session,
    current_user: Profile,
):
    if COMPLIANCE_DEMO_MODE:
        svc = _demo_service()
        case = svc.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        body = _fuse_body_from_scenario(body, body.scenario_id)

        async def run_fusion():
            licensed = [_parse_licensed(row) for row in body.licensed_events]
            controls = [_parse_control(row) for row in body.control_purchases]
            return await svc.fuse_case(
                case_id,
                licensed_events=licensed,
                control_purchases=controls,
                scenario_id=body.scenario_id,
            )

        async def event_generator():
            async for event in fusion_sse_events(
                case_ref=case.case_ref,
                request_is_disconnected=request.is_disconnected,
                run_fusion=run_fusion,
            ):
                yield event

        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    body = _fuse_body_from_scenario(body, body.scenario_id)

    async def run_fusion():
        licensed = [_parse_licensed(row) for row in body.licensed_events]
        controls = [_parse_control(row) for row in body.control_purchases]
        chain_adapters = get_demo_adapters(body.scenario_id) if body.scenario_id else None
        return await service.fuse_case(
            case_id,
            licensed_events=licensed,
            control_purchases=controls,
            chain_adapters=chain_adapters,
        )

    async def event_generator():
        async for event in fusion_sse_events(
            case_ref=case.case_ref,
            request_is_disconnected=request.is_disconnected,
            run_fusion=run_fusion,
        ):
            yield event

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/cases/{case_id}/fuse/stream")
async def fuse_compliance_case_stream(
    case_id: UUID,
    request: Request,
    scenario_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    """SSE fusion (GET). Pass ?scenario_id= for demo licensed/control events."""
    body = FuseCaseRequest(scenario_id=scenario_id)
    return await _fuse_stream_response(
        case_id=case_id,
        body=body,
        request=request,
        db=db,
        current_user=current_user,
    )


@router.post("/cases/{case_id}/fuse/stream")
async def fuse_compliance_case_stream_post(
    case_id: UUID,
    body: FuseCaseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    """SSE fusion (POST) with licensed_events / control_purchases body."""
    return await _fuse_stream_response(
        case_id=case_id,
        body=body,
        request=request,
        db=db,
        current_user=current_user,
    )


@router.get("/cases/{case_id}/graph")
async def get_case_evidence_graph(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
):
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")

    graph = (case.fusion_result or {}).get("evidence_graph")
    if graph and graph.get("nodes"):
        return enrich_serialized_graph(graph)

    from flowsint_crypto_compliance.storage.graph_store import EvidenceGraphStore

    stored = EvidenceGraphStore().load(case.case_ref)
    if stored.get("nodes"):
        return enrich_serialized_graph(stored)

    raise HTTPException(status_code=404, detail="Evidence graph not available")


@router.post("/cases/{case_id}/graph/merge", response_model=GraphMergeResponse)
async def merge_case_evidence_graph(
    case_id: UUID,
    body: GraphMergeRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    if not body.evidence_graph.get("nodes"):
        raise HTTPException(status_code=422, detail="evidence_graph.nodes required")
    try:
        result = service.merge_case_graph(
            case_id,
            body.evidence_graph,
            merge_mode=body.merge_mode,
            actor_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GraphMergeResponse(**result)


@router.post("/cases/{case_id}/graph/export")
async def export_case_graph(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    graph = (case.fusion_result or {}).get("evidence_graph")
    if not graph or not graph.get("nodes"):
        from flowsint_crypto_compliance.storage.graph_store import EvidenceGraphStore

        stored = EvidenceGraphStore().load(case.case_ref)
        if stored.get("nodes"):
            graph = stored
    if not graph:
        raise HTTPException(status_code=404, detail="Run fusion before graph export")

    exporter = EvidenceGraphNeo4jExporter()
    stored = exporter.fetch_graph_payload(case.case_ref)
    if stored.get("nodes"):
        return {"case_ref": case.case_ref, "source": "neo4j", **stored}
    return {
        "case_ref": case.case_ref,
        "source": "fusion_result",
        **graph,
        "neo4j_export": (case.fusion_result or {}).get("neo4j_export"),
    }


@router.get("/cases/{case_id}/report.json")
async def get_case_report_json(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
):
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.fusion_result:
        raise HTTPException(status_code=404, detail="Report not available")
    return case.fusion_result


@router.post(
    "/cases/{case_id}/fuse/async",
    response_model=FusionAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def fuse_compliance_case_async(
    case_id: UUID,
    body: FuseCaseRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    """Queue OSINT fusion on Celery (long-running cases)."""
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")

    run = service.create_fusion_run(case_id, correlation_id=str(case_id))
    service.log_audit(
        case_id=case_id,
        actor_id=current_user.id,
        action="fusion_async_queued",
        payload={"run_id": str(run.id)},
        correlation_id=str(run.id),
    )
    db.commit()

    task = celery.send_task(
        "run_compliance_fusion",
        args=[
            str(case_id),
            str(run.id),
            body.licensed_events,
            body.control_purchases,
        ],
    )
    service.update_fusion_run(run.id, status="queued", celery_task_id=task.id)
    db.commit()

    return FusionAsyncResponse(run_id=run.id, task_id=task.id, status="queued")


@router.get(
    "/cases/{case_id}/fusion-runs/{run_id}",
    response_model=FusionRunRead,
)
async def get_fusion_run(
    case_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
):
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")

    run = service.get_fusion_run(run_id)
    if not run or run.case_id != case_id:
        raise HTTPException(status_code=404, detail="Fusion run not found")
    return run


@router.get("/demo/scenarios", response_model=list[DemoScenarioRead])
async def list_demo_scenarios(
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    """Сценарии демо-прототипа для показа регулятору."""
    return RegulatorDemoRunner.list_scenarios()


@router.post("/demo/run/{scenario_id}", response_model=RegulatorReportRead)
async def run_demo_scenario(
    scenario_id: str,
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    """
    Запуск полного OSINT-цикла на демо-данных (без ручной загрузки).
    Боевой прототип для презентации регулятору.
    """
    runner = RegulatorDemoRunner()
    try:
        report = await runner.run(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RegulatorReportRead(**report.to_dict())


@router.post("/demo/seed/{scenario_id}", response_model=RegulatorReportRead)
async def seed_and_run_demo(
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    """
    Полный цикл: KYT → банки → fusion → отчёт.
    При COMPLIANCE_DEMO_MODE=1 работает без PostgreSQL.
    """
    if COMPLIANCE_DEMO_MODE:
        try:
            payload = await _demo_service().seed_scenario(scenario_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RegulatorReportRead(**payload)

    from flowsint_crypto_compliance.demo.scenarios import get_scenario
    from flowsint_crypto_compliance.ingestion.hub_rows import bank_feed_to_hub_row

    try:
        scenario = get_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    service = _service(db)
    existing = service.get_case_by_ref(scenario.case_ref)
    if existing:
        case = existing
    else:
        case = service.create_case(
            case_ref=scenario.case_ref,
            owner_id=current_user.id,
        )

    for label in scenario.registry_labels:
        service._cache.put(label)
    db.commit()

    bank_batch = {
        "schema_version": "regulator-hub/v1",
        "hub_id": "demo-fiu-hub-ru",
        "feeds": [bank_feed_to_hub_row(b) for b in scenario.bank_feeds],
    }
    validate_bank_feed_batch(bank_batch)
    service.ingest_bank_feed_batch(case.id, bank_batch)

    try:
        payload = await service.fuse_case_with_report(
            case.id,
            scenario_title_ru=scenario.title_ru,
            licensed_events=scenario.licensed_events,
            control_purchases=scenario.control_purchases,
            chain_adapters=get_demo_adapters(scenario_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RegulatorReportRead(**payload)


@router.get("/demo/health")
async def compliance_demo_health():
    if not COMPLIANCE_DEMO_MODE:
        return {"mode": "production", "demo_fallback": False}
    svc = _demo_service()
    return {
        "mode": "in_memory",
        "demo_fallback": True,
        "registry_labels": svc._cache.count(),
        "cases": len(svc.store.cases),
    }


@router.get("/cases/{case_id}/report.pdf")
async def get_case_report_pdf(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
):
    if COMPLIANCE_DEMO_MODE:
        case = _demo_service().get_case(case_id)
        if not case or not case.fusion_result:
            raise HTTPException(status_code=404, detail="Report not available")
        html = render_regulator_html(case.fusion_result)
        content, media_type = render_pdf_bytes(html)
        filename = f"{case.case_ref}-report.pdf"
        if media_type.startswith("text/html"):
            filename = filename.replace(".pdf", ".html")
        from flowsint_crypto_compliance.platform.v2.operator_events import (
            OperatorEventType,
            publish_operator_event,
        )

        publish_operator_event(
            OperatorEventType.REPORT_GENERATED,
            payload={
                "case_id": str(case_id),
                "case_ref": case.case_ref,
                "format": "pdf",
            },
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.fusion_result:
        raise HTTPException(status_code=404, detail="Report not available")
    html = render_regulator_html(case.fusion_result)
    content, media_type = render_pdf_bytes(html)
    filename = f"{case.case_ref}-report.pdf"
    if media_type.startswith("text/html"):
        filename = filename.replace(".pdf", ".html")
    from flowsint_crypto_compliance.platform.v2.operator_events import (
        OperatorEventType,
        publish_operator_event,
    )

    publish_operator_event(
        OperatorEventType.REPORT_GENERATED,
        payload={
            "case_id": str(case_id),
            "case_ref": case.case_ref,
            "format": "pdf",
        },
        investigation_id=case.investigation_id,
        actor=str(current_user.id),
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cases/{case_id}/report.xlsx")
async def get_case_report_xlsx(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
):
    if COMPLIANCE_DEMO_MODE:
        case = _demo_service().get_case(case_id)
        if not case or not case.fusion_result:
            raise HTTPException(status_code=404, detail="Report not available")
        report = case.fusion_result
    else:
        service = _service(db)
        case = service.get_case(case_id)
        if not case or case.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Case not found")
        if not case.fusion_result:
            raise HTTPException(status_code=404, detail="Report not available")
        report = case.fusion_result

    content = render_regulator_xlsx(report)
    filename = f"{report.get('case_ref', case_id)}-report.xlsx"
    from flowsint_crypto_compliance.platform.v2.operator_events import (
        OperatorEventType,
        publish_operator_event,
    )

    publish_operator_event(
        OperatorEventType.REPORT_GENERATED,
        payload={
            "case_id": str(case_id),
            "case_ref": report.get("case_ref") or getattr(case, "case_ref", str(case_id)),
            "format": "xlsx",
        },
        investigation_id=getattr(case, "investigation_id", None),
        actor=str(current_user.id),
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/cases/{case_id}/hub/pull")
async def pull_regulator_hub(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    """Pull bank STR batch from sovereign regulator hub (mTLS)."""
    connector = RegulatorAPIConnector.from_env()
    if not connector:
        raise HTTPException(status_code=503, detail="REGULATOR_HUB_URL not configured")
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    batch = connector.fetch_bank_feed_batch()
    count = service.ingest_bank_feed_batch(case_id, batch)
    db.commit()
    return {"ingested": count, "hub_id": batch.get("hub_id")}


@router.post("/cases/{case_id}/hub/stream/poll")
async def poll_regulator_hub_stream(
    case_id: UUID,
    max_messages: int = 10,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    """Poll Redpanda/Kafka hub topic when KAFKA_BOOTSTRAP_SERVERS is set."""
    consumer = HubStreamConsumer.from_env()
    if not consumer:
        raise HTTPException(status_code=503, detail="Kafka/Redpanda not configured")
    service = _service(db)
    case = service.get_case(case_id)
    if not case or case.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Case not found")
    total = 0

    def handle(batch: dict) -> None:
        nonlocal total
        total += service.ingest_bank_feed_batch(case_id, batch)

    processed = consumer.poll_once(handle, max_messages=max_messages)
    db.commit()
    return {"batches_processed": processed, "feeds_ingested": total}


@router.get("/metrics")
async def compliance_metrics():
    return Response(content=metrics_payload(), media_type="text/plain; version=0.0.4")


@router.get("/scalpel/status")
async def scalpel_status():
    from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine

    engine = ScalpelEngine()
    tor_probe = await engine._gw.probe_tor()
    from flowsint_crypto_compliance.osint_core.scalpel.workers.maigret_runner import (
        maigret_available,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.workers.spiderfoot_runner import (
        spiderfoot_available,
    )
    from flowsint_crypto_compliance.reporting.ocr_pipeline import _paddle_available

    return {
        **engine.status(),
        "tor_probe": tor_probe,
        "maigret_cli": maigret_available(),
        "spiderfoot_cli": spiderfoot_available(),
        "paddleocr": _paddle_available(),
        "celery_tasks": [
            "run_scalpel_collect",
            *[
                "scalpel_collect_onchain",
                "scalpel_collect_sanctions",
                "scalpel_collect_username",
                "scalpel_collect_username_probe",
                "scalpel_collect_abuse",
                "scalpel_collect_darknet",
                "scalpel_collect_darknet_tor",
                "scalpel_collect_clearnet",
                "scalpel_collect_vasp",
                "scalpel_collect_court",
                "scalpel_collect_dns",
            ],
            "run_maigret_scan",
            "run_spiderfoot_scan",
            "run_ocr_extract",
            "ingest_enforcement_notices",
            "run_multihop_fusion",
            "live_collect_tron_chain",
            "live_collect_tron_trc20",
            "live_collect_btc_chain",
            "live_collect_sanctions",
            "live_collect_bitcoinabuse",
            "live_collect_maigret",
            "live_collect_ahmia",
        ],
        "mode": "battle",
    }


@router.get("/scalpel/collectors")
async def scalpel_collectors_catalog(
    current_user: Profile = Depends(get_current_user),
):
    """Scalpel Console — collector catalog with health, metrics, and call history."""
    from flowsint_crypto_compliance.config.env_loader import trongrid_key_configured
    from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine
    from flowsint_crypto_compliance.osint_core.scalpel.console_catalog import build_scalpel_console_catalog

    engine = ScalpelEngine()
    tor_probe = await engine._gw.probe_tor()
    tor_ok = engine._gw.config.tor_enabled() or bool(
        tor_probe.get("ok") or tor_probe.get("reachable")
    )
    catalog = await build_scalpel_console_catalog(
        tor_available=tor_ok,
        trongrid_configured=trongrid_key_configured(),
    )
    return {
        **catalog,
        "tor_probe": tor_probe,
        "osint_depth_labels": {
            "1": "Target address only",
            "2": "Address + 1-hop counterparties (on-chain)",
            "3": "2-hop: counterparties + OSINT entity addresses",
        },
    }


@router.post(
    "/scalpel/collect/async",
    response_model=ScalpelAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def scalpel_collect_async(
    body: ScalpelCollectRequest,
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    task = celery.send_task(
        "run_scalpel_collect",
        kwargs={
            "address": body.address,
            "chain": body.chain.lower(),
            "depth": body.depth,
            "counterparties": body.counterparties,
            "usernames": body.usernames,
            "collectors": body.collectors or None,
        },
    )
    return ScalpelAsyncResponse(task_id=task.id, status="queued")


@router.post(
    "/scalpel/maigret/async",
    response_model=ScalpelAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def maigret_scan_async(
    body: MaigretScanRequest,
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    from flowsint_crypto_compliance.osint_core.scalpel.security import sanitize_username

    try:
        username = sanitize_username(body.username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    task = celery.send_task(
        "run_maigret_scan",
        kwargs={
            "username": username,
            "top_sites": min(body.top_sites, 500),
            "use_tor": body.use_tor,
        },
    )
    return ScalpelAsyncResponse(task_id=task.id, status="queued")


@router.post(
    "/scalpel/spiderfoot/async",
    response_model=ScalpelAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def spiderfoot_scan_async(
    body: SpiderFootScanRequest,
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    task = celery.send_task(
        "run_spiderfoot_scan",
        kwargs={"target": body.target, "modules": body.modules or None},
    )
    return ScalpelAsyncResponse(task_id=task.id, status="queued")


@router.get("/scalpel/tasks/{task_id}", response_model=ScalpelTaskStatus)
async def scalpel_task_status(
    task_id: str,
    current_user: Profile = Depends(get_current_user),
):
    from celery.result import AsyncResult

    async_result = AsyncResult(task_id, app=celery)
    payload: dict = {
        "task_id": task_id,
        "status": async_result.status,
        "result": None,
        "error": None,
    }
    if async_result.ready():
        if async_result.successful():
            payload["result"] = async_result.result
        else:
            payload["error"] = str(async_result.result)[:2000]
    return ScalpelTaskStatus(**payload)


@router.get("/graph/status")
async def graph_store_status(current_user: Profile = Depends(get_current_user)):
    from flowsint_crypto_compliance.storage.graph_store import EvidenceGraphStore

    return EvidenceGraphStore().status()


@router.get("/graph/{case_ref}")
async def graph_load(case_ref: str, current_user: Profile = Depends(get_current_user)):
    from flowsint_crypto_compliance.storage.graph_store import EvidenceGraphStore

    return EvidenceGraphStore().load(case_ref)


@router.get("/ml/status")
async def ml_status(current_user: Profile = Depends(get_current_user)):
    from flowsint_crypto_compliance.ml.onnx_inference import ONNXRiskScorer, default_model_path

    scorer = ONNXRiskScorer()
    return {
        "onnx_available": scorer.available,
        "model_path": str(default_model_path()),
        "features": 10,
        "graphsage_hops": 2,
    }


@router.post("/enforcement/ingest")
async def enforcement_ingest(current_user: Profile = Depends(require_permission("batch:screen"))):
    from flowsint_crypto_compliance.ingestion.enforcement_feeds import ingest_enforcement_feeds

    return ingest_enforcement_feeds()


@router.get("/live/collectors/status")
async def live_collectors_status(current_user: Profile = Depends(get_current_user)):
    from flowsint_crypto_compliance.osint_core.live_cache import _TTL
    from flowsint_crypto_compliance.osint_core.live_collector_registry import list_live_collectors
    from flowsint_crypto_compliance.ml.active_learning import active_label_count
    from flowsint_core.tasks.live_collectors import LIVE_COLLECTOR_TASKS

    return {
        "mode": "battle",
        "collectors": list_live_collectors(),
        "celery_tasks": LIVE_COLLECTOR_TASKS,
        "cache_ttl_sec": _TTL,
        "rate_limit_rps": 5,
        "active_learning_labels": active_label_count(),
        "env": {
            "BITCOINABUSE_API_KEY": bool(os.getenv("BITCOINABUSE_API_KEY")),
            "TRONGRID_API_KEY": bool(os.getenv("TRONGRID_API_KEY")),
        },
    }


@router.post("/live/collect")
async def live_collect_one(
    body: LiveCollectRequest,
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    from flowsint_crypto_compliance.osint_core.live_collector_registry import (
        LIVE_COLLECTOR_REGISTRY,
        run_live_collector,
    )

    if body.collector not in LIVE_COLLECTOR_REGISTRY:
        raise HTTPException(status_code=422, detail=f"Unknown collector: {body.collector}")
    param = LIVE_COLLECTOR_REGISTRY[body.collector]["param"]
    value = (
        body.address
        if param == "address"
        else body.query
        if param == "query"
        else body.username
    )
    if not value or not str(value).strip():
        raise HTTPException(status_code=422, detail=f"Provide '{param}' for {body.collector}")

    if body.async_mode:
        task_name = LIVE_COLLECTOR_REGISTRY[body.collector].get("celery_task")
        if not task_name:
            raise HTTPException(status_code=422, detail="No celery task for collector")
        task = celery.send_task(task_name, args=[str(value).strip()])
        return {"task_id": task.id, "status": "queued", "collector": body.collector}

    try:
        result = await asyncio.wait_for(
            run_live_collector(body.collector, str(value).strip()),
            timeout=45.0,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Collector timeout (45s)") from exc
    return {"collector": body.collector, "result": result}


@router.post("/live/fusion")
async def live_multihop_fusion(
    body: LiveFusionRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    idem_key = body.idempotency_key or f"live-fusion:{body.chain}:{body.address.strip()}:{body.max_hops}"
    if body.async_mode:
        task = celery.send_task(
            "run_multihop_fusion",
            kwargs={
                "address": body.address.strip(),
                "chain": body.chain.lower(),
                "case_ref": body.case_ref,
                "max_hops": body.max_hops,
                "idempotency_key": idem_key,
            },
        )
        return LiveFusionAsyncResponse(task_id=task.id, status="queued", idempotency_key=idem_key)

    from flowsint_crypto_compliance.ml.scoring_pipeline import score_fusion_graph
    from flowsint_crypto_compliance.osint_core.multihop_fusion import MultiHopFusionEngine
    from flowsint_crypto_compliance.storage.wallet_neo4j import WalletNeo4jStore

    try:
        engine = MultiHopFusionEngine(max_hops=body.max_hops)
        graph = await asyncio.wait_for(
            engine.explore(body.address.strip(), body.chain.lower()),
            timeout=30.0,
        )
        payload = graph.to_dict()
        ref = body.case_ref or f"LIVE-{body.chain.upper()}-{body.address[:12]}"
        payload["case_ref"] = ref
        payload["ml_score"] = score_fusion_graph(payload, address=body.address, chain=body.chain)
        payload["neo4j"] = WalletNeo4jStore().persist_fusion_graph(payload, case_ref=ref)
        _service(db).log_audit(
            actor_id=current_user.id,
            action="live_fusion_completed",
            payload={"case_ref": ref, "nodes": payload.get("node_count", 0)},
            correlation_id=idem_key,
        )
        db.commit()
        return payload
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Live fusion timeout (30s)") from exc


@router.get("/events/stream")
async def compliance_events_stream(
    current_user: Profile = Depends(require_permission("case:read")),
):
    """SSE relay for compliance domain events (Redis Streams / memory)."""
    from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

    async def _gen():
        bus = get_event_bus()
        for ev in bus.recent(5):
            yield {"event": "message", "data": json.dumps(ev, ensure_ascii=False)}
        import asyncio

        loop = asyncio.get_event_loop()
        while True:
            ev = await loop.run_in_executor(None, _next_event, bus)
            if ev:
                yield {"event": "message", "data": json.dumps(ev, ensure_ascii=False)}
            await asyncio.sleep(0.05)

    return EventSourceResponse(_gen())


def _next_event(bus):
    for ev in bus.stream_events(block_ms=1500):
        return ev
    return None


@router.get("/dashboard/read-model")
async def compliance_dashboard_read_model(
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
):
    from flowsint_crypto_compliance.infrastructure.read_models import ComplianceDashboardReadModel

    return ComplianceDashboardReadModel(db).get()


@router.get("/audit", response_model=list[ComplianceAuditLogRead])
async def list_compliance_audit(
    case_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
):
    service = _service(db)
    rows = service.list_audit_log(case_id=case_id, limit=limit, offset=offset)
    _service(db).log_audit(
        actor_id=current_user.id,
        action="audit_log_viewed",
        payload={"case_id": str(case_id) if case_id else None, "limit": limit},
        publish_event=False,
    )
    db.commit()
    return rows


@router.get("/circuit-breakers/status")
async def circuit_breaker_status(
    current_user: Profile = Depends(get_current_user),
):
    from flowsint_crypto_compliance.infrastructure.circuit_breaker import all_breaker_statuses

    return {"breakers": all_breaker_statuses()}


@router.post("/scoring/predict")
async def scoring_predict(
    body: ScoringPredictRequest,
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    from flowsint_crypto_compliance.ml.scoring_pipeline import score_fusion_graph

    if not body.graph.get("nodes"):
        raise HTTPException(status_code=422, detail="graph.nodes required")
    return score_fusion_graph(body.graph, address=body.address, chain=body.chain)


@router.post("/scoring/label-case")
async def scoring_label_case(
    body: ScoringLabelCaseRequest,
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    from flowsint_crypto_compliance.ml.active_learning import append_case_label

    return append_case_label(
        case_ref=body.case_ref,
        address=body.address,
        chain=body.chain,
        label=body.label,
        risk_score=body.risk_score,
        features=body.features,
        source=body.source,
    )


@router.post("/ocr/extract", response_model=OCRExtractResponse)
async def ocr_extract(
    file: UploadFile = File(...),
    backend: str = "auto",
    async_mode: bool = False,
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    import base64

    from flowsint_crypto_compliance.osint_core.scalpel.security import (
        assert_upload_size,
        sanitize_filename,
    )

    data = await file.read()
    try:
        assert_upload_size(len(data))
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    filename = sanitize_filename(file.filename or "document.pdf")
    allowed_backends = {"auto", "paddle", "pymupdf", "tesseract"}
    if backend not in allowed_backends:
        raise HTTPException(status_code=422, detail="Unsupported OCR backend")
    if async_mode:
        task = celery.send_task(
            "run_ocr_extract",
            kwargs={
                "filename": filename,
                "data_b64": base64.b64encode(data).decode("ascii"),
                "backend": backend,
            },
        )
        return OCRExtractResponse(
            filename=filename,
            backend="celery_queued",
            text_chars=0,
            confidence=0.0,
            seizure_fields={},
            entities={},
            suitable_for_seizure_report=False,
            warnings=[f"task_id:{task.id}"],
        )

    from flowsint_crypto_compliance.reporting.ocr_pipeline import OCRPipeline

    result = OCRPipeline().process_bytes(data, filename, backend=backend)
    d = result.to_dict()
    return OCRExtractResponse(
        filename=d["filename"],
        backend=d["backend"],
        text_chars=d["text_chars"],
        confidence=d["confidence"],
        seizure_fields=d["seizure_fields"],
        entities=d["entities"],
        suitable_for_seizure_report=d["suitable_for_seizure_report"],
        warnings=d.get("warnings") or [],
    )


def _parse_licensed(row: dict) -> LicensedPlatformEvent:
    return LicensedPlatformEvent(
        event_id=str(row["event_id"]),
        platform_name=str(row["platform_name"]),
        platform_license_id=row.get("platform_license_id"),
        region=row.get("region"),
        direction=str(row["direction"]).lower(),
        chain=Chain(str(row["chain"]).lower()),
        address=str(row["address"]),
        amount_crypto=row.get("amount_crypto"),
        asset=row.get("asset"),
        amount_fiat=row.get("amount_fiat"),
        currency=row.get("currency"),
        user_ref=row.get("user_ref"),
        observed_at=row.get("observed_at"),
    )


def _parse_control(row: dict) -> ControlPurchaseEvent:
    return ControlPurchaseEvent(
        event_id=str(row["event_id"]),
        operator_ref=str(row["operator_ref"]),
        region=str(row["region"]),
        channel=str(row["channel"]),
        chain=Chain(str(row["chain"]).lower()),
        source_address=row.get("source_address"),
        target_address=str(row["target_address"]),
        asset=row.get("asset"),
        amount_fiat=row.get("amount_fiat"),
        currency=row.get("currency"),
        observed_at=row.get("observed_at"),
        notes=row.get("notes"),
    )
