"""RFC-0002 / RFC-0003 debt closure regression tests."""

from __future__ import annotations

import importlib
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

from flowsint_crypto_compliance.attribution.types import EntityLabel
from flowsint_crypto_compliance.platform.v2.canonical import Entity, EntityType
from flowsint_crypto_compliance.platform.v2.entity_resolution import EntityResolutionEngine
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore, get_knowledge_graph_store
from flowsint_crypto_compliance.platform.v2.neo4j_projection import V2_NEO4J_LABELS
from flowsint_crypto_compliance.storage.wallet_neo4j import WalletNeo4jStore


def test_kg_store_env_defaults_postgres(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

    monkeypatch.delenv("FINSKALP_ENTITY_STORE", raising=False)
    ks_mod._kg_store = None
    store = get_knowledge_graph_store()
    assert store._force_memory is False
    ks_mod._kg_store = None


def test_kg_store_explicit_memory(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "postgres")
    ks_mod._kg_store = None
    store = get_knowledge_graph_store(use_memory=True)
    assert store._force_memory is True
    ks_mod._kg_store = None


def test_kg_store_env_memory(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    ks_mod._kg_store = None
    store = get_knowledge_graph_store()
    assert store._force_memory is True
    ks_mod._kg_store = None


def test_entity_label_bridge_sync(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod
    from flowsint_crypto_compliance.platform.v2.entity_label_bridge import sync_entity_label_to_kg
    from flowsint_crypto_compliance.platform.v2.ingest_pipeline import IngestPipeline

    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    ks_mod._kg_store = None
    mem_store = KnowledgeGraphStore(use_memory=True)
    pipeline = IngestPipeline(store=mem_store)

    label = EntityLabel(
        address="T9yD14Nj9j7xAR4oQL3FzRPiRYiH5b8q",
        chain="tron",
        label="Test Exchange",
        category="exchange",
        confidence=0.9,
        source="test",
        tier=2,
        risk_score=5.0,
    )
    with patch(
        "flowsint_crypto_compliance.platform.v2.ingest_pipeline.get_ingest_pipeline",
        return_value=pipeline,
    ):
        result = sync_entity_label_to_kg(label)
    assert result["synced"] is True
    assert result["entity_id"]
    ks_mod._kg_store = None


def test_wallet_neo4j_facade_delegates_projection():
    store = WalletNeo4jStore()
    assert hasattr(store, "_projection")
    mock_conn = MagicMock()
    store._conn = mock_conn
    store._projection.project_entity = MagicMock(return_value={"projected": True})
    store._projection.project_relation = MagicMock(return_value={"projected": True})

    graph = {
        "nodes": [
            {
                "id": "tron:ADDR1",
                "address": "ADDR1",
                "chain": "tron",
                "label": "A",
                "hop": 0,
                "role": "",
            },
            {
                "id": "tron:ADDR2",
                "address": "ADDR2",
                "chain": "tron",
                "label": "B",
                "hop": 1,
                "role": "",
            },
        ],
        "edges": [
            {"from": "tron:ADDR1", "to": "tron:ADDR2", "tx_hash": "0x1"},
        ],
        "risk_annotations": [],
    }
    out = store.persist_fusion_graph(graph, case_ref="CASE-TEST")
    assert out["persisted"] is True
    store._projection.project_entity.assert_called()
    store._projection.project_relation.assert_called()


def test_er_context_scoring_boosts_score():
    engine = EntityResolutionEngine()
    tenant = uuid.uuid4()
    candidate = Entity(
        tenant_id=tenant,
        entity_type=EntityType.PERSON,
        canonical_key="person:john",
        display_name="John",
    )
    base = engine.score_match(candidate, entity_type="person", value="Jane Doe")
    with_ctx = engine.score_match(
        candidate,
        entity_type="person",
        value="Jane Doe",
        context={
            "timestamp": "2026-01-01T00:00:00Z",
            "geo": "RU-MOW",
            "behavior": {"tx_count": 12},
        },
    )
    assert with_ctx.score > base.score
    assert "temporal_context" in with_ctx.explain


def test_auto_versioning_on_upsert():
    store = KnowledgeGraphStore(use_memory=True)
    tenant = uuid.uuid4()
    ent = Entity(
        tenant_id=tenant,
        entity_type=EntityType.WALLET,
        canonical_key="tron:AUTOVER1",
        display_name="Auto version test",
    )
    stored = store.upsert_entity(ent)
    history = store.get_entity_history(stored.id)
    assert len(history) >= 1
    assert history[-1]["version"] == stored.version


def test_shared_routes_module_exists():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    router = create_platform_v2_router()
    paths = {getattr(r, "path", None) for r in router.routes}
    assert "/knowledge-model" in paths
    assert "/entities/{entity_id}" in paths
    assert "/ingest" in paths


def test_neo4j_labels_cover_major_entity_types():
    major = {
        EntityType.WALLET,
        EntityType.CASE,
        EntityType.PERSON,
        EntityType.EMAIL,
        EntityType.PHONE,
        EntityType.DNS_DOMAIN,
        EntityType.TRANSACTION,
        EntityType.TELEGRAM,
        EntityType.SANCTIONS_LIST,
    }
    assert major.issubset(set(V2_NEO4J_LABELS.keys()))


def test_default_fusion_pipeline_rfc0003(monkeypatch):
    from flowsint_crypto_compliance.platform.v2.fusion_pipeline import default_fusion_pipeline

    monkeypatch.delenv("FINSKALP_FUSION_MODE", raising=False)
    pipe = default_fusion_pipeline()
    assert pipe.include_rfc0003 is True

    monkeypatch.setenv("FINSKALP_FUSION_MODE", "legacy")
    pipe_legacy = default_fusion_pipeline()
    assert pipe_legacy.include_rfc0003 is False


def test_hub_ingest_pipeline_alias():
    from flowsint_crypto_compliance.ingestion.pipeline import HubIngestPipeline, IngestPipeline

    assert IngestPipeline is HubIngestPipeline
