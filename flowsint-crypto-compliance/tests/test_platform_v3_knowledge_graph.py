"""Tests for RFC-0003 Unified Data Model & Knowledge Graph v2.0."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from flowsint_crypto_compliance.platform.v2.canonical import (
    EntityType,
    KnowledgeRelation,
    RelationWithoutEvidenceError,
    normalize_entity_type,
)
from flowsint_crypto_compliance.platform.v2.confidence_model import calculate_confidence
from flowsint_crypto_compliance.platform.v2.entity_resolution import (
    EntityResolutionEngine,
    MatchSignal,
    MergeDecision,
    SIGNAL_WEIGHTS,
)
from flowsint_crypto_compliance.platform.v2.graph_history import GraphHistoryService
from flowsint_crypto_compliance.platform.v2.ingest_pipeline import IngestPipeline
from flowsint_crypto_compliance.platform.v2.knowledge_graph import knowledge_model_manifest
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore
from flowsint_crypto_compliance.platform.v2.relation_types import RelationType

TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_entity_type_taxonomy():
    manifest = knowledge_model_manifest()
    values = {et["value"] for et in manifest["entity_types"]}
    assert "person" in values
    assert "company" in values
    assert "blockchain_address" in values
    assert "dns_domain" in values
    assert "sanctions" in values
    assert "telegram" in values
    # Backward-compat aliases
    assert normalize_entity_type("organization") == EntityType.COMPANY
    assert normalize_entity_type("domain") == EntityType.DNS_DOMAIN
    assert normalize_entity_type("crypto_address") == EntityType.BLOCKCHAIN_ADDRESS
    assert EntityType.ORGANIZATION.value == "organization"
    assert EntityType.DOMAIN.value == "domain"


def test_relation_requires_evidence():
    store = KnowledgeGraphStore(use_memory=True)
    a_id = uuid.uuid4()
    b_id = uuid.uuid4()
    with pytest.raises(RelationWithoutEvidenceError, match="доказательства"):
        store.link_relation(
            a_id,
            b_id,
            "related_to",
            tenant_id=TENANT,
            evidence_ids=[],
            require_evidence=True,
        )

    ev_id = uuid.uuid4()
    rel = KnowledgeRelation(
        tenant_id=TENANT,
        from_entity_id=a_id,
        to_entity_id=b_id,
        relation_type=RelationType.RELATED_TO.value,
        evidence_ids=[ev_id],
    )
    rel_id = store.link_relation(rel, require_evidence=True)
    assert rel_id == rel.id


def test_relation_flagged_without_evidence_model():
    rel = KnowledgeRelation(
        tenant_id=TENANT,
        from_entity_id=uuid.uuid4(),
        to_entity_id=uuid.uuid4(),
        relation_type="related_to",
        evidence_ids=[],
    )
    assert rel.flagged_without_evidence is True
    assert rel.is_valid_fact() is False


def test_entity_resolution_weighted_scoring():
    engine = EntityResolutionEngine()
    store = KnowledgeGraphStore(use_memory=True)

    first = engine.resolve_signal(
        tenant_id=TENANT,
        entity_type="email",
        value="test@example.com",
        confidence=0.8,
    )
    store.upsert_entity(first)

    result = engine.resolve_with_scoring(
        tenant_id=TENANT,
        entity_type="email",
        value="test@example.com",
        store=store,
        confidence=0.8,
    )
    assert result.decision in (MergeDecision.MERGE, MergeDecision.LINK, MergeDecision.CREATE)
    assert 0.0 < result.confidence <= 1.0
    assert "decision" in result.explain
    assert SIGNAL_WEIGHTS[MatchSignal.EMAIL] > SIGNAL_WEIGHTS[MatchSignal.NAME]


def test_confidence_model():
    cb = calculate_confidence(
        sources=["sanctions", "osint"],
        signals=[
            {"value": "TAddr123", "normalized_value": "TAddr123"},
            {"value": "TAddr123", "normalized_value": "TAddr123"},
        ],
        trust_levels=[0.9, 0.5],
        discovered_at=datetime.now(timezone.utc),
        base_confidence=0.7,
    )
    assert 0.0 < cb.composite <= 1.0
    assert cb.independent_sources >= 2
    assert "formula" in cb.explain
    assert cb.source_quality > 0.4


def test_ingest_mandatory_path():
    store = KnowledgeGraphStore(use_memory=True)
    pipeline = IngestPipeline(store=store)

    result = pipeline.ingest(
        tenant_id=TENANT,
        source_type="osint",
        entity_type="domain",
        entity_value="evil.example",
        payload={"url": "https://evil.example"},
        confidence=0.72,
    )
    assert result.ok
    assert result.entity_id is not None
    assert result.evidence_id is not None
    assert result.stages_completed == [
        "source_to_event",
        "normalize",
        "entity_resolution",
        "knowledge_graph",
        "evidence",
    ]
    ent = store.get_entity(result.entity_id)
    assert ent is not None
    assert ent.entity_type == EntityType.DOMAIN


def test_graph_history_and_neighbors():
    store = KnowledgeGraphStore(use_memory=True)
    history = GraphHistoryService(store=store)
    engine = EntityResolutionEngine()

    a = engine.resolve_signal(tenant_id=TENANT, entity_type="phone", value="+79991234567")
    b = engine.resolve_signal(tenant_id=TENANT, entity_type="email", value="a@b.c")
    a_stored = store.upsert_entity(a)
    b_stored = store.upsert_entity(b)
    history.record_entity_version(a_stored)
    history.record_entity_version(b_stored)

    ev_id = uuid.uuid4()
    store.store_evidence(
        __import__(
            "flowsint_crypto_compliance.platform.v2.canonical", fromlist=["Evidence"]
        ).Evidence(
            id=ev_id,
            tenant_id=TENANT,
            source_type="test",
            content_hash="abc123",
        )
    )
    rel = KnowledgeRelation(
        tenant_id=TENANT,
        from_entity_id=a_stored.id,
        to_entity_id=b_stored.id,
        relation_type=RelationType.RELATED_TO.value,
        evidence_ids=[ev_id],
    )
    store.link_relation(rel)
    history.record_relation_version(rel)

    neighbors = store.get_neighbors(a_stored.id)
    assert len(neighbors) >= 1
    assert neighbors[0]["relation_type"] == RelationType.RELATED_TO.value

    hist = history.get_entity_history(a_stored.id)
    assert len(hist) >= 1

    at_v1 = history.get_entity_at_version(a_stored.id, a_stored.version)
    assert at_v1 is not None
    assert at_v1.canonical_key == a_stored.canonical_key


def test_knowledge_model_manifest_rules():
    manifest = knowledge_model_manifest()
    assert manifest["rfc"] == "RFC-0003"
    assert manifest["rules"]["relation_requires_evidence"] is True
    assert "доказательства" in manifest["rules"]["message_ru"]
    rel_values = {r["value"] for r in manifest["relation_types"]}
    assert RelationType.OWNS.value in rel_values
    assert RelationType.SAME_CLUSTER.value in rel_values
