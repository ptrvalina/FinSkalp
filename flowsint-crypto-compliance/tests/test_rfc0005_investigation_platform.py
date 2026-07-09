"""RFC-0005 Investigation Platform — readiness tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.investigation_platform import (
    get_investigation_platform_service,
    investigation_platform_manifest,
    operations_manifest,
)
from flowsint_crypto_compliance.platform.v2.intelligence.orchestrator import _orchestrator
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore
from flowsint_crypto_compliance.services.case_workflow import RFC_0005_LIFECYCLE, WORKFLOW_STATUSES


@pytest.fixture(autouse=True)
def reset_singletons(monkeypatch):
    global _orchestrator
    import flowsint_crypto_compliance.platform.v2.intelligence.orchestrator as orch_mod

    orch_mod._orchestrator = None
    import flowsint_crypto_compliance.platform.v2.investigation_platform.service as svc_mod

    svc_mod._service = None
    import flowsint_crypto_compliance.platform.v2.knowledge_graph as kg_mod

    kg_mod._kg_service = None
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

    ks_mod._kg_store = None
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")

    mem = KnowledgeGraphStore(use_memory=True)
    kg = kg_mod.KnowledgeGraphService(store=mem)

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
        monkeypatch.setattr(
            target,
            _kg_service if "service" in target else _mem_store,
        )
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
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_investigation_manifest_rfc0005():
    m = investigation_platform_manifest()
    assert m["rfc"] == "RFC-0005"
    assert len(m["lifecycle_stages"]) == 7
    assert len(m["workspace_panels"]) == 10
    assert len(m["report_kinds"]) == 8
    assert m["evidence_rules"]["delete_forbidden"] is True


def test_operations_manifest():
    m = operations_manifest()
    assert m["rfc"] == "RFC-0005"
    assert "metrics_endpoint" in m
    assert len(m["release_cycle"]) == 9


def test_rfc0005_lifecycle_maps_workflow():
    for code in WORKFLOW_STATUSES:
        assert code in RFC_0005_LIFECYCLE


def test_workspace_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/investigations/RFC5-TEST/workspace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_ref"] == "RFC5-TEST"
    assert len(body["panels"]) == 10
    assert "workflow" in body


def test_evidence_register_and_status_change():
    svc = get_investigation_platform_service()

    reg = svc.register_evidence(
        case_ref="RFC5-EV",
        source_type="manual",
        entity_type="document",
        entity_value="report.pdf",
        actor="analyst-1",
    )
    assert reg["ok"] is True
    eid = uuid.UUID(reg["evidence_id"])

    updated = svc.update_evidence_status(eid, new_status="verified", actor="analyst-2", reason="проверено")
    assert updated["ok"] is True
    assert updated["status"] == "verified"

    listed = svc.list_evidence(case_ref="RFC5-EV")
    assert listed["delete_forbidden"] is True
    assert listed["count"] >= 1


def test_evidence_api(v2_client):
    resp = v2_client.post(
        "/api/platform/v2/investigations/RFC5-API/evidence",
        json={
            "source_type": "osint",
            "entity_type": "domain",
            "entity_value": "example.org",
            "acquisition_method": "scalpel",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    lst = v2_client.get("/api/platform/v2/investigations/RFC5-API/evidence")
    assert lst.status_code == 200
    assert lst.json()["count"] >= 1


def test_timeline_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/cases/RFC5-TEST/timeline")
    assert resp.status_code == 200
    assert "events" in resp.json()


def test_explain_endpoint_not_found(v2_client):
    resp = v2_client.get(
        f"/api/platform/v2/investigations/RFC5-TEST/explain/{uuid.uuid4()}"
    )
    assert resp.status_code == 404
