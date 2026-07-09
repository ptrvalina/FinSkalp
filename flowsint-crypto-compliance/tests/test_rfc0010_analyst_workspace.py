"""RFC-0010 Analyst Workspace — tests."""



from __future__ import annotations



import pytest

from fastapi import FastAPI

from fastapi.testclient import TestClient



from flowsint_crypto_compliance.platform.v2.analyst_workspace import (

    analyst_workspace_manifest,

    get_analyst_workspace_service,

    reset_collaboration_store,

    reset_personalization_store,

    universal_search,

)

from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace

from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore

from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router





@pytest.fixture(autouse=True)

def reset_singletons(monkeypatch):

    import flowsint_crypto_compliance.platform.v2.analyst_workspace.service as aws_mod

    import flowsint_crypto_compliance.platform.v2.investigation_platform.service as svc_mod

    import flowsint_crypto_compliance.platform.v2.intelligence.orchestrator as orch_mod

    import flowsint_crypto_compliance.platform.v2.knowledge_graph as kg_mod

    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod



    orch_mod._orchestrator = None

    svc_mod._service = None

    aws_mod._service = None

    kg_mod._kg_service = None

    ks_mod._kg_store = None

    reset_collaboration_store()

    reset_personalization_store()

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

    app = FastAPI()

    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")

    return TestClient(app)





def test_analyst_workspace_manifest_structure():

    m = analyst_workspace_manifest()

    assert m["rfc"] == "RFC-0010"

    assert len(m["workspace_tabs"]) == 8

    assert len(m["navigation_modules"]) == 10

    assert len(m["navigation_levels"]) == 3

    assert len(m["command_palette"]) >= 10

    assert "workspace_state_ms" in m["performance_slas"]

    assert "active_tab" in m["sync_fields"]

    assert m["multi_window_sync"]["enabled"] is True

    assert m["multi_window_sync"]["transport"] == "broadcast_channel"

    assert m["collaboration"]["realtime"] == "channel"





def test_analyst_workspace_state_service():

    state = get_analyst_workspace_service().get_workspace_state(case_ref="RFC10-TEST")

    assert state["ok"] is True

    assert state["case_ref"] == "RFC10-TEST"

    assert len(state["tabs"]) == 8

    assert "workspace" in state

    assert "evidence" in state

    assert "timeline" in state

    assert "intelligence" in state

    assert state["intelligence"]["engines_count"] >= 0

    assert "notifications" in state

    assert "collaboration" in state

    assert "personalization" in state





def test_analyst_workspace_state_missing_ref():

    state = get_analyst_workspace_service().get_workspace_state()

    assert state["ok"] is False

    assert "message_ru" in state





def test_analyst_workspace_manifest_api(v2_client):

    resp = v2_client.get("/api/platform/v2/analyst-workspace/manifest")

    assert resp.status_code == 200

    body = resp.json()

    assert body["rfc"] == "RFC-0010"

    assert body["principle_ru"]

    assert "latency_ms" in body

    assert resp.headers.get("X-Finskalp-Latency-Ms") is not None





def test_analyst_workspace_state_api(v2_client):

    resp = v2_client.get("/api/platform/v2/analyst-workspace/state?case_ref=RFC10-API")

    assert resp.status_code == 200

    body = resp.json()

    assert body["ok"] is True

    assert body["case_ref"] == "RFC10-API"

    assert body["counts"]["panels"] >= 1

    assert "latency_ms" in body





def test_universal_search_finds_case_entity():

    ws = InvestigationWorkspace()

    ws.open_case(case_ref="RFC10-SEARCH-001")

    result = universal_search("RFC10-SEARCH", case_ref="RFC10-SEARCH-001")

    assert result["ok"] is True

    assert result["counts"]["cases"] >= 1

    assert any(r["kind"] == "case" for r in result["results"])





def test_universal_search_empty_query():

    result = universal_search("")

    assert result["ok"] is False

    assert "message_ru" in result





def test_analyst_workspace_search_api(v2_client):

    ws = InvestigationWorkspace()

    ws.open_case(case_ref="RFC10-API-SEARCH")

    resp = v2_client.get("/api/platform/v2/analyst-workspace/search?q=RFC10-API")

    assert resp.status_code == 200

    body = resp.json()

    assert body["ok"] is True

    assert body["counts"]["total"] >= 1

    assert "latency_ms" in body





def test_collaboration_comment_and_activity(v2_client):

    post = v2_client.post(

        "/api/platform/v2/analyst-workspace/collaboration/comment",

        json={"case_ref": "RFC10-COLLAB", "text": "Тестовый комментарий"},

    )

    assert post.status_code == 200

    comment_body = post.json()

    assert comment_body["ok"] is True

    assert comment_body["comment"]["text"] == "Тестовый комментарий"



    activity = v2_client.get(

        "/api/platform/v2/analyst-workspace/collaboration/activity?case_ref=RFC10-COLLAB"

    )

    assert activity.status_code == 200

    act_body = activity.json()

    assert act_body["ok"] is True

    assert act_body["count"] >= 1

    assert any(c["text"] == "Тестовый комментарий" for c in act_body["comments"])





def test_collaboration_comment_validation(v2_client):

    resp = v2_client.post(

        "/api/platform/v2/analyst-workspace/collaboration/comment",

        json={"case_ref": "RFC10-COLLAB", "text": ""},

    )

    assert resp.status_code == 422





def test_personalization_api(v2_client):

    put = v2_client.put(

        "/api/platform/v2/analyst-workspace/personalization",

        json={"preferences": {"active_tab": "evidence", "density": "compact"}},

    )

    assert put.status_code == 200

    prefs = put.json()

    assert prefs["ok"] is True

    assert prefs["preferences"]["active_tab"] == "evidence"



    get = v2_client.get("/api/platform/v2/analyst-workspace/personalization")

    assert get.status_code == 200

    assert get.json()["preferences"]["active_tab"] == "evidence"





def test_state_includes_collaboration_after_comment(v2_client):

    v2_client.post(

        "/api/platform/v2/analyst-workspace/collaboration/comment",

        json={"case_ref": "RFC10-STATE-COLLAB", "text": "Комментарий в state"},

    )

    resp = v2_client.get("/api/platform/v2/analyst-workspace/state?case_ref=RFC10-STATE-COLLAB")

    assert resp.status_code == 200

    body = resp.json()

    assert body["collaboration"]["comments_count"] >= 1

    assert len(body["notifications"]) >= 1


