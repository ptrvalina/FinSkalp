"""
Операционный центр регулятора — локальный боевой прототип.
"""

from __future__ import annotations

import asyncio
import html
import json
import os
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from flowsint_crypto_compliance.attribution import AttributionEngine
from flowsint_crypto_compliance.demo.demo_context import (
    get_demo_chain_adapters,
    get_demo_label_cache,
    preload_kyt_samples,
    seed_demo_registry,
)
from flowsint_crypto_compliance.demo.compliance_api import router as compliance_demo_router
from flowsint_crypto_compliance.demo.instrument_runner import CAPABILITY_TAG, InstrumentRunner
from flowsint_crypto_compliance.demo.national_scale import (
    build_live_dashboard,
    cis_coverage,
    get_dashboard,
    list_banks,
    list_exchangers,
    live_feed_event,
)
from flowsint_crypto_compliance.demo.live_ops_metrics import get_live_ops_metrics
from flowsint_crypto_compliance.demo.microservices import (
    get_mesh_topology,
    list_microservices,
    run_microservice,
)
from flowsint_crypto_compliance.demo.enterprise_platform import (
    MODULE_BY_IC,
    get_platform_overview,
    list_platform_modules,
)
from flowsint_crypto_compliance.demo.osint_console import OSINTConsole
from flowsint_crypto_compliance.demo.security_hardening import (
    DemoRateLimitMiddleware,
    assert_demo_api_token,
    assert_upload_size,
    cors_origins_from_env,
    demo_bind_host,
    sanitize_filename,
    sanitize_username,
    validate_case_ref,
    validate_evidence_hash,
    validate_upload_magic,
)
from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine
from flowsint_crypto_compliance.reporting.ocr_pipeline import OCRPipeline
from flowsint_crypto_compliance.demo.combat_mode import combat_seed_address, is_combat_mode
from flowsint_crypto_compliance.demo.combat_investigation import CombatInvestigationPipeline
from flowsint_crypto_compliance.demo.operations_center import OperationsCenter
from flowsint_crypto_compliance.demo.runner import RegulatorDemoRunner
from flowsint_crypto_compliance.demo.scenarios import get_scenario, list_scenarios
from flowsint_crypto_compliance.reporting.finskalp_report import FinSkalpReportBuilder
from flowsint_crypto_compliance.reporting.fz115_report import FZ115ReportBuilder
from flowsint_crypto_compliance.observability.middleware import CorrelationIdMiddleware
from flowsint_crypto_compliance.observability.tracing import (
    celery_dispatch_kwargs,
    instrument_fastapi,
    shutdown_tracing,
)
from flowsint_crypto_compliance.reporting.pdf_report import render_fz115_html, render_pdf_bytes
from flowsint_crypto_compliance.services.finskalp_investigator import (
    FinSkalpInvestigationRequest,
    FinSkalpInvestigator,
)
from flowsint_crypto_compliance.services.wallet_screening import (
    WalletScreeningRequest,
    WalletScreeningService,
    infer_chain,
)
from flowsint_types.fiat_crypto import Chain

from flowsint_crypto_compliance.chains import get_chain_adapter

from flowsint_crypto_compliance.config.env_loader import load_project_env

load_project_env()

STATIC_DIR = Path(__file__).resolve().parent / "static"

center = OperationsCenter()
instrument_runner = InstrumentRunner(center)
pipeline = CombatInvestigationPipeline()
_fz115 = FZ115ReportBuilder()
_osint = OSINTConsole()
_finskalp = FinSkalpInvestigator()
_finskalp_store: dict[str, dict] = {}
_finskalp_reporter = FinSkalpReportBuilder()
_scalpel_engine = ScalpelEngine()
_ocr_pipeline = OCRPipeline()
_bg_task: asyncio.Task | None = None
_investigate_tasks: dict[str, dict[str, Any]] = {}

_DEFAULT_FUSION_SCENARIO = "p2p_rub_offshore"


def _investigate_timeout_sec() -> float:
    raw = os.getenv("COMPLIANCE_INVESTIGATE_TIMEOUT_SEC", "").strip()
    if raw:
        return float(raw)
    return 900.0 if is_combat_mode() else 300.0


_INVESTIGATE_TIMEOUT_SEC = _investigate_timeout_sec()


def _resolve_scenario_id(scenario_id: str | None) -> str:
    sid = (scenario_id or "").strip()
    return sid or _DEFAULT_FUSION_SCENARIO


def _cache_finskalp_payload(payload: dict[str, Any]) -> None:
    inv_id = payload.get("investigation_id")
    if inv_id:
        _finskalp_store[str(inv_id)] = payload


async def _resolve_finskalp_payload(
    investigation_id: str | None = None,
    *,
    alert_id: str | None = None,
) -> dict[str, Any]:
    """Lookup investigation payload from memory cache or completed case report."""
    if investigation_id:
        cached = _finskalp_store.get(investigation_id)
        if cached:
            return cached

    if alert_id:
        try:
            alert = await center.get_alert(alert_id)
        except KeyError:
            alert = None
        if alert:
            report = alert.get("report") or {}
            inv = report.get("investigation_id") or investigation_id
            if inv:
                cached = _finskalp_store.get(str(inv))
                if cached:
                    return cached
            forensic = report.get("forensic_report") or {}
            if forensic.get("address_profile"):
                return {
                    "investigation_id": inv or forensic.get("report_id") or alert_id,
                    "forensic_report": forensic,
                    "address_report": {},
                    "volumetric_report": report.get("volumetric_report") or {},
                    "sar_report": report.get("sar_report") or {},
                    "seizure_report": report.get("seizure_report") or {},
                    "case_ref": report.get("case_ref") or alert.get("case_ref"),
                }

    if investigation_id:
        try:
            inbox = await center.list_inbox()
        except Exception:
            inbox = []
        for alert in inbox:
            report = (alert or {}).get("report") or {}
            if report.get("investigation_id") == investigation_id:
                forensic = report.get("forensic_report") or {}
                if forensic.get("address_profile"):
                    payload = {
                        "investigation_id": investigation_id,
                        "forensic_report": forensic,
                        "address_report": report.get("address_report") or {},
                        "volumetric_report": report.get("volumetric_report") or {},
                        "sar_report": report.get("sar_report") or {},
                        "seizure_report": report.get("seizure_report") or {},
                        "case_ref": report.get("case_ref") or alert.get("case_ref"),
                    }
                    _cache_finskalp_payload(payload)
                    return payload

    raise HTTPException(
        status_code=404,
        detail=(
            "Расследование не найдено. Запустите расследование заново "
            "(кэш сбрасывается при перезапуске стенда)."
        ),
    )


def _select_finskalp_report(stored: dict[str, Any], report_type: str) -> dict[str, Any]:
    if report_type == "forensic":
        report = stored.get("forensic_report")
        if not report or not report.get("address_profile"):
            raise HTTPException(
                status_code=404,
                detail="Forensic-отчёт ещё не сформирован для этого расследования",
            )
        return report
    if report_type == "volumetric":
        report = stored.get("volumetric_report") or {}
        if not report.get("sections"):
            raise HTTPException(
                status_code=404,
                detail="Объёмный отчёт ещё не сформирован для этого расследования",
            )
        return report
    if report_type == "sar":
        report = stored.get("sar_report") or {}
        if not report.get("evidence_sections"):
            raise HTTPException(
                status_code=404,
                detail="SAR-отчёт ещё не сформирован для этого расследования",
            )
        return report
    if report_type == "seizure":
        return stored.get("seizure_report") or {}
    if report_type == "transaction":
        tx = (stored.get("forensic_report") or {}).get("tx_hash") or ""
        forensic = stored.get("forensic_report") or {}
        return _finskalp_reporter.build_transaction_report(forensic, tx or "—")
    report = stored.get("address_report")
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт скрининга не найден")
    return report


def _render_finskalp_attachment(report: dict[str, Any], report_type: str, investigation_id: str) -> Response:
    try:
        content, media, ext = _finskalp_reporter.render_pdf(report)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Ошибка рендеринга отчёта ({report_type}): {exc}",
        ) from exc
    filename = f"finskalp_{report_type}_{investigation_id[:8]}.{ext}"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _bootstrap_live_ops() -> None:
    """Seed inbox and feed with first live KYT / STR pass after stand boots."""
    await asyncio.sleep(2.0)
    try:
        await center.bootstrap_live_queue()
    except Exception:
        pass


async def _warmup_finskalp() -> None:
    """Прогрев XGBoost/пайплайна — первый запрос пользователя не висит минуту."""
    try:
        await asyncio.wait_for(
            _finskalp.investigate(
                FinSkalpInvestigationRequest(address="TRU_HUB_MSK", chain=Chain.TRON)
            ),
            timeout=30.0,
        )
    except Exception:
        pass


async def _auto_pattern_monitor() -> None:
    interval = int(os.getenv("COMPLIANCE_DEMO_AUTO_SCAN_SEC", "45"))
    await asyncio.sleep(8)
    while True:
        await center.run_pattern_scan()
        await asyncio.sleep(interval)


async def _finalize_investigation(
    alert_id: str,
    steps: list[dict],
    report: dict,
) -> dict:
    cache = report.pop("_finskalp_cache", None)
    if cache:
        _cache_finskalp_payload(cache)
    elif report.get("investigation_id") and (report.get("forensic_report") or {}).get("address_profile"):
        _cache_finskalp_payload(
            {
                "investigation_id": report["investigation_id"],
                "forensic_report": report["forensic_report"],
                "address_report": report.get("address_report") or {},
                "volumetric_report": report.get("volumetric_report") or {},
                "sar_report": report.get("sar_report") or {},
                "seizure_report": report.get("seizure_report") or {},
                "case_ref": report.get("case_ref"),
            }
        )
    alert = await center.get_alert(alert_id)
    fz115 = _fz115.build(alert=alert, investigation_report=report).to_dict()
    await center.update_alert(
        alert_id,
        status="completed",
        report=report,
        fz115_report=fz115,
        steps=steps,
        workflow_status="pending_filing",
    )
    try:
        from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

        get_event_bus().publish(
            "case_investigation_done",
            payload={
                "alert_id": alert_id,
                "alert_code": alert.get("alert_code"),
                "case_ref": alert.get("case_ref"),
            },
            text_ru=(
                f"Расследование завершено · {alert.get('alert_code')} · "
                f"риск {str(report.get('risk_level', '—')).upper()} · граф готов"
            ),
            severity="critical" if report.get("risk_level") == "critical" else "high",
            correlation_id=alert.get("case_ref"),
        )
    except Exception:
        pass
    return fz115


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bg_task
    from flowsint_crypto_compliance.demo.combat_mode import apply_combat_env_defaults
    from flowsint_crypto_compliance.osint.collector_health import (
        start_collector_health_daemon,
        stop_collector_health_daemon,
    )
    from flowsint_crypto_compliance.platform.v2.entity_store_mode import warn_if_memory_store_in_production
    from flowsint_crypto_compliance.platform.v2.integration import bootstrap_platform_v2

    apply_combat_env_defaults()
    await bootstrap_platform_v2()
    warn_if_memory_store_in_production()

    seed_demo_registry()
    preload_kyt_samples()
    asyncio.create_task(AttributionEngine(label_cache=get_demo_label_cache()).ensure_bootstrap())
    asyncio.create_task(_warmup_finskalp())
    await start_collector_health_daemon()
    if is_combat_mode():
        asyncio.create_task(_bootstrap_live_ops())
    if os.getenv("COMPLIANCE_DEMO_AUTO_SCAN", "1") == "1":
        _bg_task = asyncio.create_task(_auto_pattern_monitor())
    yield
    await stop_collector_health_daemon()
    if _bg_task:
        _bg_task.cancel()
        try:
            await _bg_task
        except asyncio.CancelledError:
            pass
    shutdown_tracing()


app = FastAPI(
    title="Flowsint Compliance — Операционный центр",
    description="Боевой прототип ПОД/ФТ: STR, паттерны, OSINT, отчёты 115-ФЗ",
    version="0.6.0",
    lifespan=lifespan,
)
instrument_fastapi(app)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_from_env(),
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Correlation-ID", "X-Analyst-Id", "X-Analyst-Role"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    _CSP_CLASSIC = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.bunny.net; "
        "font-src 'self' https://fonts.bunny.net; "
        "img-src 'self' data:; connect-src 'self'"
    )
    _CSP_ENTERPRISE = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.bunny.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.bunny.net https://fonts.gstatic.com data:; "
        "img-src 'self' data: https://lh3.googleusercontent.com https://*.googleusercontent.com; "
        "connect-src 'self'"
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if os.getenv("COMPLIANCE_DEMO_HSTS", "0") == "1":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        path = request.url.path
        csp = self._CSP_ENTERPRISE if path in ("/", "/classic") else self._CSP_CLASSIC
        response.headers["Content-Security-Policy"] = csp
        return response


# RFC-0002 M3: mark legacy demo routes deprecated in favor of canonical /api/platform/v2/*
_DEPRECATED_ROUTE_SUCCESSORS: dict[str, str] = {
    "/api/finskalp/investigate": "/api/platform/v2/investigate",
    "/api/osint/investigate": "/api/platform/v2/investigate",
    "/api/scalpel/collect": "/api/platform/v2/scalpel/collect",
    "/api/scalpel/collect/async": "/api/platform/v2/scalpel/collect",
    "/api/compliance/attribution/confirm": "/api/platform/v2/attribution/confirm",
    "/api/compliance/attribution/reject": "/api/platform/v2/attribution/reject",
    "/api/wallet/screen": "/api/compliance/wallets/screen",
}


class PlatformDeprecationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        successor = _DEPRECATED_ROUTE_SUCCESSORS.get(request.url.path)
        if successor:
            response.headers["Deprecation"] = "true"
            response.headers["Link"] = f'<{successor}>; rel="successor-version"'
            response.headers["X-Platform-V2-Canonical"] = successor
        return response


app.add_middleware(PlatformDeprecationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(DemoRateLimitMiddleware)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(compliance_demo_router, prefix="/api/compliance")

from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

app.include_router(
    create_platform_v2_router(demo_api_token_guard=assert_demo_api_token),
    prefix="/api/platform/v2",
    tags=["platform-v2"],
)


def _demo_wallet_service() -> WalletScreeningService:
    cache = get_demo_label_cache()
    if is_combat_mode():
        return WalletScreeningService(
            chain_adapters={
                Chain.TRON: get_chain_adapter(Chain.TRON),
                Chain.ETH: get_chain_adapter(Chain.ETH),
                Chain.BTC: get_chain_adapter(Chain.BTC),
            },
            label_cache=cache,
        )
    return WalletScreeningService(
        chain_adapters=get_demo_chain_adapters(),
        label_cache=cache,
    )


class BankStrRequest(BaseModel):
    scenario_id: str | None = Field(None, description="Контекст типологии (метаданные STR, не синтетический граф)")
    crypto_address: str | None = Field(None, min_length=10, max_length=128, description="Live криптоадрес из СОО")
    crypto_chain: str | None = Field(None, description="tron | eth | btc")


class WorkflowTransitionBody(BaseModel):
    workflow_status: str = Field(..., description="new|triage|investigating|pending_filing|filed|archived")
    assignee: str | None = None
    note: str | None = None


class CaseCommentBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    author: str | None = None


class WalletScreenRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=128)
    chain: str | None = Field(None, description="btc | eth | tron; пусто = авто")
    depth: int = Field(1, ge=1, le=2)
    limit: int = Field(50, ge=1, le=100)


class KytWatchlistRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=128)


_NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


@app.get("/", response_class=HTMLResponse)
async def index():
    """FinSkalp enterprise UI + full live SPA."""
    return HTMLResponse(
        (STATIC_DIR / "index.html").read_text(encoding="utf-8"),
        headers=_NO_STORE_HEADERS,
    )


@app.get("/classic", response_class=HTMLResponse)
async def classic_demo():
    """Classic layout (pre-enterprise shell)."""
    classic = STATIC_DIR / "index.classic.html"
    if classic.is_file():
        return HTMLResponse(classic.read_text(encoding="utf-8"), headers=_NO_STORE_HEADERS)
    return HTMLResponse(
        (STATIC_DIR / "index.html").read_text(encoding="utf-8"),
        headers=_NO_STORE_HEADERS,
    )


@app.get("/status", response_class=HTMLResponse)
async def public_status_page():
    """Public transparency dashboard — live session metrics, not synthetic KPIs."""
    m = get_live_ops_metrics().snapshot()
    from flowsint_crypto_compliance.osint_core.live_collector_registry import list_live_collectors
    from flowsint_crypto_compliance.demo.live_kyt_scanner import list_kyt_watch_addresses

    collectors = list_live_collectors()
    watch = list_kyt_watch_addresses()
    uptime_h = round(int(m.get("uptime_sec") or 0) / 3600, 2)
    inv_count = int(m.get("investigations") or 0)
    avg_inv = m.get("avg_decision_ms")
    avg_inv_s = f"{int(avg_inv)}ms" if avg_inv is not None else "—"
    screened = int(m.get("wallet_screens") or 0)
    rows = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td><strong>{html.escape(str(v))}</strong></td></tr>"
        for k, v in m.items()
    )
    hero = (
        f"<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin:1rem 0'>"
        f"<div><div class='muted'>Uptime</div><strong>{uptime_h} h</strong></div>"
        f"<div><div class='muted'>Расследований</div><strong>{inv_count}</strong></div>"
        f"<div><div class='muted'>Ср. время расслед.</div><strong>{avg_inv_s}</strong></div>"
        f"<div><div class='muted'>Скринингов</div><strong>{screened}</strong></div>"
        f"<div><div class='muted'>KYT watchlist</div><strong>{len(watch)}</strong></div>"
        f"<div><div class='muted'>Combat</div><strong>{is_combat_mode()}</strong></div>"
        f"</div>"
    )
    coll_rows = "".join(
        f"<li>{html.escape(c['name_ru'])} · {html.escape(c.get('chain') or '—')}</li>" for c in collectors
    )
    return HTMLResponse(
        f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"/>
        <title>FinSkalp · System Status</title>
        <style>body{{font-family:system-ui;background:#0f172a;color:#e2e8f0;padding:2rem;max-width:720px;margin:auto}}
        h1{{font-size:1.4rem}} table{{width:100%;border-collapse:collapse;margin:1rem 0}}
        td{{padding:0.4rem 0;border-bottom:1px solid #334155}} .muted{{color:#94a3b8;font-size:0.85rem}}</style></head>
        <body><h1>FinSkalp · Live Status</h1>
        <p class="muted">Реальные метрики текущей сессии стенда · не витринные числа</p>
        {hero}
        <table>{rows}</table>
        <h2>Live collectors ({len(collectors)})</h2><ul>{coll_rows}</ul>
        <h2>KYT watchlist ({len(watch)})</h2>
        <p class="muted">{", ".join(html.escape(a[:16]+"…" if len(a)>18 else a) for a in watch[:8]) or "—"}</p>
        <p class="muted">Uptime: {uptime_h} h · combat_mode={is_combat_mode()}</p>
        </body></html>"""
    )


@app.get("/api/health/live")
async def health_live():
    """Liveness probe — always fast, no I/O."""
    return {"status": "ok", "service": "flowsint-compliance-ops-center"}


@app.get("/api/health/ready")
async def health_ready():
    """Readiness probe — cached collector snapshot, no live pings."""
    from flowsint_crypto_compliance.osint.collector_health import get_collector_health_snapshot

    collectors = get_collector_health_snapshot()
    overall = "ok" if collectors.get("status") in ("ok", "warming") else "degraded"
    return {
        "status": overall,
        "service": "flowsint-compliance-ops-center",
        "osint_collectors": collectors,
    }


@app.get("/api/health")
async def health():
    """Operational health — non-blocking; collector pings run in background only."""
    from flowsint_crypto_compliance.attribution.postgres_entity_store import entity_store_mode
    from flowsint_crypto_compliance.osint.collector_health import get_collector_health_snapshot

    collectors = get_collector_health_snapshot()
    overall = "ok" if collectors.get("status") in ("ok", "warming") else "degraded"
    return {
        "status": overall,
        "service": "flowsint-compliance-ops-center",
        "mode": "combat_prototype" if is_combat_mode() else "demo_prototype",
        "combat_mode": is_combat_mode(),
        "storage": entity_store_mode(),
        "entity_store": entity_store_mode(),
        "version": "0.8.0-osint-quality",
        "platform": "flowsint_compliance",
        "investigate_timeout_sec": _investigate_timeout_sec(),
        "osint_collectors": collectors,
    }


@app.get("/api/search")
async def global_search(q: str = Query(..., min_length=1, max_length=200), limit: int = Query(20, ge=1, le=50)):
    """Full-text search: cases, wallets, VASP (Meilisearch with Postgres fallback)."""
    from flowsint_crypto_compliance.search.meilisearch_client import get_search_client, search_postgres_fallback

    client = get_search_client()
    hits = client.search(q, limit=limit) if client.available else []
    backend = "meilisearch" if hits else "postgres"
    if not hits:
        hits = search_postgres_fallback(q, limit=limit)
    return {"query": q, "hits": hits, "count": len(hits), "backend": backend}


@app.get("/api/compliance/attribution/eval")
async def attribution_eval_report(engine_version: str = "1.0"):
    """Attribution evaluation report (Evidently + precision/recall deploy gate)."""
    from flowsint_crypto_compliance.ml.attribution_eval import run_attribution_evaluation

    return await run_attribution_evaluation(engine_version=engine_version)


@app.get("/api/infra/tron-node")
async def tron_node_infra():
    from flowsint_crypto_compliance.chains.on_chain_provider import tron_infra_status

    return await tron_infra_status()


@app.get("/api/server-info")
async def server_info():
    port = int(os.getenv("COMPLIANCE_DEMO_PORT", "8877"))
    return {
        "port": port,
        "local_url": f"http://localhost:{port}",
        "lan_url": f"http://{_lan_ip()}:{port}",
        "organization_ru": "ФинСкальп · FinSkalp — суверенная криптофорензика · 115-ФЗ",
        "product": "FinSkalp",
        "product_ru": "ФинСкальп",
        "tagline_ru": "Точный срез финансовых потоков",
    }


@app.get("/api/platform")
async def platform_overview():
    overview = get_platform_overview()
    overview["dashboard"] = get_dashboard()
    return overview


@app.get("/api/platform/modules")
async def platform_modules():
    return list_platform_modules()


@app.get("/api/instruments")
async def instruments():
    items = list_instruments()
    for item in items:
        mod = MODULE_BY_IC.get(item["code"])
        if mod:
            item["platform_code"] = mod.code
            item["name_ru_module"] = mod.name_ru
            item["capability_tag_ru"] = mod.capability_tag_ru
            item["suite_ru"] = mod.suite_ru
            item["capabilities_ru"] = mod.capabilities_ru
            item["sla_pct"] = mod.sla_pct
        item["capability_ru"] = CAPABILITY_TAG.get(item["code"], "")
    return items


@app.get("/api/microservices")
async def microservices_list():
    return list_microservices()


@app.get("/api/microservices/mesh")
async def microservices_mesh():
    return get_mesh_topology()


class MicroserviceRunRequest(BaseModel):
    scenario_id: str | None = Field(None, description="Демо-сценарий для OSINT/microservice run")


@app.post("/api/microservices/{service_id}/run")
async def microservice_run(
    service_id: str,
    body: MicroserviceRunRequest | None = None,
    scenario_id: str | None = None,
):
    sid = (body.scenario_id if body and body.scenario_id else None) or scenario_id or "p2p_rub_offshore"
    try:
        get_scenario(sid)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown scenario: {sid}") from exc
    try:
        return await run_microservice(service_id, scenario_id=sid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/osint/status")
async def osint_status():
    return _osint.status()


@app.get("/api/osint/sources")
async def osint_sources():
    return _osint.sources()


@app.get("/api/osint/pipeline")
async def osint_pipeline():
    return _osint.pipeline()


class FinSkalpInvestigateRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=128, description="Криптоадрес")
    chain: str | None = Field(None, description="tron | eth | btc")
    tx_hash: str | None = Field(None, max_length=128)
    bank_reference: str | None = Field(None, max_length=128)
    bank_name: str | None = Field(None, max_length=256)
    subject_id: str | None = Field(None, max_length=64)
    amount: float | None = None
    currency: str | None = Field(None, max_length=8)
    region: str = Field("RU", max_length=8)
    notes: str | None = Field(None, max_length=2000)
    scenario_id: str | None = None
    depth: int = Field(2, ge=1, le=3, description="On-chain глубина скрининга")
    osint_depth: int = Field(2, ge=1, le=3, description="OSINT разветка: 1=адрес, 2=+контрагенты, 3=+2-й hop")
    limit: int = Field(50, ge=1, le=100)
    collectors: list[str] | None = Field(
        None,
        description="ID коллекторов Scalpel; пусто = все 8",
    )


def _build_investigation_request(body: FinSkalpInvestigateRequest) -> tuple[FinSkalpInvestigationRequest, Chain | None]:
    try:
        chain = Chain(body.chain.lower()) if body.chain else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Неподдерживаемая сеть") from exc
    if body.scenario_id:
        try:
            get_scenario(body.scenario_id)
        except KeyError as exc:
            raise HTTPException(status_code=422, detail=f"Unknown scenario: {body.scenario_id}") from exc
    req = FinSkalpInvestigationRequest(
        address=body.address.strip(),
        chain=chain,
        tx_hash=body.tx_hash,
        bank_reference=body.bank_reference,
        bank_name=body.bank_name,
        subject_id=body.subject_id,
        amount=body.amount,
        currency=body.currency,
        region=body.region,
        notes=body.notes,
        scenario_id=body.scenario_id,
        depth=body.depth,
        osint_depth=body.osint_depth,
        limit=body.limit,
        collectors=body.collectors,
    )
    return req, chain


def _finalize_finskalp_payload(payload: dict[str, Any]) -> dict[str, Any]:
    _cache_finskalp_payload(payload)
    try:
        from flowsint_crypto_compliance.search.meilisearch_client import index_case, index_wallet

        index_case(str(payload.get("case_ref") or ""), workflow_status="investigating")
        index_wallet(payload.get("chain", "tron"), payload.get("address", ""), risk_score=payload.get("risk_score"))
    except Exception:
        pass
    if is_combat_mode():
        live = payload.get("live_fusion") or {}
        nodes = int(live.get("node_count") or len(live.get("nodes") or []))
        edges = int(live.get("edge_count") or len(live.get("edges") or []))
        get_live_ops_metrics().record_investigation(
            duration_ms=int(payload.get("duration_ms") or 0),
            graph_nodes=nodes,
            graph_edges=edges,
        )
    try:
        from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

        score = float(payload.get("risk_score") or 0)
        get_event_bus().publish(
            "investigation_completed",
            payload={
                "case_ref": payload.get("case_ref"),
                "address": payload.get("address"),
                "risk_score": score,
            },
            severity="critical" if score >= 85 else "high" if score >= 65 else "info",
            correlation_id=payload.get("case_ref"),
        )
    except Exception:
        pass
    return payload


async def _run_finskalp_investigate_core(
    body: FinSkalpInvestigateRequest,
    *,
    correlation_id: str | None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.observability.logging import correlation_id_var

    req, _chain = _build_investigation_request(body)
    cid = correlation_id or correlation_id_var.get()
    result = await asyncio.wait_for(
        _finskalp.investigate(req, correlation_id=cid),
        timeout=_investigate_timeout_sec(),
    )
    return _finalize_finskalp_payload(result.to_dict())


async def _run_investigate_task(task_id: str, body: FinSkalpInvestigateRequest, correlation_id: str | None) -> None:
    _investigate_tasks[task_id]["status"] = "running"
    try:
        payload = await _run_finskalp_investigate_core(body, correlation_id=correlation_id)
        _investigate_tasks[task_id].update(
            {
                "status": "success",
                "result": payload,
                "error": None,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except asyncio.TimeoutError:
        hint = (
            "Укажите live-адрес (TRON/ETH/BTC) и повторите."
            if is_combat_mode()
            else "Попробуйте демо-адрес TRU_HUB_MSK или повторите позже."
        )
        _investigate_tasks[task_id].update(
            {
                "status": "failure",
                "error": f"Расследование превысило лимит времени ({int(_investigate_timeout_sec())} с). {hint}",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except ValueError as exc:
        _investigate_tasks[task_id].update(
            {
                "status": "failure",
                "error": str(exc),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:
        _investigate_tasks[task_id].update(
            {
                "status": "failure",
                "error": str(exc)[:2000],
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )


@app.get("/api/scenarios")
async def scenarios_list():
    return list_scenarios()


@app.post("/api/finskalp/investigate")
@app.post("/api/osint/investigate")
async def finskalp_investigate(body: FinSkalpInvestigateRequest, request: Request):
    assert_demo_api_token(request)
    from flowsint_crypto_compliance.observability.logging import correlation_id_var

    try:
        return await _run_finskalp_investigate_core(
            body,
            correlation_id=correlation_id_var.get() or request.headers.get("X-Correlation-ID"),
        )
    except asyncio.TimeoutError as exc:
        hint = (
            "Укажите live-адрес (TRON/ETH/BTC) и повторите."
            if is_combat_mode()
            else "Попробуйте демо-адрес TRU_HUB_MSK или повторите позже."
        )
        raise HTTPException(
            status_code=504,
            detail=f"Расследование превысило лимит времени. {hint}",
        ) from exc
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/finskalp/investigate/async")
@app.post("/api/osint/investigate/async")
async def finskalp_investigate_async(body: FinSkalpInvestigateRequest, request: Request):
    """Фоновое расследование — для live TRON + все Scalpel-коллекторы (5–15 мин)."""
    assert_demo_api_token(request)
    from flowsint_crypto_compliance.observability.logging import correlation_id_var

    try:
        _build_investigation_request(body)
    except HTTPException:
        raise
    task_id = str(uuid.uuid4())
    _investigate_tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "result": None,
        "error": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "timeout_sec": _investigate_timeout_sec(),
    }
    correlation_id = correlation_id_var.get() or request.headers.get("X-Correlation-ID")
    asyncio.create_task(_run_investigate_task(task_id, body, correlation_id))
    return {
        "task_id": task_id,
        "status": "queued",
        "poll_url": f"/api/finskalp/investigate/tasks/{task_id}",
        "timeout_sec": _investigate_timeout_sec(),
    }


@app.get("/api/finskalp/investigate/tasks/{task_id}")
async def finskalp_investigate_task_poll(task_id: str):
    task = _investigate_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача расследования не найдена")
    return task


@app.get("/api/finskalp/report/{investigation_id}/pdf")
async def finskalp_report_pdf(investigation_id: str, type: str = "address", alert_id: str | None = None):
    stored = await _resolve_finskalp_payload(investigation_id, alert_id=alert_id)
    report = _select_finskalp_report(stored, type)
    return _render_finskalp_attachment(report, type, investigation_id)


@app.get("/api/finskalp/report/{investigation_id}/html")
async def finskalp_report_html(investigation_id: str, type: str = "address", alert_id: str | None = None):
    stored = await _resolve_finskalp_payload(investigation_id, alert_id=alert_id)
    report = _select_finskalp_report(stored, type)
    try:
        html = _finskalp_reporter.render_html(report)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Ошибка рендеринга отчёта ({type}): {exc}",
        ) from exc
    return HTMLResponse(html)


@app.post("/api/kyt/import")
async def kyt_import(file: UploadFile = File(...)):
    """MetaSleuth / BlockSec / CSV / XLSX → labels + exposure в кэш FinSkalp."""
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


class OSINTFusionRequest(BaseModel):
    scenario_id: str | None = Field(None, description="Демо-сценарий для fusion")


@app.post("/api/osint/fusion")
async def osint_fusion(body: OSINTFusionRequest | None = None):
    if is_combat_mode():
        raise HTTPException(
            status_code=422,
            detail=(
                "В live-режиме fusion только по адресу: "
                "OSINT → «Полный цикл расследования» или /api/finskalp/investigate"
            ),
        )
    sid = _resolve_scenario_id(body.scenario_id if body else None)
    try:
        get_scenario(sid)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown scenario: {sid}") from exc
    try:
        return await asyncio.wait_for(_osint.run_fusion(sid), timeout=30.0)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="OSINT Fusion превысил лимит времени") from exc


@app.get("/api/v1/score/{address}")
async def quick_risk_score(address: str, chain: str | None = None):
    """Lightweight risk score API (<500ms target) — separate from full investigation."""
    try:
        ch = Chain(chain.lower()) if chain else infer_chain(address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Неподдерживаемая сеть") from exc
    t0 = asyncio.get_event_loop().time()
    try:
        result = await asyncio.wait_for(
            _demo_wallet_service().screen(
                WalletScreeningRequest(address=address, chain=ch, depth=0, limit=20)
            ),
            timeout=0.45,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Score timeout") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    elapsed_ms = int((asyncio.get_event_loop().time() - t0) * 1000)
    return {
        "address": address,
        "chain": ch.value,
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "summary_ru": result.summary_ru,
        "latency_ms": elapsed_ms,
        "api": "v1/score",
    }


@app.post("/api/wallet/screen")
async def wallet_screen(body: WalletScreenRequest):
    try:
        chain = Chain(body.chain.lower()) if body.chain else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Неподдерживаемая сеть") from exc
    try:
        result = await _demo_wallet_service().screen(
            WalletScreeningRequest(
                address=body.address,
                chain=chain,
                depth=body.depth,
                limit=body.limit,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = result.model_dump(mode="json")
    if is_combat_mode():
        from flowsint_crypto_compliance.demo.live_feed import publish_screening_feed

        get_live_ops_metrics().record_screen(
            risk_score=float(payload.get("risk_score") or 0),
            address=body.address,
        )
        publish_screening_feed(
            address=body.address,
            chain=(chain or infer_chain(body.address)).value,
            risk_score=float(payload.get("risk_score") or 0),
            summary_ru=payload.get("summary_ru"),
        )
    return payload


@app.get("/api/dashboard")
async def dashboard():
    ops = await center.stats()
    wf = await center.workflow_stats()
    if is_combat_mode():
        merged = build_live_dashboard(
            ops_stats=ops,
            workflow_stats=wf,
            metrics=get_live_ops_metrics().snapshot(),
        )
        merged["ops_queue"] = ops
        merged["workflow_sla_breached"] = wf.get("sla_breached", 0)
        return merged
    try:
        from flowsint_crypto_compliance.infrastructure.read_models import ComplianceDashboardReadModel

        dash = ComplianceDashboardReadModel(None).get()
    except Exception:
        dash = get_dashboard()
    merged = {**dash, "ops_queue": ops}
    if "case_pipeline" not in merged or not isinstance(merged.get("case_pipeline"), dict):
        merged["case_pipeline"] = wf["pipeline"]
    else:
        pipe = dict(merged["case_pipeline"])
        for key, val in wf["pipeline"].items():
            if key in pipe and isinstance(pipe[key], int) and val:
                pipe[key] = max(pipe[key], val)
        merged["case_pipeline"] = pipe
    merged["workflow_sla_breached"] = wf.get("sla_breached", 0)
    return merged


@app.get("/api/scalpel/status")
async def scalpel_status():
    from flowsint_crypto_compliance.osint_core.scalpel.workers.maigret_runner import (
        maigret_available,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.workers.spiderfoot_runner import (
        spiderfoot_available,
    )
    from flowsint_crypto_compliance.reporting.ocr_pipeline import _paddle_available

    from flowsint_crypto_compliance.osint_core.scalpel.api_cache import cache_stats
    from flowsint_crypto_compliance.osint_core.scalpel.rate_limit import rate_limit_status

    tor_probe = await _scalpel_engine._gw.probe_tor()
    return {
        **_scalpel_engine.status(),
        "tor_probe": tor_probe,
        "maigret_cli": maigret_available(),
        "spiderfoot_cli": spiderfoot_available(),
        "paddleocr": _paddle_available(),
        "api_cache": cache_stats(),
        "rate_limits": rate_limit_status(),
    }


class ScalpelCollectBody(BaseModel):
    address: str
    chain: str = "tron"
    depth: int = Field(2, ge=1, le=3, description="OSINT разветка")
    onchain_depth: int | None = Field(None, ge=1, le=3, description="Глубина on-chain для контрагентов")
    counterparties: list[str] = Field(default_factory=list)
    usernames: list[str] = Field(default_factory=list)
    collectors: list[str] | None = Field(None, description="Подмножество коллекторов Scalpel")


class MaigretBody(BaseModel):
    username: str
    top_sites: int = 120
    use_tor: bool = False


@app.get("/api/scalpel/collectors")
async def scalpel_collectors():
    from flowsint_crypto_compliance.config.env_loader import trongrid_key_configured
    from flowsint_crypto_compliance.osint_core.scalpel.registry import registry_manifest

    tor_probe = await _scalpel_engine._gw.probe_tor()
    tor_ok = _scalpel_engine._gw.config.tor_enabled() or bool(
        tor_probe.get("ok") or tor_probe.get("reachable")
    )
    return {
        "collectors": registry_manifest(
            tor_available=tor_ok,
            trongrid_configured=trongrid_key_configured(),
        ),
        "tor_probe": tor_probe,
        "osint_depth_labels": {
            "1": "Только целевой адрес",
            "2": "Адрес + 1-hop контрагенты (on-chain)",
            "3": "2-hop: контрагенты + адреса из сущностей OSINT",
        },
    }


@app.post("/api/scalpel/collect")
async def scalpel_collect(body: ScalpelCollectBody):
    try:
        chain = Chain(body.chain.lower())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Неподдерживаемая сеть") from exc
    cps = list(body.counterparties)
    onchain_depth = body.onchain_depth if body.onchain_depth is not None else body.depth
    if body.depth >= 2 and not cps:
        try:
            screening = await _demo_wallet_service().screen(
                WalletScreeningRequest(
                    address=body.address.strip(),
                    chain=chain,
                    depth=onchain_depth,
                    limit=50,
                )
            )
            summary = screening.onchain_summary or {}
            cps = list(summary.get("counterparty_addresses") or [])[:12]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        result = await asyncio.wait_for(
            _scalpel_engine.collect(
                body.address.strip(),
                chain,
                counterparties=cps or None,
                depth=body.depth,
                collectors=body.collectors,
                usernames=body.usernames or None,
            ),
            timeout=45.0,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Scalpel collect timeout (45s)") from exc
    payload = result.to_dict()
    try:
        import uuid as _uuid

        from flowsint_crypto_compliance.platform.v2.gateway import emit_scalpel_collect_event

        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        extracted = payload.get("extracted_entities") or {}
        mentions = extracted.get("mentions") or payload.get("mentions") or []
        emit_scalpel_collect_event(
            case_ref=None,
            tenant_id=_uuid.UUID(tenant_raw),
            investigation_id=None,
            mentions=mentions if isinstance(mentions, list) else [],
        )
    except Exception:
        pass
    return payload


@app.post("/api/scalpel/collect/async")
async def scalpel_collect_async(body: ScalpelCollectBody):
    try:
        from flowsint_core.core.celery import celery

        task = celery.send_task(
            "run_scalpel_collect",
            kwargs=celery_dispatch_kwargs(body.model_dump()),
        )
        return {"task_id": task.id, "status": "queued"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Celery unavailable: {exc}") from exc


@app.get("/api/scalpel/tasks/{task_id}")
async def scalpel_task_poll(task_id: str):
    try:
        from celery.result import AsyncResult
        from flowsint_core.core.celery import celery

        r = AsyncResult(task_id, app=celery)
        out: dict = {"task_id": task_id, "status": r.status, "result": None, "error": None}
        if r.ready():
            if r.successful():
                out["result"] = r.result
            else:
                out["error"] = str(r.result)[:2000]
        return out
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/scalpel/maigret/async")
async def maigret_async(body: MaigretBody):
    try:
        username = sanitize_username(body.username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        from flowsint_core.core.celery import celery

        task = celery.send_task(
            "run_maigret_scan",
            kwargs={
                "username": username,
                "top_sites": min(body.top_sites, 500),
                "use_tor": body.use_tor,
            },
        )
        return {"task_id": task.id, "status": "queued"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/graph/status")
async def graph_store_status():
    from flowsint_crypto_compliance.storage.graph_store import EvidenceGraphStore

    return EvidenceGraphStore().status()


@app.get("/api/graph/{case_ref}")
async def graph_load(case_ref: str):
    from flowsint_crypto_compliance.storage.graph_store import EvidenceGraphStore

    return EvidenceGraphStore().load(case_ref)


@app.get("/api/graph/export")
async def graph_export(
    format: str = "graphml",
    investigation_id: str | None = None,
    alert_id: str | None = None,
    view: str = "address",
):
    """Export investigation graph as GraphML or JSON."""
    from flowsint_crypto_compliance.reporting.graph_top_tier import graph_to_graphml

    payload = await _resolve_finskalp_payload(investigation_id, alert_id=alert_id)
    graph = payload.get("live_fusion") or payload.get("graph_viz") or {}
    if not graph.get("nodes") and not graph.get("address_view"):
        raise HTTPException(status_code=404, detail="Graph not found for export")

    fmt = format.lower()
    if fmt == "graphml":
        body = graph_to_graphml(graph, view=view)
        return Response(
            content=body,
            media_type="application/xml",
            headers={"Content-Disposition": 'attachment; filename="finskalp_graph.graphml"'},
        )
    if fmt == "json":
        return Response(
            content=json.dumps(graph, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="finskalp_graph.json"'},
        )
    raise HTTPException(status_code=422, detail="format must be graphml or json")


class GraphViewBody(BaseModel):
    name: str
    zoom: float | None = 1.0
    center: dict[str, float] | None = None
    expanded_clusters: list[str] = Field(default_factory=list)
    timeline_ts: int | None = None
    pins: dict[str, Any] = Field(default_factory=dict)
    view_mode: str = "cluster"
    highlighted_path: list[str] | None = None


@app.get("/api/investigations/{investigation_id}/graph/views")
async def list_investigation_graph_views(investigation_id: str):
    """Server-side saved graph camera views (Postgres or in-memory fallback)."""
    from flowsint_crypto_compliance.storage.graph_view_store import list_views

    return {"investigation_id": investigation_id, "views": list_views(investigation_id)}


@app.post("/api/investigations/{investigation_id}/graph/views")
async def save_investigation_graph_view(investigation_id: str, body: GraphViewBody):
    from flowsint_crypto_compliance.storage.graph_view_store import save_view

    try:
        saved = save_view(investigation_id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return saved


@app.delete("/api/investigations/{investigation_id}/graph/views/{view_id}")
async def delete_investigation_graph_view(investigation_id: str, view_id: str):
    from flowsint_crypto_compliance.storage.graph_view_store import delete_view

    if not delete_view(investigation_id, view_id):
        raise HTTPException(status_code=404, detail="Graph view not found")
    return {"deleted": view_id}


# --- Phase 4: followthemoney + GraphSense TagPack interop ---


@app.get("/api/interop/ftm/entity-labels")
async def interop_ftm_export_labels(chain: str | None = None):
    """Export entity labels as FTM ndjson (OpenSanctions-compatible)."""
    from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store
    from flowsint_crypto_compliance.interop.ftm_adapter import export_labels_ftm_ndjson

    store = get_entity_label_store()
    labels = store.all_labels()
    if chain:
        labels = [l for l in labels if l.chain.lower() == chain.lower()]
    body = export_labels_ftm_ndjson(labels)
    return Response(
        content=body,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="finskalp_entity_labels.ftm.json"'},
    )


@app.post("/api/interop/ftm/entity-labels")
async def interop_ftm_import_labels(request: Request):
    """Import FTM ndjson into entity label store."""
    from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store
    from flowsint_crypto_compliance.interop.ftm_adapter import import_labels_from_ftm_ndjson

    raw = await request.body()
    text = raw.decode("utf-8") if raw else ""
    if not text.strip():
        raise HTTPException(status_code=422, detail="Empty ndjson body")
    store = get_entity_label_store()
    return import_labels_from_ftm_ndjson(text, store)


@app.get("/api/interop/ftm/fusion-graph/{investigation_id}")
async def interop_ftm_fusion_graph(
    investigation_id: str,
    format: str = "bundle",
    alert_id: str | None = None,
):
    """Export investigation fusion graph as FTM entity + statement bundle."""
    from flowsint_crypto_compliance.interop.fusion_ftm_export import (
        fusion_graph_to_ftm_bundle,
        fusion_graph_to_ftm_ndjson,
    )

    payload = await _resolve_finskalp_payload(investigation_id, alert_id=alert_id)
    graph = payload.get("live_fusion") or payload.get("graph_viz") or {}
    if not graph.get("nodes") and not graph.get("address_view"):
        raise HTTPException(status_code=404, detail="Graph not found for investigation")

    fmt = format.lower()
    if fmt == "ndjson":
        body = fusion_graph_to_ftm_ndjson(graph)
        return Response(
            content=body,
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": f'attachment; filename="finskalp_{investigation_id}.ftm.json"',
            },
        )
    bundle = fusion_graph_to_ftm_bundle(graph)
    return bundle


@app.get("/api/interop/graphsense/paths")
async def interop_graphsense_paths(
    from_addr: str = Query(..., alias="from"),
    to_addr: str = Query(..., alias="to"),
    investigation_id: str | None = None,
    alert_id: str | None = None,
    max_hops: int = 4,
):
    """GraphSense-style path result on local fusion graph."""
    from flowsint_crypto_compliance.interop.graphsense_paths import graphsense_path_result

    if not from_addr or not to_addr:
        raise HTTPException(status_code=422, detail="Query params 'from' and 'to' required")

    graph: dict[str, Any] = {}
    if investigation_id or alert_id:
        payload = await _resolve_finskalp_payload(investigation_id, alert_id=alert_id)
        graph = payload.get("live_fusion") or payload.get("graph_viz") or {}
    if not graph.get("nodes") and not graph.get("address_view"):
        raise HTTPException(status_code=404, detail="Graph not found; provide investigation_id or alert_id")

    return graphsense_path_result(graph, from_addr, to_addr, max_hops=max(1, min(max_hops, 8)))


@app.post("/api/interop/graphsense/tagpack/import")
async def interop_graphsense_tagpack_import(file: UploadFile = File(...)):
    """Upload GraphSense TagPack CSV for regulator demos."""
    from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store
    from flowsint_crypto_compliance.interop.graphsense_tagpack import parse_tagpack_csv

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8") from exc
    labels = parse_tagpack_csv(text)
    store = get_entity_label_store()
    upserted = store.bulk_upsert(labels)
    return {"loaded": len(labels), "upserted": upserted, "total_in_store": store.count()}


@app.post("/api/kyt/watchlist")
async def kyt_watchlist_add(body: KytWatchlistRequest):
    """One-click address monitoring from case card — merged with env watchlist."""
    from flowsint_crypto_compliance.demo.live_kyt_scanner import add_kyt_watch_address, list_kyt_watch_addresses

    try:
        addr, chain = add_kyt_watch_address(body.address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "status": "subscribed",
        "address": addr,
        "chain": chain.value,
        "watchlist_size": len(list_kyt_watch_addresses()),
    }


@app.get("/api/kyt/watchlist")
async def kyt_watchlist_list():
    from flowsint_crypto_compliance.demo.live_kyt_scanner import list_kyt_watch_addresses

    addrs = list_kyt_watch_addresses()
    return {"addresses": addrs, "count": len(addrs)}


@app.post("/api/osint/continuous/rescan")
async def osint_continuous_rescan(request: Request):
    """Periodic OSINT rescan for KYT watchlist addresses."""
    assert_demo_api_token(request)
    from flowsint_crypto_compliance.osint.continuous_osint import run_continuous_osint_rescan

    tenant = os.getenv("FINSKALP_TENANT_ID")
    return await run_continuous_osint_rescan(tenant_id=tenant, max_addresses=10)


@app.get("/api/osint/fusion-explain/{investigation_id}")
async def osint_fusion_explain(investigation_id: str):
    """Fusion confidence explain trace for evidence-chain visualization."""
    payload = await _resolve_finskalp_payload(investigation_id)
    open_osint = payload.get("open_osint") or {}
    fusion = open_osint.get("fusion_confidence") or {}
    if not fusion:
        raise HTTPException(status_code=404, detail="Fusion explain недоступен")
    return {
        "investigation_id": investigation_id,
        "subject": payload.get("address"),
        "chain": payload.get("chain"),
        "fusion": fusion,
        "mentions": (open_osint.get("mentions") or [])[:30],
        "institutional_memory": open_osint.get("institutional_memory"),
        "preserved_evidence": open_osint.get("preserved_evidence") or [],
    }


@app.get("/api/osint/evidence/{case_ref}/{content_hash}")
async def osint_evidence_manifest(case_ref: str, content_hash: str):
    from flowsint_crypto_compliance.osint.evidence_preservation import load_evidence_manifest

    try:
        safe_ref = validate_case_ref(case_ref)
        safe_hash = validate_evidence_hash(content_hash)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Некорректные параметры доказательства") from exc
    data = load_evidence_manifest(safe_ref, safe_hash)
    if not data:
        raise HTTPException(status_code=404, detail="Снимок доказательства не найден")
    return data


@app.get("/api/osint/source-reliability")
async def osint_source_reliability_list():
    from flowsint_crypto_compliance.osint.source_reliability import load_reliability_map, sync_from_attribution_eval

    sync = sync_from_attribution_eval()
    return {"reliability": load_reliability_map(), "sync": sync}


@app.post("/api/osint/source-reliability/feedback")
async def osint_source_reliability_feedback(body: dict, request: Request):
    assert_demo_api_token(request)
    from flowsint_crypto_compliance.osint.source_reliability import record_analyst_feedback

    name = str(body.get("source_name") or "")
    if not name:
        raise HTTPException(status_code=422, detail="source_name required")
    row = record_analyst_feedback(
        source_name=name,
        confirmed=bool(body.get("confirmed", True)),
        osint_source_type=body.get("source_type"),
    )
    return row.to_dict()


@app.get("/api/osint/collector-health")
async def osint_collector_health(force: bool = False):
    from flowsint_crypto_compliance.osint.collector_health import run_collector_health_check

    return await run_collector_health_check(force=force)


@app.get("/api/osint/priority-queue")
async def osint_priority_queue_list():
    from flowsint_crypto_compliance.osint.priority_queue import get_osint_priority_queue

    return {"queue": get_osint_priority_queue().to_list(), "size": get_osint_priority_queue().size()}


@app.get("/api/ml/status")
async def ml_status():
    from flowsint_crypto_compliance.ml.onnx_inference import ONNXRiskScorer, default_model_path

    scorer = ONNXRiskScorer()
    return {
        "onnx_available": scorer.available,
        "model_path": str(default_model_path()),
        "features": 10,
        "graphsage_hops": 2,
    }


@app.post("/api/enforcement/ingest")
async def enforcement_ingest():
    from flowsint_crypto_compliance.ingestion.enforcement_feeds import ingest_enforcement_feeds

    return ingest_enforcement_feeds()


class LiveFusionRequest(BaseModel):
    address: str
    chain: str = "tron"
    max_hops: int = Field(3, ge=1, le=3)


@app.post("/api/live/fusion")
async def live_multihop_fusion(body: LiveFusionRequest):
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
        ref = f"LIVE-{body.chain.upper()}-{body.address[:12]}"
        payload["case_ref"] = ref
        payload["ml_score"] = score_fusion_graph(payload, address=body.address, chain=body.chain)
        payload["neo4j"] = WalletNeo4jStore().persist_fusion_graph(payload, case_ref=ref)
        return payload
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Live fusion timeout (30s)") from exc


@app.get("/api/live/collectors/status")
async def live_collectors_status():
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
            "BSCSCAN_API_KEY": bool(os.getenv("BSCSCAN_API_KEY")),
            "ETHERSCAN_API_KEY": bool(os.getenv("ETHERSCAN_API_KEY")),
        },
    }


class AttributionReviewBody(BaseModel):
    chain: str = "tron"
    address: str
    label: str
    category: str = "exchange"
    analyst_id: str = "analyst"
    case_ref: str | None = None


_ANALYST_ROLES = frozenset({"analyst", "senior_analyst", "lead", "admin", "compliance_officer"})


def _assert_analyst_role(request: Request) -> str:
    role = (request.headers.get("X-Analyst-Role") or "analyst").strip().lower()
    if role not in _ANALYST_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Подтверждение атрибуции доступно аналитику и выше",
        )
    analyst = request.headers.get("X-Analyst-Id") or role
    return analyst


@app.post("/api/compliance/attribution/confirm")
async def confirm_attribution(body: AttributionReviewBody, request: Request):
    analyst = _assert_analyst_role(request)
    from flowsint_crypto_compliance.attribution.postgres_entity_store import analyst_confirm_label

    lbl = analyst_confirm_label(
        chain=body.chain.lower(),
        address=body.address.strip(),
        label=body.label,
        category=body.category,
        analyst_id=analyst,
    )
    try:
        from flowsint_crypto_compliance.search.meilisearch_client import index_wallet

        index_wallet(body.chain.lower(), body.address.strip(), label=body.label)
    except Exception:
        pass
    try:
        from flowsint_crypto_compliance.osint.source_reliability import record_analyst_feedback

        record_analyst_feedback(
            source_name=f"attribution:{body.category}",
            confirmed=True,
            osint_source_type=body.category,
        )
    except Exception:
        pass
    try:
        import os
        import uuid as _uuid

        from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
        from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus

        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        get_platform_event_bus().publish(
            PlatformEvent(
                event_type=EventType.REVIEW_SUBMITTED,
                source="compliance.attribution",
                tenant_id=_uuid.UUID(tenant_raw),
                actor=analyst,
                payload={
                    "action": "confirm",
                    "chain": body.chain.lower(),
                    "address": body.address.strip(),
                    "label": body.label,
                    "category": body.category,
                    "case_ref": body.case_ref,
                    "confidence": 0.95,
                },
            )
        )
    except Exception:
        pass
    return {"status": "confirmed", "label": lbl.to_dict()}


@app.post("/api/compliance/attribution/reject")
async def reject_attribution(body: AttributionReviewBody, request: Request):
    analyst = _assert_analyst_role(request)
    from flowsint_crypto_compliance.attribution.postgres_entity_store import analyst_reject_label

    lbl = analyst_reject_label(
        chain=body.chain.lower(),
        address=body.address.strip(),
        label=body.label,
        category=body.category,
        analyst_id=analyst,
    )
    try:
        from flowsint_crypto_compliance.osint.source_reliability import record_analyst_feedback

        record_analyst_feedback(
            source_name=f"attribution:{body.category}",
            confirmed=False,
            osint_source_type=body.category,
        )
    except Exception:
        pass
    try:
        import os
        import uuid as _uuid

        from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
        from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus

        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        get_platform_event_bus().publish(
            PlatformEvent(
                event_type=EventType.REVIEW_SUBMITTED,
                source="compliance.attribution",
                tenant_id=_uuid.UUID(tenant_raw),
                actor=analyst,
                payload={
                    "action": "reject",
                    "chain": body.chain.lower(),
                    "address": body.address.strip(),
                    "label": body.label,
                    "category": body.category,
                    "case_ref": body.case_ref,
                    "confidence": 0.2,
                },
            )
        )
    except Exception:
        pass
    return {"status": "rejected", "label": lbl.to_dict()}


class LiveCollectRequest(BaseModel):
    collector: str = Field(..., description="collect_tron_chain | collect_tron_trc20_transfers | …")
    address: str | None = None
    query: str | None = None
    username: str | None = None
    async_mode: bool = False


@app.post("/api/live/collect")
async def live_collect_one(body: LiveCollectRequest):
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
        try:
            from flowsint_core.core.celery import celery

            task = celery.send_task(task_name, args=[str(value).strip()])
            return {"task_id": task.id, "status": "queued", "collector": body.collector}
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        result = await asyncio.wait_for(
            run_live_collector(body.collector, str(value).strip()),
            timeout=45.0,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Collector timeout (45s)") from exc
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"collector": body.collector, "result": result}


class ScoringPredictRequest(BaseModel):
    graph: dict[str, Any] = Field(default_factory=dict)
    address: str = ""
    chain: str = "tron"


@app.post("/api/scoring/predict")
async def scoring_predict(body: ScoringPredictRequest):
    from flowsint_crypto_compliance.ml.scoring_pipeline import score_fusion_graph

    if not body.graph.get("nodes"):
        raise HTTPException(status_code=422, detail="graph.nodes required")
    return score_fusion_graph(body.graph, address=body.address, chain=body.chain)


@app.post("/api/scoring/label-case")
async def scoring_label_case(body: dict[str, Any]):
    from flowsint_crypto_compliance.ml.active_learning import append_case_label

    return append_case_label(
        case_ref=str(body.get("case_ref", "")),
        address=str(body.get("address", "")),
        chain=str(body.get("chain", "tron")),
        label=str(body.get("label", "illicit")),
        risk_score=float(body.get("risk_score", 0)),
        features=body.get("features"),
        source=str(body.get("source", "CASE_SAR")),
    )


@app.post("/api/ocr/extract")
async def ocr_extract_upload(
    file: UploadFile = File(...),
    backend: str = "auto",
    async_mode: bool = False,
):
    import base64

    data = await file.read()
    try:
        assert_upload_size(len(data))
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    filename = sanitize_filename(file.filename or "document.pdf")
    try:
        validate_upload_magic(data, filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    allowed_backends = {"auto", "paddle", "pymupdf", "tesseract"}
    if backend not in allowed_backends:
        raise HTTPException(status_code=422, detail="Недопустимый OCR backend")
    if async_mode:
        try:
            from flowsint_core.core.celery import celery

            task = celery.send_task(
                "run_ocr_extract",
                kwargs={
                    "filename": filename,
                    "data_b64": base64.b64encode(data).decode("ascii"),
                    "backend": backend,
                },
            )
            return {"status": "queued", "task_id": task.id, "filename": filename}
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    result = _ocr_pipeline.process_bytes(data, filename, backend=backend)
    return result.to_dict()


@app.get("/api/registry/banks")
async def registry_banks(offset: int = 0, limit: int = 50):
    return list_banks(offset=offset, limit=limit)


@app.get("/api/registry/exchangers")
async def registry_exchangers(
    offset: int = 0,
    limit: int = 50,
    risk: str | None = None,
    jurisdiction: str | None = None,
):
    return list_exchangers(offset=offset, limit=limit, risk=risk, jurisdiction=jurisdiction)


@app.get("/api/registry/vasp/meta")
async def registry_vasp_meta():
    from flowsint_crypto_compliance.registry.cis_vasp_registry import registry_metadata

    return registry_metadata()


@app.get("/api/cis")
async def cis():
    return cis_coverage()


class InstrumentRunRequest(BaseModel):
    scenario_id: str | None = None
    alert_id: str | None = None
    address: str | None = Field(None, max_length=128)
    chain: str | None = None
    bank_reference: str | None = None
    amount: float | None = None


@app.post("/api/instruments/{code}/run")
async def run_instrument(code: str, body: InstrumentRunRequest | None = None):
    try:
        result = await instrument_runner.run(
            code,
            scenario_id=body.scenario_id if body else None,
            alert_id=body.alert_id if body else None,
            address=body.address if body else None,
            chain=body.chain if body else None,
            bank_reference=body.bank_reference if body else None,
            amount=body.amount if body else None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@app.get("/api/feed/live")
async def live_feed():
    from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

    bus = get_event_bus()

    async def events():
        loop = asyncio.get_event_loop()
        for ev in bus.recent(5):
            payload = ev.get("payload") or {}
            row = {
                "source": ev.get("source", "finskalp"),
                "text_ru": ev.get("text_ru", ""),
                "severity": ev.get("severity", "info"),
                "type": ev.get("type"),
                **payload,
            }
            yield f"data: {json.dumps(row, ensure_ascii=False)}\n\n"
        while True:
            ev = await loop.run_in_executor(None, _poll_event, bus)
            if ev:
                payload = ev.get("payload") or {}
                row = {
                    "source": ev.get("source", "finskalp"),
                    "text_ru": ev.get("text_ru", ""),
                    "severity": ev.get("severity", "info"),
                    "type": ev.get("type"),
                    **payload,
                }
            else:
                row = live_feed_event()
            if row:
                row["ts"] = asyncio.get_event_loop().time()
                yield f"data: {json.dumps(row, ensure_ascii=False)}\n\n"
            await asyncio.sleep(1.0 if ev else 3.0)

    return StreamingResponse(events(), media_type="text/event-stream")


def _poll_event(bus):
    for ev in bus.stream_events(block_ms=1500):
        return ev
    return None


@app.get("/api/stats")
async def stats():
    return await center.stats()


@app.get("/api/inbox")
async def inbox(status: str | None = None):
    return await center.list_inbox(status=status)  # type: ignore[arg-type]


@app.get("/api/reports")
async def reports_registry():
    return await center.list_reports()


@app.get("/api/inbox/{alert_id}")
async def get_alert(alert_id: str):
    try:
        return await center.get_alert(alert_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/cases/workflow/stats")
async def workflow_stats():
    return await center.workflow_stats()


@app.patch("/api/inbox/{alert_id}/workflow")
async def transition_workflow(alert_id: str, body: WorkflowTransitionBody):
    try:
        result = await center.transition_workflow(
            alert_id,
            target=body.workflow_status,  # type: ignore[arg-type]
            assignee=body.assignee,
            note=body.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus

        get_event_bus().publish(
            "case_transition",
            payload={
                "alert_id": alert_id,
                "alert_code": result.get("alert_code"),
                "case_ref": result.get("case_ref"),
                "workflow_status": result.get("workflow_status"),
            },
            text_ru=(
                f"Дело {result.get('alert_code')} → "
                f"{result.get('workflow_label_ru', result.get('workflow_status'))}"
            ),
            severity="info",
            correlation_id=result.get("case_ref"),
        )
    except Exception:
        pass
    return result


@app.post("/api/inbox/{alert_id}/comments")
async def add_case_comment(alert_id: str, body: CaseCommentBody):
    try:
        return await center.add_comment(alert_id, text=body.text, author=body.author)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/inbox/{alert_id}/graph")
async def get_alert_graph(alert_id: str):
    try:
        alert = await center.get_alert(alert_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    graph = alert.get("evidence_graph")
    if not graph:
        report = alert.get("report") or {}
        graph = report.get("live_fusion") if (report.get("live_fusion") or {}).get("nodes") else report.get("graph_viz")
    if not graph or not graph.get("nodes"):
        raise HTTPException(status_code=404, detail="Граф расследования ещё не построен")
    return graph


@app.get("/api/inbox/{alert_id}/forensic/pdf")
async def get_forensic_pdf(alert_id: str):
    stored = await _resolve_finskalp_payload(alert_id=alert_id)
    inv_id = str(stored.get("investigation_id") or alert_id)
    report = _select_finskalp_report(stored, "forensic")
    return _render_finskalp_attachment(report, "forensic", inv_id)


@app.get("/api/inbox/{alert_id}/volumetric/pdf")
async def get_volumetric_pdf(alert_id: str):
    stored = await _resolve_finskalp_payload(alert_id=alert_id)
    inv_id = str(stored.get("investigation_id") or alert_id)
    report = _select_finskalp_report(stored, "volumetric")
    return _render_finskalp_attachment(report, "volumetric", inv_id)


@app.get("/api/inbox/{alert_id}/sar/pdf")
async def get_sar_pdf(alert_id: str):
    stored = await _resolve_finskalp_payload(alert_id=alert_id)
    inv_id = str(stored.get("investigation_id") or alert_id)
    report = _select_finskalp_report(stored, "sar")
    return _render_finskalp_attachment(report, "sar", inv_id)


@app.get("/api/inbox/{alert_id}/fz115")
async def get_fz115_report(alert_id: str):
    try:
        alert = await center.get_alert(alert_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not alert.get("fz115_report"):
        raise HTTPException(status_code=404, detail="Отчёт 115-ФЗ ещё не сформирован")
    return alert["fz115_report"]


@app.get("/api/inbox/{alert_id}/fz115/pdf")
async def get_fz115_pdf(alert_id: str):
    try:
        alert = await center.get_alert(alert_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    fz115 = alert.get("fz115_report")
    if not fz115:
        raise HTTPException(status_code=404, detail="Отчёт 115-ФЗ ещё не сформирован")
    html = render_fz115_html(fz115)
    content, media_type = render_pdf_bytes(html)
    filename = f"{fz115.get('report_id', alert_id)}.pdf"
    if media_type.startswith("text/html"):
        filename = filename.replace(".pdf", ".html")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/patterns")
async def patterns():
    return center.list_patterns()


@app.post("/api/hub/str")
async def receive_bank_str(body: BankStrRequest | None = None):
    sid = body.scenario_id if body else None
    try:
        payload = await center.receive_bank_str(
            sid,
            crypto_address=body.crypto_address if body else None,
            crypto_chain=body.crypto_chain if body else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return payload


@app.post("/api/monitor/scan")
async def pattern_scan():
    found = await center.run_pattern_scan()
    return {"found": len(found), "alerts": found}


@app.post("/api/investigate/{alert_id}")
async def investigate(alert_id: str):
    try:
        alert = await center.get_alert(alert_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if alert.get("report"):
        return {
            "alert_id": alert_id,
            "steps": alert.get("investigation_steps", []),
            "report": alert["report"],
            "fz115_report": alert.get("fz115_report"),
            "cached": True,
        }

    await center.update_alert(alert_id, status="investigating", workflow_status="investigating")

    async def on_step(steps: list[dict]) -> None:
        await center.update_alert(alert_id, steps=steps)

    try:
        steps, report = await pipeline.run_for_alert(alert, on_step=on_step)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    fz115 = await _finalize_investigation(alert_id, steps, report)
    updated = await center.get_alert(alert_id)
    return {
        "alert_id": alert_id,
        "steps": steps,
        "report": report,
        "fz115_report": fz115,
        "alert": updated,
        "cached": False,
    }


@app.get("/api/investigate/{alert_id}/stream")
async def investigate_stream(alert_id: str):
    try:
        alert = await center.get_alert(alert_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if alert.get("report"):

        async def cached_events():
            payload = {
                "type": "done",
                "report": alert["report"],
                "fz115_report": alert.get("fz115_report"),
                "steps": alert.get("investigation_steps", []),
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(cached_events(), media_type="text/event-stream")

    async def event_generator():
        queue: asyncio.Queue[dict] = asyncio.Queue()

        async def on_step(steps: list[dict]) -> None:
            await center.update_alert(alert_id, steps=steps)
            await queue.put({"type": "step", "steps": steps})

        async def run_pipeline():
            await center.update_alert(
                alert_id, status="investigating", workflow_status="investigating"
            )
            try:
                steps, report = await pipeline.run_for_alert(alert, on_step=on_step)
            except ValueError as exc:
                await queue.put({"type": "error", "detail": str(exc)})
                return
            fz115 = await _finalize_investigation(alert_id, steps, report)
            await queue.put(
                {"type": "done", "steps": steps, "report": report, "fz115_report": fz115}
            )

        task = asyncio.create_task(run_pipeline())
        yield f"data: {json.dumps({'type': 'start', 'alert_id': alert_id}, ensure_ascii=False)}\n\n"

        while True:
            item = await queue.get()
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            if item.get("type") in ("done", "error"):
                break

        await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")


_runner = RegulatorDemoRunner()


@app.get("/api/scenarios")
async def list_scenarios():
    return RegulatorDemoRunner.list_scenarios()


@app.post("/api/run/{scenario_id}")
async def run_scenario(scenario_id: str):
    try:
        report = await _runner.run(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return report.to_dict()


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main() -> None:
    import uvicorn

    host = demo_bind_host()
    port = int(os.getenv("COMPLIANCE_DEMO_PORT", "8877"))
    lan = _lan_ip()
    print()
    print("=" * 64)
    print("  FLOWSINT COMPLIANCE — Боевой прототип ПОД/ФТ (115-ФЗ)")
    print("=" * 64)
    print(f"  Локально:     http://localhost:{port}")
    if host != "127.0.0.1":
        print(f"  В сети (LAN): http://{lan}:{port}")
    print("  LAN: задайте COMPLIANCE_DEMO_BIND_HOST=0.0.0.0 и COMPLIANCE_DEMO_ALLOW_ALL_CORS=1")
    print("  Масштаб:      100 банков · 1 847 OTC · 187M+ население · 11 юрисдикций СНГ")
    print("  Остановка:    Ctrl+C")
    print("=" * 64)
    print()
    uvicorn.run(
        "flowsint_crypto_compliance.demo.web_server:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
