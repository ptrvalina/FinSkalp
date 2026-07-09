"""RFC-0004 Intelligence Platform tests."""

from __future__ import annotations

import uuid

import pytest

from flowsint_crypto_compliance.platform.v2.intelligence import (
    get_intelligence_orchestrator,
    intelligence_platform_manifest,
    run_intelligence_analysis,
)
from flowsint_crypto_compliance.platform.v2.intelligence.engines import (
    AttributionIntelligenceEngine,
    BlockchainIntelligenceEngine,
    OsintIntelligenceEngine,
    RecommendationIntelligenceEngine,
    RiskIntelligenceEngine,
)
from flowsint_crypto_compliance.platform.v2.intelligence.types import IntelligenceContext
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000099")


@pytest.fixture
def memory_store() -> KnowledgeGraphStore:
    return KnowledgeGraphStore(use_memory=True)


def test_intelligence_manifest_lists_11_engines():
    m = intelligence_platform_manifest()
    assert m["rfc"] == "RFC-0004"
    assert len(m["engines"]) == 11
    ids = {e["engine"] for e in m["engines"]}
    assert "blockchain" in ids
    assert "recommendation" in ids


def test_blockchain_engine_detects_activity(tenant_id: uuid.UUID):
    engine = BlockchainIntelligenceEngine()
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        address="TXyz123",
        chain="tron",
        screening={"onchain_summary": {"inbound_count": 5, "outbound_count": 3}},
    )
    result = engine.analyze(ctx)
    assert any(f.code == "TX_ACTIVITY" for f in result.findings)


def test_osint_engine_categorizes_mentions(tenant_id: uuid.UUID):
    engine = OsintIntelligenceEngine()
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        mentions=[
            {"entity_type": "domain", "entity_value": "example.com", "source_type": "scalpel", "confidence": 0.6},
            {"entity_type": "telegram", "entity_value": "@user", "source_type": "telegram", "confidence": 0.7},
        ],
    )
    result = engine.analyze(ctx)
    assert len(result.findings) == 2
    assert "categories_seen" in result.explain


def test_risk_engine_aggregates_findings(tenant_id: uuid.UUID):
    engine = RiskIntelligenceEngine()
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        address="addr",
        screening={
            "risk_score": 40,
            "_intel_findings": [
                {"code": "MIXER_OR_SANCTIONS", "severity": "high", "confidence": 0.9},
                {"code": "OSINT_MENTION", "severity": "info", "confidence": 0.5},
            ],
        },
    )
    result = engine.analyze(ctx)
    assert result.explain["aggregate_risk_score"] > 40


def test_recommendation_engine_produces_steps(tenant_id: uuid.UUID):
    engine = RecommendationIntelligenceEngine()
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        case_ref="FSK-TEST-001",
        screening={"_aggregate_risk": 60, "_intel_findings": [{"code": "SHARED_IDENTIFIER"}]},
    )
    result = engine.analyze(ctx)
    recs = result.findings[0].explain["recommendations"]
    assert len(recs) >= 2
    assert any("OSINT" in r["action_ru"] for r in recs)


def test_orchestrator_runs_all_engines(tenant_id: uuid.UUID, memory_store: KnowledgeGraphStore):
    from flowsint_crypto_compliance.platform.v2.ingest_pipeline import IngestPipeline
    from flowsint_crypto_compliance.platform.v2.intelligence.orchestrator import IntelligenceOrchestrator
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import KnowledgeGraphService
    from flowsint_crypto_compliance.platform.v2.intelligence.types import IntelligenceContext

    orch = IntelligenceOrchestrator()
    orch._ingest = IngestPipeline(store=memory_store)
    orch._kg = KnowledgeGraphService(store=memory_store)

    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        address="TAddr123456789",
        chain="tron",
        case_ref="CASE-1",
        screening={"risk_score": 30, "onchain_summary": {"inbound_count": 2, "outbound_count": 1}},
        mentions=[{"entity_type": "domain", "entity_value": "test.com", "confidence": 0.5}],
    )
    result = orch.run(ctx, publish=True)
    assert result.ok
    assert len(result.engines_run) == 11
    assert result.aggregate_risk_score >= 0
    assert isinstance(result.recommendations, list)


def test_attribution_engine_from_dict(tenant_id: uuid.UUID):
    engine = AttributionIntelligenceEngine()
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        attribution={
            "labels": {
                "TAddr": {
                    "address": "TAddr",
                    "chain": "tron",
                    "label": "Test Exchange",
                    "category": "exchange",
                    "confidence": 0.8,
                    "source": "sovereign_registry",
                    "tier": 1,
                }
            }
        },
    )
    result = engine.analyze(ctx)
    assert any(f.code == "ATTRIBUTION_HYPOTHESIS" for f in result.findings)


def test_routes_include_intelligence_manifest():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    router = create_platform_v2_router()
    paths = [getattr(r, "path", "") for r in router.routes]
    assert "/intelligence/manifest" in paths
    assert "/intelligence/analyze" in paths


def test_get_intelligence_orchestrator_singleton():
    a = get_intelligence_orchestrator()
    b = get_intelligence_orchestrator()
    assert a is b
