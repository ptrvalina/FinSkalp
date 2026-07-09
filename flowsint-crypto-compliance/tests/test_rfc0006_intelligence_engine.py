"""RFC-0006 Intelligence Engine — readiness tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.intelligence_engine import (
    intelligence_pipeline_manifest,
    run_intelligence_engine,
)
from flowsint_crypto_compliance.platform.v2.intelligence_engine.memory import reset_memory
from flowsint_crypto_compliance.platform.v2.intelligence_engine.patterns import detect_patterns
from flowsint_crypto_compliance.platform.v2.intelligence_engine.scores import calculate_intelligence_scores
from flowsint_crypto_compliance.platform.v2.intelligence_engine.types import IntelligenceEngineContext
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore


@pytest.fixture(autouse=True)
def memory_env(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.intelligence.orchestrator as orch_mod
    import flowsint_crypto_compliance.platform.v2.intelligence_engine.orchestrator as rfc6_orch
    import flowsint_crypto_compliance.platform.v2.knowledge_graph as kg_mod
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

    orch_mod._orchestrator = None
    rfc6_orch._orchestrator = None
    kg_mod._kg_service = None
    ks_mod._kg_store = None
    reset_memory()
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    mem = KnowledgeGraphStore(use_memory=True)
    kg = kg_mod.KnowledgeGraphService(store=mem)

    def _kg():
        return kg

    for target in (
        "flowsint_crypto_compliance.platform.v2.knowledge_store.get_knowledge_graph_store",
        "flowsint_crypto_compliance.platform.v2.knowledge_graph.get_knowledge_graph_service",
        "flowsint_crypto_compliance.platform.v2.investigation_platform.service.get_knowledge_graph_service",
        "flowsint_crypto_compliance.platform.v2.intelligence.orchestrator.get_knowledge_graph_service",
    ):
        monkeypatch.setattr(target, _kg)
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.neo4j_projection.Neo4jUnifiedProjection.project_entity",
        lambda *a, **k: {"projected": False},
    )
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.event_bus.PlatformEventBus._persist_postgres",
        lambda *a, **k: None,
    )
    yield


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000099")


@pytest.fixture
def v2_client():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_manifest_rfc0006():
    m = intelligence_pipeline_manifest()
    assert m["rfc"] == "RFC-0006"
    assert len(m["pipeline"]) == 14
    assert len(m["score_metrics"]) == 8
    assert len(m["questions_ru"]) == 5


def test_pattern_engine_detects_repeated_domain(tenant_id: uuid.UUID):
    ctx = IntelligenceEngineContext(
        tenant_id=tenant_id,
        mentions=[
            {"entity_type": "domain", "entity_value": "example.org", "confidence": 0.6},
            {"entity_type": "domain", "entity_value": "example.org", "confidence": 0.7},
        ],
    )
    hits = detect_patterns(ctx)
    assert any(h.code == "REPEATED_DOMAIN" for h in hits)


def test_eight_intelligence_scores(tenant_id: uuid.UUID):
    ctx = IntelligenceEngineContext(tenant_id=tenant_id, case_ref="RFC6-TEST")
    scores = calculate_intelligence_scores(
        ctx,
        patterns=[],
        hypotheses=[],
        evidence_count=3,
        engines_run=11,
    )
    d = scores.to_dict()
    assert len(d) == 8
    assert all(0 <= v <= 100 for v in d.values())


def test_run_intelligence_engine(tenant_id: uuid.UUID):
    result = run_intelligence_engine(
        tenant_id=tenant_id,
        address="TTestRFC6",
        chain="tron",
        case_ref="RFC6-RUN",
        screening={"onchain_summary": {"inbound_count": 5, "outbound_count": 4}},
        mentions=[{"entity_type": "domain", "entity_value": "test.org", "confidence": 0.5}],
        publish=False,
    )
    body = result.to_dict()
    assert body["ok"] is True
    assert len(body["scores"]) == 8
    assert len(body["questions_answered"]) == 5
    assert "pattern_detection" in body["pipeline_stages"] or "hypothesis_generator" in body["pipeline_stages"]


def test_intelligence_engine_api(v2_client):
    resp = v2_client.get("/api/platform/v2/intelligence-engine/manifest")
    assert resp.status_code == 200
    assert resp.json()["rfc"] == "RFC-0006"

    run = v2_client.post(
        "/api/platform/v2/intelligence-engine/run",
        json={
            "address": "TAddrRFC6",
            "chain": "tron",
            "case_ref": "RFC6-API",
            "screening": {"onchain_summary": {"inbound_count": 2, "outbound_count": 2}},
            "mentions": [{"entity_value": "dup.org", "entity_type": "domain"}, {"entity_value": "dup.org", "entity_type": "domain"}],
            "publish": False,
        },
    )
    assert run.status_code == 200
    data = run.json()
    assert data["ok"] is True
    assert len(data["hypotheses"]) >= 0
    assert "weakest_score" in data
