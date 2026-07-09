"""RFC-0007 Integration & Connectors — tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.connectors import get_connector_registry
from flowsint_crypto_compliance.platform.v2.connectors.base import BaseConnector
from flowsint_crypto_compliance.platform.v2.connectors.registry import ConnectorRegistry
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


def test_connectors_manifest():
    m = get_connector_registry().manifest()
    assert m["rfc"] == "RFC-0007"
    assert m["total"] >= 30
    assert "blockchain" in m["categories"]
    assert "osint" in m["categories"]
    assert len(m["contract_methods"]) == 8


def test_blockchain_connectors_seven_plus():
    reg = get_connector_registry()
    chains = reg.list_descriptors()
    blockchain = [c for c in chains if c.category.value == "blockchain" and c.status.value == "production"]
    assert len(blockchain) >= 7


def test_connector_contract_lifecycle():
    reg = ConnectorRegistry()
    from flowsint_crypto_compliance.platform.v2.connectors.registry import _bootstrap_connectors

    _bootstrap_connectors(reg)
    connector = reg.create("chain.tron")
    assert isinstance(connector, BaseConnector)

    async def _run():
        return await connector.run_pipeline(
            query={"address": "TTestConnector", "chain": "tron"},
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            case_ref="RFC7-TEST",
            publish=False,
        )

    import asyncio

    result = asyncio.run(_run())
    assert result.ok
    assert "validate" in result.stages
    assert "normalize" in result.stages
    assert len(result.normalized) == 1


def test_connectors_api(v2_client):
    resp = v2_client.get("/api/platform/v2/connectors/manifest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rfc"] == "RFC-0007"
    assert "sdk" in body
    assert "security" in body

    health = v2_client.post("/api/platform/v2/connectors/chain.btc/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    collect = v2_client.post(
        "/api/platform/v2/connectors/chain.eth/collect",
        json={"query": {"address": "0xabc", "chain": "eth"}, "publish": False},
    )
    assert collect.status_code == 200
    assert collect.json()["ok"] is True
