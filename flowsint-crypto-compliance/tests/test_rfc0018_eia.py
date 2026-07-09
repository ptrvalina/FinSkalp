"""RFC-0018 Explainable AI & Investigation Assistant — tests."""

from __future__ import annotations

import inspect
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.eccf.orchestrator import run_eccf_pipeline
from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository, reset_eccf_repository
from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import reset_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.timeline import reset_evidence_timeline
from flowsint_crypto_compliance.platform.v2.eccf.archive import reset_evidence_archive
from flowsint_crypto_compliance.platform.v2.eccf.report_bridge import reset_report_bridge
from flowsint_crypto_compliance.platform.v2.eccf.id_generator import reset_id_counters
from flowsint_crypto_compliance.platform.v2.eia.constraints import eia_architectural_constraints
from flowsint_crypto_compliance.platform.v2.eia.context_engine import (
    build_investigation_context,
    reset_context_cache,
)
from flowsint_crypto_compliance.platform.v2.eia.manifest import eia_manifest
from flowsint_crypto_compliance.platform.v2.eia.monitoring import reset_eia_metrics
from flowsint_crypto_compliance.platform.v2.eia.orchestrator import run_eia_task
from flowsint_crypto_compliance.platform.v2.eia.prompt_engine import render_prompt
from flowsint_crypto_compliance.platform.v2.eia.prompt_registry import reset_prompt_registry
from flowsint_crypto_compliance.platform.v2.eia.report_assistant import build_report_outline
from flowsint_crypto_compliance.platform.v2.eia.security import reset_audit_log
from flowsint_crypto_compliance.platform.v2.eia.types import AITaskType, EIAStage
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore


@pytest.fixture(autouse=True)
def memory_env(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.knowledge_graph as kg_mod
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

    reset_eccf_repository()
    reset_audit_trail()
    reset_evidence_timeline()
    reset_evidence_archive()
    reset_report_bridge()
    reset_id_counters()
    reset_context_cache()
    reset_eia_metrics()
    reset_prompt_registry()
    reset_audit_log()

    ks_mod._kg_store = None
    kg_mod._kg_service = None
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    mem = KnowledgeGraphStore(use_memory=True)
    kg = kg_mod.KnowledgeGraphService(store=mem)

    def _kg():
        return kg

    for target in (
        "flowsint_crypto_compliance.platform.v2.knowledge_store.get_knowledge_graph_store",
        "flowsint_crypto_compliance.platform.v2.knowledge_graph.get_knowledge_graph_service",
    ):
        monkeypatch.setattr(target, _kg)
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.event_bus.PlatformEventBus._persist_postgres",
        lambda *a, **k: None,
    )
    yield


@pytest.fixture
def v2_client():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


@pytest.fixture
def sample_eccf_payload():
    return {
        "entity_type": "company",
        "entity_value": "EIA Test Org",
        "source_type": "registry",
        "payload": {"license": "LIC-EIA", "confidence": 0.85},
    }


@pytest.mark.asyncio
async def test_eia_manifest_task_types():
    m = eia_manifest()
    assert m["rfc"] == "RFC-0018"
    assert m["schema_version"] == "2.0.0"
    assert len(m["task_types"]) == 8
    assert AITaskType.EXPLAIN_RISK.value in m["task_types"]
    assert AITaskType.REPORT_OUTLINE.value in m["task_types"]
    assert len(m["pipeline"]) == 7
    assert EIAStage.CONTEXT.value in m["pipeline"]
    assert EIAStage.DELIVER.value in m["pipeline"]
    assert "architectural_constraints" in m
    assert m["architectural_constraints"]["human_in_the_loop"] is True


@pytest.mark.asyncio
async def test_context_engine_gathers_multi_source(sample_eccf_payload):
    await run_eccf_pipeline(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        collector_payload=sample_eccf_payload,
        case_ref="RFC18-CTX",
    )
    ctx = await build_investigation_context(
        case_ref="RFC18-CTX",
        entity_keys=["EIA Test Org"],
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        use_cache=False,
    )
    assert ctx["ok"]
    assert ctx["case_ref"] == "RFC18-CTX"
    assert ctx["evidence_count"] >= 1
    assert "workflow" in ctx["sources"] or "evidence" in ctx["sources"]
    assert "analyst_history" in ctx
    assert ctx["analyst_history"]["stub"] is True


@pytest.mark.asyncio
async def test_assist_explain_risk_with_citations(sample_eccf_payload):
    await run_eccf_pipeline(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        collector_payload=sample_eccf_payload,
        case_ref="RFC18-RISK",
    )
    result = await run_eia_task(
        task_type=AITaskType.EXPLAIN_RISK,
        case_ref="RFC18-RISK",
        entity_keys=["EIA Test Org"],
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
    )
    assert result.ok
    assert result.task_type == "explain_risk"
    assert result.narrative_ru
    assert result.requires_analyst_confirmation is True
    assert len(result.citations) >= 1
    assert result.citations[0].evidence_id is not None
    assert EIAStage.EXPLANATION.value in result.stages


@pytest.mark.asyncio
async def test_recommendations_require_analyst():
    result = await run_eia_task(
        task_type=AITaskType.SUMMARY,
        case_ref="RFC18-REC",
        entity_keys=["test-entity"],
    )
    assert result.ok
    assert result.requires_analyst_confirmation is True
    for rec in result.recommendations:
        assert rec.get("requires_analyst_confirmation") is True


def test_constraints_no_mutation():
    constraints = eia_architectural_constraints()
    forbidden = constraints["forbidden_actions"]
    assert "mutate_knowledge_graph" in forbidden
    assert "mutate_evidence" in forbidden
    assert "mutate_risk_score" in forbidden
    assert "auto_decision" in forbidden
    assert constraints["auto_decisions"] is False

    from flowsint_crypto_compliance.platform.v2.eia import orchestrator

    src = inspect.getsource(orchestrator.run_eia_task)
    assert "upsert" not in src.lower()
    assert "store(" not in src or "temporal_store" not in src


def test_prompt_versioning():
    result_v1 = render_prompt(
        "explain_risk",
        {
            "case_ref": "TEST",
            "entity_key": "org-1",
            "risk_signals": "{}",
            "top_factors": "[]",
        },
        version="1.0.0",
    )
    result_latest = render_prompt(
        "explain_risk",
        {
            "case_ref": "TEST",
            "entity_key": "org-1",
            "risk_signals": "{}",
            "top_factors": "[]",
        },
    )
    assert result_v1["ok"]
    assert result_latest["ok"]
    assert result_v1["version"] == "1.0.0"
    assert result_latest["version"] == "1.1.0"
    assert "evidence_id" in result_latest["prompt"]
    assert len(result_latest["available_versions"]) >= 2


def test_api_assist_endpoint(v2_client, sample_eccf_payload):
    import asyncio

    asyncio.run(
        run_eccf_pipeline(
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            collector_payload=sample_eccf_payload,
            case_ref="RFC18-API",
        )
    )
    resp = v2_client.post(
        "/api/platform/v2/eia/assist",
        json={
            "task_type": "summary",
            "case_ref": "RFC18-API",
            "entity_keys": ["EIA Test Org"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"]
    assert data["task_type"] == "summary"
    assert data["requires_analyst_confirmation"] is True


@pytest.mark.asyncio
async def test_report_assistant_outline(sample_eccf_payload):
    await run_eccf_pipeline(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        collector_payload=sample_eccf_payload,
        case_ref="RFC18-REPORT",
    )
    ctx = await build_investigation_context(
        case_ref="RFC18-REPORT",
        entity_keys=["EIA Test Org"],
        use_cache=False,
    )
    outline = build_report_outline(ctx)
    assert outline["outline"]
    assert len(outline["outline"]) >= 6
    assert outline["materials"]
    assert outline["open_questions"]
    assert "Черновик отчёта" in outline["narrative_ru"]

    result = await run_eia_task(
        task_type=AITaskType.REPORT_OUTLINE,
        case_ref="RFC18-REPORT",
        entity_keys=["EIA Test Org"],
    )
    assert result.ok
    assert "outline" in result.explain.get("engine", {}) or result.narrative_ru
