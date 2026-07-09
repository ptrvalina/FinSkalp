"""RFC-0014 Intelligence Collection Framework — tests."""

from __future__ import annotations

import inspect
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.connectors.types import SourceQualityProfile
from flowsint_crypto_compliance.platform.v2.icf.collector import ICFCollector
from flowsint_crypto_compliance.platform.v2.icf.evidence import EvidenceGenerator
from flowsint_crypto_compliance.platform.v2.icf.manifest import icf_manifest
from flowsint_crypto_compliance.platform.v2.icf.orchestrator import run_icf_pipeline
from flowsint_crypto_compliance.platform.v2.icf.quality import QualityEngine
from flowsint_crypto_compliance.platform.v2.icf.scheduler import get_collection_scheduler
from flowsint_crypto_compliance.platform.v2.icf.types import ICFStage, SourceCategory
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


def test_icf_manifest_stages():
    m = icf_manifest()
    assert m["rfc"] == "RFC-0014"
    assert m["schema_version"] == "2.0.0"
    assert len(m["pipeline"]) == 8
    assert ICFStage.SOURCE.value in m["pipeline"]
    assert ICFStage.KNOWLEDGE_GRAPH.value in m["pipeline"]
    assert len(m["source_categories"]["categories"]) == len(SourceCategory)
    assert m["collector_count"] >= 30


def test_icf_pipeline_all_stages():
    async def _run():
        return await run_icf_pipeline(
            connector_id="chain.tron",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            query={"address": "TTestICFCollector", "chain": "tron"},
            case_ref="RFC14-TEST",
            publish=True,
        )

    import asyncio

    result = asyncio.run(_run())
    assert result.ok
    assert ICFStage.SOURCE.value in result.stages
    assert ICFStage.COLLECTOR.value in result.stages
    assert ICFStage.NORMALIZER.value in result.stages
    assert ICFStage.VALIDATOR.value in result.stages
    assert ICFStage.ENTITY_EXTRACTOR.value in result.stages
    assert ICFStage.EVIDENCE_GENERATOR.value in result.stages
    assert ICFStage.FUSION.value in result.stages
    assert ICFStage.KNOWLEDGE_GRAPH.value in result.stages
    assert len(result.normalized) >= 1
    assert len(result.evidence) >= 1


def test_entity_extractor_stage():
    from flowsint_crypto_compliance.platform.v2.icf.entity_extractor import get_entity_extractor

    extractor = get_entity_extractor()
    entities = extractor.extract_from_records(
        [
            {
                "entity_type": "text",
                "entity_value": "contact@test.ru wallet TTestICFCollector123456789012345678901",
                "confidence": 0.7,
            }
        ],
        connector_id="test.extractor",
    )
    types = {e["entity_type"] for e in entities}
    assert "email" in types or "crypto_address" in types or "domain" in types
    assert all("provenance" in e for e in entities)


def test_evidence_generator_fields():
    gen = EvidenceGenerator()
    tid = uuid.UUID("00000000-0000-0000-0000-000000000099")
    rows = gen.generate(
        [{"entity_type": "crypto_address", "entity_value": "TTestEvidence", "confidence": 0.8}],
        tenant_id=tid,
        connector_id="chain.tron",
        case_ref="RFC14-EV",
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
    ):
        assert field in ev
    assert ev["version"] == "2.0"
    assert len(ev["content_hash"]) == 64


def test_quality_engine_score():
    engine = QualityEngine()
    score = engine.score(
        profile=SourceQualityProfile(
            provenance="official",
            official=True,
            completeness=0.9,
            stability=0.85,
            trust_level=0.8,
        ),
        records=[{"entity_type": "crypto_address", "entity_value": "TTest", "payload": {}}],
        validation_errors=[],
    )
    assert 0.0 < score.composite <= 1.0
    assert score.completeness > 0
    assert score.structure > 0


def test_collector_architectural_constraints():
    import flowsint_crypto_compliance.platform.v2.icf.collector as collector_mod

    source = inspect.getsource(collector_mod)
    constraints = ICFCollector.architectural_constraints()
    assert "direct_knowledge_graph_mutation" in constraints["forbidden"]
    assert "from flowsint_crypto_compliance.platform.v2.knowledge_graph" not in source
    assert "from flowsint_crypto_compliance.platform.v2.knowledge_store" not in source
    assert "from flowsint_crypto_compliance.platform.v2.entity_resolution" not in source
    assert "get_knowledge_graph" not in source
    for mod in constraints["forbidden_modules"]:
        assert mod.split(".")[-1] not in collector_mod.__dict__


def test_icf_api_manifest_and_collect(v2_client):
    manifest = v2_client.get("/api/platform/v2/icf/manifest")
    assert manifest.status_code == 200
    body = manifest.json()
    assert body["rfc"] == "RFC-0014"
    assert "sdk" in body
    assert "security" in body

    collect = v2_client.post(
        "/api/platform/v2/icf/collect",
        json={
            "connector_id": "chain.eth",
            "query": {"address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", "chain": "eth"},
            "publish": False,
        },
    )
    assert collect.status_code == 200
    data = collect.json()
    assert data["connector_id"] == "chain.eth"
    assert "stages" in data


def test_scheduler_register():
    scheduler = get_collection_scheduler()
    job = scheduler.schedule(
        connector_id="chain.btc",
        query={"address": "bc1qtest", "chain": "btc"},
        case_ref="RFC14-SCHED",
        interval_seconds=300,
    )
    status = scheduler.status()
    assert status["total_jobs"] >= 1
    assert any(j["job_id"] == job.job_id for j in status["jobs"])
