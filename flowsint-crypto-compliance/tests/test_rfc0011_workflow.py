"""RFC-0011 Workflow & User Interaction Logic — tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore
from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router
from flowsint_crypto_compliance.platform.v2.workflow import (
    get_workflow_orchestrator,
    reset_recovery_store,
    workflow_manifest,
)
from flowsint_crypto_compliance.platform.v2.workflow.recovery import save_recovery_state


@pytest.fixture(autouse=True)
def memory_env(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.investigation_platform.service as svc_mod
    import flowsint_crypto_compliance.platform.v2.knowledge_graph as kg_mod
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod
    import flowsint_crypto_compliance.platform.v2.workflow.orchestrator as wf_mod

    svc_mod._service = None
    wf_mod._service = None
    kg_mod._kg_service = None
    ks_mod._kg_store = None
    reset_recovery_store()
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")

    mem = KnowledgeGraphStore(use_memory=True)
    kg = kg_mod.KnowledgeGraphService(store=mem)
    ks_mod._kg_store = mem

    def _kg_service():
        return kg

    def _mem_store(*_a, **_k):
        return mem

    for target in (
        "flowsint_crypto_compliance.platform.v2.knowledge_store.get_knowledge_graph_store",
        "flowsint_crypto_compliance.platform.v2.investigation_workspace.get_knowledge_graph_store",
        "flowsint_crypto_compliance.platform.v2.knowledge_graph.get_knowledge_graph_store",
        "flowsint_crypto_compliance.platform.v2.knowledge_graph.get_knowledge_graph_service",
        "flowsint_crypto_compliance.platform.v2.investigation_platform.service.get_knowledge_graph_service",
    ):
        monkeypatch.setattr(target, _kg_service if "service" in target else _mem_store)

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
def v2_client():
    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_workflow_manifest_structure():
    m = workflow_manifest()
    assert m["rfc"] == "RFC-0011"
    assert len(m["philosophy"]) == 4
    assert len(m["investigation_lifecycle"]) == 13
    assert all(s["mandatory"] for s in m["investigation_lifecycle"])
    assert len(m["seed_object_types"]) == 6
    assert m["event_driven"] is True


def test_workflow_state_for_case():
    InvestigationWorkspace().open_case(case_ref="RFC11-STATE")
    state = get_workflow_orchestrator().get_workflow_state(case_ref="RFC11-STATE")
    assert state["ok"] is True
    assert state["oicd_phase"] in ("observe", "investigate", "correlate", "decide")
    assert len(state["lifecycle"]) == 13


def test_workflow_recommendations():
    InvestigationWorkspace().open_case(case_ref="RFC11-REC")
    recs = get_workflow_orchestrator().get_recommendations(case_ref="RFC11-REC")
    assert recs["ok"] is True
    assert recs["count"] >= 1
    assert recs["recommendations"][0]["explanation_ru"]


def test_workflow_first_login():
    briefing = get_workflow_orchestrator().get_first_login_briefing()
    assert briefing["ok"] is True
    assert len(briefing["checks"]) == 6


def test_workflow_recovery_roundtrip():
    saved = save_recovery_state("user-1", {"active_tab": "graph", "graph_zoom": 1.5})
    assert saved["ok"] is True
    assert saved["state"]["active_tab"] == "graph"


def test_workflow_manifest_api(v2_client):
    resp = v2_client.get("/api/platform/v2/workflow/manifest")
    assert resp.status_code == 200
    assert resp.json()["rfc"] == "RFC-0011"


def test_workflow_state_api(v2_client):
    InvestigationWorkspace().open_case(case_ref="RFC11-API")
    resp = v2_client.get("/api/platform/v2/workflow/state?case_ref=RFC11-API")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_workflow_start_wallet_seed():
    result = await get_workflow_orchestrator().start_workflow(
        case_ref="RFC11-START",
        seed_type="wallet",
        seed_value="TWorkflowTestAddress",
        chain="tron",
    )
    assert result["ok"] is True
    assert result["auto_collectors_started"] is True
    assert result["entity_id"]
