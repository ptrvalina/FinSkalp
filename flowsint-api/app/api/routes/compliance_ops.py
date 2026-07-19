"""Additional compliance API routes — workflow, batch, webhooks, watchlist, FZ115 export."""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from flowsint_core.core.celery import celery
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.compliance import (
    BatchScreenJobRead,
    CaseCommentCreate,
    CaseCommentRead,
    CaseQueueOrderRequest,
    CaseTransitionRequest,
    ComplianceCaseListItem,
    ComplianceCaseRead,
    ComplianceInboxItem,
    ComplianceReportListItem,
    CrossCaseGraphLink,
    CrossCaseGraphLinksRead,
    RiskHistoryPoint,
    RiskHistoryRead,
    WatchlistSubscribeRequest,
    WatchlistSubscriptionRead,
    WebhookRegisterRequest,
    WebhookRegisterResponse,
)
from flowsint_crypto_compliance.services.case_display import resolve_assignee_fields
from flowsint_core.core.models import Profile
from flowsint_core.core.postgre_db import get_db
from flowsint_crypto_compliance.observability.metrics import COMPLIANCE_WEBHOOK_INGEST_TOTAL
from flowsint_crypto_compliance.reporting.fz115_xml import fz115_report_to_xml
from flowsint_crypto_compliance.reporting.report_i18n import localize_fz115_report
from flowsint_crypto_compliance.services.batch_screening import BatchScreeningService
from flowsint_crypto_compliance.services.batch_parser import parse_address_rows
from flowsint_crypto_compliance.services.case_workflow import workflow_payload
from flowsint_crypto_compliance.services.compliance_rbac import (
    can_access_case,
    get_user_compliance_role,
    require_permission,
    user_has_permission,
    ComplianceRole,
)
from flowsint_crypto_compliance.services.compliance_service import ComplianceService
from flowsint_crypto_compliance.services.webhook_ingest import WebhookIngestService, verify_signature, resolve_webhook_secret
from flowsint_crypto_compliance.services.watchlist_monitor import WatchlistMonitorService
from flowsint_crypto_compliance.storage.db_models import ComplianceBatchScreenJob

router = APIRouter()


def _svc(db: Session) -> ComplianceService:
    return ComplianceService(db)


def _case_list_items(db: Session, cases: list) -> list[ComplianceCaseListItem]:
    svc = _svc(db)
    assignee_ids = {c.assignee_id for c in cases if c.assignee_id}
    profiles = svc.load_profiles(assignee_ids)
    out: list[ComplianceCaseListItem] = []
    for c in cases:
        names = resolve_assignee_fields(c.assignee_id, profiles)
        out.append(
            ComplianceCaseListItem(
                id=c.id,
                case_ref=c.case_ref,
                status=c.status,
                investigation_id=c.investigation_id,
                workflow_status=c.workflow_status or "new",
                assignee_id=c.assignee_id,
                assignee_name=names["assignee_name"],
                analyst_name_ru=names["analyst_name_ru"],
                priority=c.priority or "normal",
                due_at=c.due_at,
                sla_breached=bool(c.sla_breached),
                queue_priority=c.queue_priority,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return out


def _case_read_payload(db: Session, case) -> ComplianceCaseRead:
    svc = _svc(db)
    profiles = svc.load_profiles({case.assignee_id} if case.assignee_id else set())
    names = resolve_assignee_fields(case.assignee_id, profiles)
    history = svc.get_case_risk_history(case.id)
    return ComplianceCaseRead(
        id=case.id,
        case_ref=case.case_ref,
        status=case.status,
        investigation_id=case.investigation_id,
        fusion_result=case.fusion_result,
        workflow_status=case.workflow_status,
        assignee_id=case.assignee_id,
        assignee_name=names["assignee_name"],
        analyst_name_ru=names["analyst_name_ru"],
        priority=case.priority,
        due_at=case.due_at,
        sla_breached=bool(case.sla_breached),
        queue_priority=case.queue_priority,
        risk_trend=history or None,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def _ensure_case_access(db: Session, user: Profile, case_id: UUID):
    svc = _svc(db)
    case = svc.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    role = get_user_compliance_role(db, user.id)
    if not can_access_case(user, case, role):
        raise HTTPException(status_code=403, detail="Access denied")
    return case, role


@router.get("/cases", response_model=list[ComplianceCaseListItem])
async def list_compliance_cases(
    workflow_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    role = get_user_compliance_role(db, current_user.id)
    owner_filter = None if role == ComplianceRole.ADMIN else current_user.id
    cases = _svc(db).list_cases(owner_filter, workflow_status=workflow_status, limit=limit, offset=offset)
    return _case_list_items(db, cases)


@router.patch("/cases/{case_id}", response_model=ComplianceCaseRead)
async def transition_compliance_case(
    case_id: UUID,
    body: CaseTransitionRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    case, role = _ensure_case_access(db, current_user, case_id)
    if body.workflow_status == "filed" and not user_has_permission(role, "case:file_fz115"):
        raise HTTPException(status_code=403, detail="Only compliance officer can mark as filed")
    try:
        updated = _svc(db).transition_case(
            case_id,
            workflow_status=body.workflow_status,
            actor_id=current_user.id,
            assignee_id=body.assignee_id,
            priority=body.priority,
            queue_priority=body.queue_priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _case_read_payload(db, updated)


@router.get("/cases/{case_id}/comments", response_model=list[CaseCommentRead])
async def list_case_comments(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    _ensure_case_access(db, current_user, case_id)
    return _svc(db).list_comments(case_id)


@router.post("/cases/{case_id}/comments", response_model=CaseCommentRead, status_code=status.HTTP_201_CREATED)
async def add_case_comment(
    case_id: UUID,
    body: CaseCommentCreate,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:comment")),
):
    _ensure_case_access(db, current_user, case_id)
    return _svc(db).add_comment(case_id, current_user.id, body.body)


@router.post("/wallets/screen/batch", response_model=BatchScreenJobRead, status_code=status.HTTP_202_ACCEPTED)
async def batch_screen_wallets(
    file: UploadFile = File(...),
    async_mode: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    raw = await file.read()
    rows = parse_address_rows(raw, filename=file.filename or "upload.csv")
    if not rows:
        raise HTTPException(status_code=422, detail="No addresses parsed from file")
    if len(rows) > 10_000:
        raise HTTPException(status_code=422, detail="Max 10,000 addresses per batch")
    svc = BatchScreeningService(db)
    job = svc.create_job(current_user.id, rows)
    if async_mode:
        task = celery.send_task("run_batch_wallet_screen", args=[str(job.id), rows])
        job.celery_task_id = task.id
        job.status = "queued"
        db.commit()
    else:
        import asyncio

        await svc.run_job_sync(job.id, rows)
        db.refresh(job)
    return job


@router.get("/wallets/screen/batch/{job_id}", response_model=BatchScreenJobRead)
async def get_batch_screen_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("batch:screen")),
):
    job = db.get(ComplianceBatchScreenJob, job_id)
    if not job or (job.owner_id != current_user.id and get_user_compliance_role(db, current_user.id) != ComplianceRole.ADMIN):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/hub/webhook/{bank_id}")
async def inbound_bank_webhook(
    bank_id: str,
    request: Request,
    case_id: UUID = Query(..., description="Target compliance case"),
    x_hub_signature: str = Header(..., alias="X-Hub-Signature"),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
):
    raw = await request.body()
    secret = resolve_webhook_secret(db, bank_id)
    if not secret or not verify_signature(raw, x_hub_signature, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = WebhookIngestService.parse_body(raw)
    svc = WebhookIngestService(db)
    try:
        count = svc.ingest(bank_id=bank_id, payload=payload, case_id=case_id, idempotency_key=x_idempotency_key)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    COMPLIANCE_WEBHOOK_INGEST_TOTAL.labels(bank_id=bank_id).inc()
    return {"ingested": count, "case_id": str(case_id)}


@router.post("/webhooks/register", response_model=WebhookRegisterResponse)
async def register_webhook(
    body: WebhookRegisterRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("webhook:manage")),
):
    row = WebhookIngestService(db).register_endpoint(body.bank_id, body.secret, body.outbound_url)
    return WebhookRegisterResponse(bank_id=row.bank_id, secret_hint=row.secret_hint, enabled=row.enabled)


@router.post("/watchlist/subscribe", response_model=WatchlistSubscriptionRead, status_code=status.HTTP_201_CREATED)
async def watchlist_subscribe(
    body: WatchlistSubscribeRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("watchlist:manage")),
):
    sub = WatchlistMonitorService(db).subscribe(
        current_user.id, address=body.address, chain=body.chain, label=body.label
    )
    return sub


@router.get("/watchlist", response_model=list[WatchlistSubscriptionRead])
async def watchlist_list(
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("watchlist:manage")),
):
    return WatchlistMonitorService(db).list_subscriptions(current_user.id)


@router.post("/watchlist/scan")
async def watchlist_scan_now(
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("watchlist:manage")),
):
    task = celery.send_task("scan_watchlist_subscriptions", kwargs={"limit": 500})
    return {"task_id": task.id, "status": "queued"}


@router.get("/cases/{case_id}/report/fz115")
async def get_fz115_report(
    case_id: UUID,
    locale: str = Query("ru", pattern="^(ru|en)$"),
    format: str = Query("json", pattern="^(json|xml)$"),
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    case, _ = _ensure_case_access(db, current_user, case_id)
    fusion = case.fusion_result or {}
    report = fusion.get("fz115_report") or fusion
    if not report.get("report_id") and not report.get("decision_ru"):
        raise HTTPException(status_code=404, detail="FZ115 report not available — run fusion first")
    localized = localize_fz115_report(report, locale=locale)
    if format == "xml":
        xml = fz115_report_to_xml(localized, locale=locale)
        return Response(content=xml, media_type="application/xml")
    return localized


@router.get("/cases/workflow/stats")
async def compliance_workflow_stats(
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    role = get_user_compliance_role(db, current_user.id)
    owner_filter = None if role == ComplianceRole.ADMIN else current_user.id
    if role == ComplianceRole.COMPLIANCE_OFFICER:
        owner_filter = None
    return _svc(db).workflow_stats(owner_filter)


def _inbox_owner_filter(db: Session, user: Profile) -> UUID | None:
    role = get_user_compliance_role(db, user.id)
    if role in (ComplianceRole.ADMIN, ComplianceRole.COMPLIANCE_OFFICER):
        return None
    return user.id


@router.get("/inbox", response_model=list[ComplianceInboxItem])
async def list_compliance_inbox(
    workflow_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    """Single operator inbox — same cases as kanban, no duplicate :8877 queue."""
    owner_filter = _inbox_owner_filter(db, current_user)
    cases = _svc(db).list_cases(owner_filter, workflow_status=workflow_status, limit=limit, offset=offset)
    profiles = _svc(db).load_profiles({c.assignee_id for c in cases if c.assignee_id})
    return [
        ComplianceInboxItem(
            id=str(c.id),
            case_id=str(c.id),
            case_ref=c.case_ref,
            alert_code=c.case_ref,
            priority=c.priority or "normal",
            workflow_status=c.workflow_status or "new",
            title_ru=f"Дело {c.case_ref}",
            investigation_id=c.investigation_id,
            assignee_id=c.assignee_id,
            **resolve_assignee_fields(c.assignee_id, profiles),
            sla_breached=bool(c.sla_breached),
            due_at=c.due_at,
        )
        for c in cases
    ]


@router.get("/reports", response_model=list[ComplianceReportListItem])
async def list_compliance_reports(
    case_ref: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    owner_filter = _inbox_owner_filter(db, current_user)
    cases = _svc(db).list_cases(owner_filter, limit=limit, offset=0)
    if case_ref:
        cases = [c for c in cases if c.case_ref == case_ref]
    out: list[ComplianceReportListItem] = []
    for c in cases:
        fusion = c.fusion_result or {}
        fz = fusion.get("fz115_report") if isinstance(fusion.get("fz115_report"), dict) else fusion
        if not isinstance(fz, dict):
            continue
        if not (fz.get("report_id") or fz.get("decision_ru")):
            continue
        out.append(
            ComplianceReportListItem(
                case_id=str(c.id),
                case_ref=c.case_ref,
                report_id=fz.get("report_id"),
                typology_code=fz.get("typology_code"),
                risk_level=fz.get("risk_level"),
                decision_ru=fz.get("decision_ru"),
                generated_at=fz.get("generated_at"),
            )
        )
    return out


@router.get("/cases/{case_id}/workflow")
async def get_case_workflow(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    case, _ = _ensure_case_access(db, current_user, case_id)
    return workflow_payload(case)


@router.get("/cases/{case_id}/risk-history", response_model=RiskHistoryRead)
async def get_case_risk_history(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    _ensure_case_access(db, current_user, case_id)
    svc = _svc(db)
    points = svc.get_case_risk_history(case_id)
    return RiskHistoryRead(
        case_id=str(case_id),
        points=[RiskHistoryPoint(**p) for p in points],
        trend=svc.risk_trend_indicator(points),
    )


@router.post("/cases/queue-order")
async def reorder_compliance_queue(
    body: CaseQueueOrderRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:transition")),
):
    updated = _svc(db).reorder_case_queue(body.case_ids, actor_id=current_user.id)
    return {"ok": True, "updated": updated}


@router.get("/graph/links", response_model=CrossCaseGraphLinksRead)
async def get_cross_case_graph_links(
    case_ref: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Profile = Depends(require_permission("case:read")),
):
    svc = _svc(db)
    case = svc.get_case_by_ref(case_ref)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    role = get_user_compliance_role(db, current_user.id)
    if not can_access_case(current_user, case, role):
        raise HTTPException(status_code=403, detail="Access denied")
    links = svc.get_cross_case_graph_links(case_ref, limit=limit)
    return CrossCaseGraphLinksRead(
        case_ref=case_ref,
        links=[CrossCaseGraphLink(**link) for link in links],
        count=len(links),
    )
