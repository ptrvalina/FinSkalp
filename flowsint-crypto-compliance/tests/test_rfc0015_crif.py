"""RFC-0015 Compliance & Registry Intelligence Framework — tests."""

from __future__ import annotations

import inspect
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.crif.connector import RegistryConnector
from flowsint_crypto_compliance.platform.v2.crif.evidence import EvidenceGenerator
from flowsint_crypto_compliance.platform.v2.crif.manifest import crif_manifest
from flowsint_crypto_compliance.platform.v2.crif.orchestrator import run_crif_pipeline
from flowsint_crypto_compliance.platform.v2.crif.rules_engine import get_rules_engine
from flowsint_crypto_compliance.platform.v2.crif.sanctions import screen_sanctions
from flowsint_crypto_compliance.platform.v2.crif.types import CRIFStage, CanonicalEntityType, RegistrySourceCategory
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore


@pytest.fixture(autouse=True)
def memory_env(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.knowledge_graph as kg_mod
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

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


def test_crif_manifest_stages_and_entity_types():
    m = crif_manifest()
    assert m["rfc"] == "RFC-0015"
    assert m["schema_version"] == "2.0.0"
    assert len(m["pipeline"]) == 9
    assert CRIFStage.REGISTRY_SOURCE.value in m["pipeline"]
    assert CRIFStage.INVESTIGATION_WORKSPACE.value in m["pipeline"]
    assert len(m["source_categories"]["categories"]) == len(RegistrySourceCategory)
    assert CanonicalEntityType.ORGANIZATION.value in m["canonical_entity_types"]
    assert m["connector_count"] >= 4


def test_crif_pipeline_all_stages():
    async def _run():
        return await run_crif_pipeline(
            connector_id="registry.sovereign",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            query={"entity_value": "Test Sovereign Org", "organization": "Test Sovereign Org"},
            case_ref="RFC15-TEST",
            organization_key="Test Sovereign Org",
            publish=True,
        )

    import asyncio

    result = asyncio.run(_run())
    assert result.ok
    assert CRIFStage.REGISTRY_SOURCE.value in result.stages
    assert CRIFStage.REGISTRY_CONNECTOR.value in result.stages
    assert CRIFStage.NORMALIZER.value in result.stages
    assert CRIFStage.SCHEMA_VALIDATOR.value in result.stages
    assert CRIFStage.ENTITY_RESOLVER.value in result.stages
    assert CRIFStage.EVIDENCE_GENERATOR.value in result.stages
    assert CRIFStage.KNOWLEDGE_GRAPH.value in result.stages
    assert CRIFStage.RISK_ENGINE.value in result.stages
    assert CRIFStage.INVESTIGATION_WORKSPACE.value in result.stages
    assert len(result.normalized) >= 1
    assert len(result.evidence) >= 1
    assert len(result.compliance_checks) >= 1


def test_sanctions_fuzzy_match_requires_analyst():
    matches = screen_sanctions("ACME Sanctns Corp")
    assert len(matches) >= 1
    fuzzy = [m for m in matches if m["match_type"] in ("fuzzy", "transliteration", "probable")]
    assert fuzzy
    assert all(m["requires_analyst_confirmation"] for m in fuzzy)


def test_rules_engine_fires_compliance_event():
    engine = get_rules_engine()
    events = engine.evaluate({"license_status": "revoked", "operations_active": True})
    assert len(events) == 1
    assert events[0].event_type == "ComplianceEvent"
    assert events[0].rule_id == "license_lost_active_ops"


def test_connector_architectural_constraints():
    import flowsint_crypto_compliance.platform.v2.crif.connector as connector_mod

    source = inspect.getsource(connector_mod)
    constraints = RegistryConnector.architectural_constraints()
    assert "direct_knowledge_graph_mutation" in constraints["forbidden"]
    assert "direct_risk_scoring" in constraints["forbidden"]
    assert "from flowsint_crypto_compliance.platform.v2.knowledge_graph" not in source
    assert "from flowsint_crypto_compliance.platform.v2.knowledge_store" not in source
    assert "get_knowledge_graph" not in source
    for mod in constraints["forbidden_modules"]:
        assert mod.split(".")[-1] not in connector_mod.__dict__


def test_crif_api_manifest_and_check(v2_client):
    manifest = v2_client.get("/api/platform/v2/crif/manifest")
    assert manifest.status_code == 200
    body = manifest.json()
    assert body["rfc"] == "RFC-0015"
    assert "sdk" in body
    assert "security" in body

    check = v2_client.post(
        "/api/platform/v2/crif/check",
        json={
            "connector_id": "registry.ofac",
            "query": {"entity_value": "Test Organization", "organization": "Test Organization"},
            "organization_key": "Test Organization",
            "publish": False,
        },
    )
    assert check.status_code == 200
    data = check.json()
    assert data["connector_id"] == "registry.ofac"
    assert "stages" in data


def test_change_history_timeline():
    async def _run():
        return await run_crif_pipeline(
            connector_id="registry.sovereign",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            query={"entity_value": "History Test Org"},
            organization_key="History Test Org",
            publish=False,
        )

    import asyncio

    asyncio.run(_run())
    from flowsint_crypto_compliance.platform.v2.crif.change_history import get_change_history_store

    timeline = get_change_history_store().get_timeline("History Test Org")
    assert len(timeline) >= 1
    assert timeline[0]["organization_key"] == "History Test Org"


def test_evidence_generator_compliance_fields():
    gen = EvidenceGenerator()
    tid = uuid.UUID("00000000-0000-0000-0000-000000000099")
    rows = gen.generate(
        [{"entity_type": "Organization", "entity_value": "Test Org", "confidence": 0.8}],
        tenant_id=tid,
        connector_id="registry.sovereign",
        case_ref="RFC15-EV",
    )
    assert len(rows) == 1
    ev = rows[0]
    for field in (
        "id",
        "source",
        "discovered_at",
        "acquisition_method",
        "content_hash",
        "version",
        "trust_level",
        "registry_source",
    ):
        assert field in ev
    assert ev["version"] == "2.0"
    assert len(ev["content_hash"]) == 64
