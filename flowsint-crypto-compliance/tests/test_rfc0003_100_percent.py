"""RFC-0003 100% readiness — Ch.6 replay, Ch.9 API, Appendix A, store mode."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from flowsint_crypto_compliance.platform.v2.canonical import Entity, EntityType
from flowsint_crypto_compliance.platform.v2.entity_store_mode import (
    entity_store_mode,
    is_memory_store_mode,
    warn_if_memory_store_in_production,
)
from flowsint_crypto_compliance.platform.v2.graph_history import GraphHistoryService
from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore
from flowsint_crypto_compliance.platform.v2.pipeline_chain import (
    APPENDIX_A_CHAIN,
    PipelineChainOrchestrator,
    pipeline_chain_manifest,
)


@pytest.fixture
def memory_store() -> KnowledgeGraphStore:
    return KnowledgeGraphStore(use_memory=True)


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000099")


def test_appendix_a_chain_manifest():
    m = pipeline_chain_manifest()
    assert m["appendix"] == "A"
    assert len(m["stages"]) == len(APPENDIX_A_CHAIN)
    assert APPENDIX_A_CHAIN[-1] == "report"


@pytest.mark.asyncio
async def test_pipeline_chain_orchestrator(memory_store: KnowledgeGraphStore, tenant_id: uuid.UUID, monkeypatch):
    from flowsint_crypto_compliance.platform.v2.ingest_pipeline import IngestPipeline

    pipe = IngestPipeline(store=memory_store)
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.ingest_pipeline.get_ingest_pipeline",
        lambda: pipe,
    )

    async def _fast_fusion_run(*_a, **_k):
        return []

    class _FastPipe:
        async def run(self, *_a, **_k):
            return []

    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.fusion_pipeline.default_fusion_pipeline",
        lambda: _FastPipe(),
    )
    class _StubWS:
        def attach_investigation(self, **_kwargs):
            return None

    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.investigation_workspace.InvestigationWorkspace",
        _StubWS,
    )
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import KnowledgeGraphService
    import flowsint_crypto_compliance.platform.v2.intelligence.orchestrator as intel_orch_mod

    kg = KnowledgeGraphService(store=memory_store)
    intel_orch_mod._orchestrator = None
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.intelligence.orchestrator.get_ingest_pipeline",
        lambda: pipe,
    )
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.intelligence.orchestrator.get_knowledge_graph_service",
        lambda: kg,
    )

    orch = PipelineChainOrchestrator()

    result = await orch.run_investigation_chain(
        tenant_id=tenant_id,
        investigation_id=uuid.uuid4(),
        case_ref="CASE-TEST-001",
        address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        chain="tron",
        screening={"risk_score": 42, "risk_level": "medium", "findings": []},
        mentions=[],
    )
    assert result.ok
    assert "analytics" in result.stages_completed
    assert result.explain.get("analytics", {}).get("engines_run")
    assert "report" in result.stages_completed
    assert result.report_refs.get("case_ref") == "CASE-TEST-001"


def test_reconstruct_graph_at_from_versions(memory_store: KnowledgeGraphStore, tenant_id: uuid.UUID):
    ent = Entity(
        tenant_id=tenant_id,
        entity_type=EntityType.WALLET,
        canonical_key="tron:abc",
        display_name="v1",
        version=1,
    )
    stored = memory_store.upsert_entity(ent)
    ent2 = stored.model_copy(update={"display_name": "v2", "version": 2})
    memory_store.upsert_entity(ent2)

    history = GraphHistoryService(store=memory_store)
    as_of = datetime.now(timezone.utc)
    snap = history.reconstruct_graph_at(tenant_id, as_of)
    assert snap["reconstruction"] in (
        "entity_relation_versions_and_events",
        "stored_snapshot",
        "entity_relation_versions",
    )
    assert snap["entity_count"] >= 1


def test_compare_entity_versions_api(memory_store: KnowledgeGraphStore, tenant_id: uuid.UUID):
    ent = Entity(
        tenant_id=tenant_id,
        entity_type=EntityType.PERSON,
        canonical_key="person:test",
        display_name="A",
        version=1,
    )
    stored = memory_store.upsert_entity(ent)
    memory_store.upsert_entity(stored.model_copy(update={"display_name": "B", "version": 2}))

    history = GraphHistoryService(store=memory_store)
    cmp = history.compare_versions(stored.id, 1, 2)
    assert "error" not in cmp
    assert cmp.get("display_name_changed") is True


def test_export_evidence_base(memory_store: KnowledgeGraphStore, tenant_id: uuid.UUID):
    from flowsint_crypto_compliance.platform.v2.canonical import Evidence, TrustLevel

    ev = Evidence(
        tenant_id=tenant_id,
        source_type="test",
        content_hash="abc123",
        trust=TrustLevel(),
        payload={"case_ref": "CASE-X"},
    )
    memory_store.store_evidence(ev)
    data = memory_store.export_evidence_base(tenant_id, case_ref="CASE-X")
    assert data["evidence_count"] >= 1


def test_entity_store_mode_default_postgres(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("FINSKALP_ENTITY_STORE", raising=False)
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "1")
    assert entity_store_mode() == "postgres"
    assert not is_memory_store_mode()


def test_entity_store_mode_explicit_memory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    assert is_memory_store_mode()


def test_warn_memory_mode_no_crash(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    monkeypatch.setenv("TESTING", "1")
    warn_if_memory_store_in_production()
    assert "ВНИМАНИЕ" not in capsys.readouterr().err


def test_create_graph_snapshot(memory_store: KnowledgeGraphStore, tenant_id: uuid.UUID):
    ent = Entity(
        tenant_id=tenant_id,
        entity_type=EntityType.CASE,
        canonical_key="case:snap",
        display_name="Snap test",
    )
    memory_store.upsert_entity(ent)
    kg = get_knowledge_graph_service()
    kg._store = memory_store  # type: ignore[method-assign]
    kg._history = GraphHistoryService(store=memory_store)
    snap = kg.create_graph_snapshot(tenant_id, changed_by="test")
    assert snap["entity_count"] >= 1
    assert snap.get("created_by") == "test"


def test_gateway_handlers_importable():
    from flowsint_crypto_compliance.platform.v2.gateway import (
        compare_entity_versions,
        export_evidence_base,
        get_pipeline_chain_manifest,
        get_relation_history,
    )

    assert callable(compare_entity_versions)
    assert callable(export_evidence_base)
    assert callable(get_relation_history)
    m = get_pipeline_chain_manifest()
    assert m["rfc"] == "RFC-0003"


def test_routes_module_has_new_endpoints():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    router = create_platform_v2_router()
    paths = {getattr(r, "path", "") for r in router.routes}
    assert "/entities/{entity_id}/compare" in paths
    assert "/evidence/export" in paths
    assert "/pipeline-chain" in paths
    assert "/graph/snapshot" in paths
    assert "/relations/{relation_id}/history" in paths
