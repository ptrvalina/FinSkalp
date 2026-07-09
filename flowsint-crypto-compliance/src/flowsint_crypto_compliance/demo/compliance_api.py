"""Compliance REST API for demo stand — no PostgreSQL, Neo4j, Redis or auth."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from flowsint_crypto_compliance.demo.demo_context import get_demo_chain_adapters, get_demo_label_cache, preload_kyt_samples
from flowsint_crypto_compliance.demo.runner import RegulatorDemoRunner
from flowsint_crypto_compliance.reporting.fz115_report import FZ115ReportBuilder
from flowsint_crypto_compliance.reporting.pdf_report import (
    render_fz115_html,
    render_pdf_bytes,
    render_regulator_html,
)
from flowsint_crypto_compliance.services.demo_compliance_service import get_demo_compliance_service
from flowsint_crypto_compliance.services.fusion_sse import fusion_sse_events
from flowsint_crypto_compliance.reporting.excel_report import render_regulator_xlsx
from flowsint_crypto_compliance.observability.metrics import metrics_payload
from flowsint_crypto_compliance.services.wallet_screening import (
    WalletScreeningRequest,
    WalletScreeningService,
)
from flowsint_types.fiat_crypto import Chain, ControlPurchaseEvent, LicensedPlatformEvent

router = APIRouter()


class CaseCreate(BaseModel):
    case_ref: str = Field(..., min_length=1, max_length=64)


class FuseCaseBody(BaseModel):
    licensed_events: list[dict[str, Any]] = Field(default_factory=list)
    control_purchases: list[dict[str, Any]] = Field(default_factory=list)
    scenario_id: str | None = None


class WalletScreenBody(BaseModel):
    address: str
    chain: str | None = None
    depth: int = 1
    limit: int = 50


class BankFeedBatchIn(BaseModel):
    schema_version: str = "regulator-hub/v1"
    hub_id: str = "demo-fiu-hub-ru"
    feeds: list[dict[str, Any]]


def _wallet_service() -> WalletScreeningService:
    return WalletScreeningService(
        chain_adapters=get_demo_chain_adapters(),
        label_cache=get_demo_label_cache(),
    )


def _case_read(case) -> dict[str, Any]:
    return {
        "id": str(case.id),
        "case_ref": case.case_ref,
        "status": case.status,
        "fusion_result": case.fusion_result,
    }


@router.get("/health")
async def compliance_health():
    svc = get_demo_compliance_service()
    return {
        "status": "ok",
        "mode": "in_memory",
        "registry_labels": svc._cache.count(),
        "cases": len(svc.store.cases),
    }


@router.post("/wallets/screen")
async def screen_wallet(body: WalletScreenBody):
    try:
        chain = Chain(body.chain.lower()) if body.chain else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unsupported chain") from exc
    try:
        result = await _wallet_service().screen(
            WalletScreeningRequest(
                address=body.address,
                chain=chain,
                depth=body.depth,
                limit=body.limit,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@router.post("/cases", status_code=status.HTTP_201_CREATED)
async def create_case(body: CaseCreate):
    svc = get_demo_compliance_service()
    if svc.get_case_by_ref(body.case_ref):
        raise HTTPException(status_code=409, detail="case_ref already exists")
    case = svc.create_case(case_ref=body.case_ref)
    return _case_read(case)


@router.get("/cases/{case_id}")
async def get_case(case_id: uuid.UUID):
    svc = get_demo_compliance_service()
    case = svc.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_read(case)


@router.post("/cases/{case_id}/bank-feeds", status_code=status.HTTP_202_ACCEPTED)
async def ingest_bank_feeds(case_id: uuid.UUID, body: BankFeedBatchIn):
    svc = get_demo_compliance_service()
    try:
        count = svc.ingest_bank_feed_batch(case_id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ingested": count, "case_id": str(case_id)}


@router.post("/registry/import")
async def import_registry(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith((".jsonl", ".ndjson", ".json")):
        raise HTTPException(status_code=400, detail="Ожидается .jsonl/.ndjson")
    raw = (await file.read()).decode("utf-8")
    svc = get_demo_compliance_service()
    try:
        imported = svc.import_registry_jsonl_lines(raw.splitlines())
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"imported": imported, "total_in_db": svc._cache.count()}


@router.post("/registry/import/parquet")
async def import_registry_parquet(file: UploadFile = File(...)):
    import tempfile
    from pathlib import Path

    if not file.filename or not file.filename.endswith(".parquet"):
        raise HTTPException(status_code=400, detail="Ожидается .parquet")
    svc = get_demo_compliance_service()
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp.write(await file.read())
        path = Path(tmp.name)
    try:
        imported = svc.import_registry_parquet(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    path.unlink(missing_ok=True)
    return {"imported": imported, "total_in_db": svc._cache.count()}


@router.post("/kyt/import")
async def import_kyt(file: UploadFile = File(...)):
    """Import MetaSleuth / BlockSec / CSV / XLSX wallet labels and exposure."""
    from flowsint_crypto_compliance.ingestion.kyt_import import import_kyt_bundle, parse_kyt_bytes
    from flowsint_crypto_compliance.storage.kyt_exposure_store import put_exposure

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    raw = await file.read()
    cache = get_demo_label_cache()
    try:
        bundle = parse_kyt_bytes(raw, file.filename)
        stats = import_kyt_bundle(cache, bundle)
        focus = bundle.get("focus_address")
        rows = bundle.get("exposure_rows") or []
        if focus and rows:
            put_exposure(bundle.get("chain", "tron"), focus, rows)
            stats["focus_address"] = focus
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return stats


@router.post("/cases/{case_id}/fuse")
async def fuse_case(case_id: uuid.UUID, body: FuseCaseBody | None = None):
    svc = get_demo_compliance_service()
    if not svc.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    body = body or FuseCaseBody()
    licensed = [_parse_licensed(row) for row in body.licensed_events]
    controls = [_parse_control(row) for row in body.control_purchases]
    try:
        result = await svc.fuse_case(
            case_id,
            licensed_events=licensed,
            control_purchases=controls,
            scenario_id=body.scenario_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.get("/cases/{case_id}/fuse/stream")
async def fuse_case_stream(
    case_id: uuid.UUID,
    request: Request,
    scenario_id: str | None = None,
):
    svc = get_demo_compliance_service()
    case = svc.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return await _demo_fuse_stream(case_id, case, FuseCaseBody(scenario_id=scenario_id), request)


@router.post("/cases/{case_id}/fuse/stream")
async def fuse_case_stream_post(
    case_id: uuid.UUID,
    body: FuseCaseBody,
    request: Request,
):
    svc = get_demo_compliance_service()
    case = svc.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return await _demo_fuse_stream(case_id, case, body, request)


async def _demo_fuse_stream(case_id, case, body: FuseCaseBody, request: Request):
    from flowsint_crypto_compliance.demo.scenarios import get_scenario

    if body.scenario_id and not body.licensed_events:
        scenario = get_scenario(body.scenario_id)
        body = FuseCaseBody(
            licensed_events=[e.model_dump() for e in scenario.licensed_events],
            control_purchases=[e.model_dump() for e in scenario.control_purchases],
            scenario_id=body.scenario_id,
        )
    svc = get_demo_compliance_service()

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


@router.get("/cases/{case_id}/graph")
async def get_graph(case_id: uuid.UUID):
    svc = get_demo_compliance_service()
    case = svc.get_case(case_id)
    if not case or not case.fusion_result:
        raise HTTPException(status_code=404, detail="Evidence graph not available")
    graph = case.fusion_result.get("evidence_graph")
    if not graph:
        raise HTTPException(status_code=404, detail="Evidence graph not available")
    return graph


@router.get("/cases/{case_id}/report.json")
async def get_report_json(case_id: uuid.UUID):
    svc = get_demo_compliance_service()
    case = svc.get_case(case_id)
    if not case or not case.fusion_result:
        raise HTTPException(status_code=404, detail="Report not available")
    return case.fusion_result


@router.get("/cases/{case_id}/report.pdf")
async def get_report_pdf(case_id: uuid.UUID):
    svc = get_demo_compliance_service()
    case = svc.get_case(case_id)
    if not case or not case.fusion_result:
        raise HTTPException(status_code=404, detail="Report not available")
    html = render_regulator_html(case.fusion_result)
    content, media_type = render_pdf_bytes(html)
    filename = f"{case.case_ref}-report.pdf"
    if media_type.startswith("text/html"):
        filename = f"{case.case_ref}-report.html"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cases/{case_id}/report.xlsx")
async def get_report_xlsx(case_id: uuid.UUID):
    svc = get_demo_compliance_service()
    case = svc.get_case(case_id)
    if not case or not case.fusion_result:
        raise HTTPException(status_code=404, detail="Report not available")
    content = render_regulator_xlsx(case.fusion_result)
    filename = f"{case.case_ref}-report.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/metrics")
async def compliance_metrics():
    return Response(content=metrics_payload(), media_type="text/plain; version=0.0.4")


@router.get("/demo/scenarios")
async def list_scenarios():
    return RegulatorDemoRunner.list_scenarios()


@router.post("/demo/run/{scenario_id}")
async def run_demo(scenario_id: str):
    runner = RegulatorDemoRunner()
    try:
        report = await runner.run(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return report.to_dict()


@router.post("/demo/seed/{scenario_id}")
async def seed_demo(scenario_id: str):
    svc = get_demo_compliance_service()
    try:
        payload = await svc.seed_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return payload


@router.post("/demo/fz115/{scenario_id}")
async def build_fz115_from_scenario(scenario_id: str):
    """Сформировать справку 115-ФЗ по демо-сценарию (без inbox alert)."""
    runner = RegulatorDemoRunner()
    try:
        report = await runner.run(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    report_dict = report.to_dict()
    fz115 = FZ115ReportBuilder().build(
        alert={
            "scenario_id": scenario_id,
            "alert_code": f"DEMO-{scenario_id}",
            "case_ref": report.case_ref,
        },
        investigation_report=report_dict,
    ).to_dict()
    return fz115


@router.post("/demo/fz115/{scenario_id}/pdf")
async def fz115_pdf_from_scenario(scenario_id: str):
    data = await build_fz115_from_scenario(scenario_id)
    html = render_fz115_html(data)
    content, media_type = render_pdf_bytes(html)
    filename = f"{data.get('report_id', 'fz115')}.pdf"
    if media_type.startswith("text/html"):
        filename = filename.replace(".pdf", ".html")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
