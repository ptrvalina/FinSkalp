"""RFC-0012 Blockchain Intelligence Framework — tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.chains.base import InMemoryChainAdapter, OnChainTransfer
from flowsint_crypto_compliance.platform.v2.blockchain_intelligence import (
    blockchain_intelligence_manifest,
    get_blockchain_intelligence_service,
)
from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.analytics import (
    cluster_counterparties,
    profile_address,
)
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore
from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router
from flowsint_types.fiat_crypto import Chain


@pytest.fixture(autouse=True)
def memory_env(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.blockchain_intelligence.service as svc_mod
    import flowsint_crypto_compliance.platform.v2.knowledge_graph as kg_mod
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

    svc_mod._service = None
    kg_mod._kg_service = None
    ks_mod._kg_store = None
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")

    mem = KnowledgeGraphStore(use_memory=True)
    kg = kg_mod.KnowledgeGraphService(store=mem)
    ks_mod._kg_store = mem

    def _kg():
        return kg

    def _mem_store(*_a, **_k):
        return mem

    for target in (
        "flowsint_crypto_compliance.platform.v2.knowledge_store.get_knowledge_graph_store",
        "flowsint_crypto_compliance.platform.v2.knowledge_graph.get_knowledge_graph_store",
        "flowsint_crypto_compliance.platform.v2.knowledge_graph.get_knowledge_graph_service",
    ):
        monkeypatch.setattr(target, _kg if "service" in target else _mem_store)

    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.intelligence.blockchain_capabilities.get_chain_adapter_by_key",
        lambda chain_key, use_memory=False: InMemoryChainAdapter(
            Chain.TRON,
            [
                OnChainTransfer(
                    chain=Chain.TRON,
                    tx_hash="tx1",
                    source="TSender",
                    target="TTarget",
                    asset="TRX",
                    amount=100.0,
                    timestamp="1700000000",
                )
            ],
        ),
    )
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.event_bus.PlatformEventBus._persist_postgres",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.neo4j_projection.Neo4jUnifiedProjection.project_entity",
        lambda *a, **k: {"projected": False},
    )
    yield


@pytest.fixture
def v2_client():
    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_blockchain_intelligence_manifest():
    m = blockchain_intelligence_manifest()
    assert m["rfc"] == "RFC-0012"
    assert len(m["canonical_entities"]) == 10
    assert len(m["supported_networks"]) == 7
    assert len(m["pipeline_stages"]) == 8
    assert m["explainable"] is True


def test_profile_and_clustering():
    import asyncio

    adapter = InMemoryChainAdapter(
        Chain.TRON,
        [
            OnChainTransfer(Chain.TRON, "tx1", "A", "B", "TRX", 1.0, "1"),
            OnChainTransfer(Chain.TRON, "tx2", "C", "B", "TRX", 2.0, "2"),
        ],
    )
    neighborhood = asyncio.run(adapter.get_neighborhood("B"))
    profile = profile_address(neighborhood)
    assert profile["inbound_count"] == 2
    clusters = cluster_counterparties(neighborhood)
    assert clusters[0]["analyst_verifiable"] is True


@pytest.mark.asyncio
async def test_analyze_address_service():
    result = await get_blockchain_intelligence_service().analyze_address(
        address="TTestAddress",
        chain="tron",
        case_ref="RFC12-TEST",
        use_memory=True,
    )
    assert result["ok"] is True
    assert result["profile"]["chain"] == "tron"
    assert "explain" in result
    assert result["latency_ms"] >= 0


def test_blockchain_intelligence_manifest_api(v2_client):
    resp = v2_client.get("/api/platform/v2/blockchain-intelligence/manifest")
    assert resp.status_code == 200
    assert resp.json()["rfc"] == "RFC-0012"


def test_blockchain_intelligence_analyze_api(v2_client):
    resp = v2_client.post(
        "/api/platform/v2/blockchain-intelligence/analyze",
        json={"address": "TApiTest", "chain": "tron", "case_ref": "RFC12-API"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["flow_graph"]["nodes"]
