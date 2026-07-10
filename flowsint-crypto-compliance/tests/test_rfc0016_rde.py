"""RFC-0016 Risk & Decision Engine — tests."""

from __future__ import annotations

import inspect
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.rde.confidence import calculate_confidence
from flowsint_crypto_compliance.platform.v2.rde.constraints import rde_architectural_constraints
from flowsint_crypto_compliance.platform.v2.rde.manifest import rde_manifest
from flowsint_crypto_compliance.platform.v2.rde.orchestrator import run_rde_assessment
from flowsint_crypto_compliance.platform.v2.rde.risk_levels import map_score_to_risk_level
from flowsint_crypto_compliance.platform.v2.rde.rules_engine import get_rules_engine
from flowsint_crypto_compliance.platform.v2.rde.types import FactorGroup, RDEStage, RiskLevel
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


@pytest.fixture
def sample_signals():
    return {
        "blockchain_signals": {
            "transaction_count": 25,
            "volume_usd": 250_000,
            "mixer_exposure": True,
            "risk_flags": ["high_volume", "mixer"],
            "address": "TXyz123",
        },
        "registry_signals": {
            "sanctioned": False,
            "license_status": "valid",
            "org_status": "active",
            "organization": "Test Org RDE",
            "check_failures": 0,
        },
        "osint_signals": {
            "mentions": [
                {"source": "news", "sentiment": 0.2, "title": "Negative coverage"},
                {"source": "forum", "sentiment": 0.3, "title": "Suspicious activity"},
            ],
            "source_count": 2,
        },
        "graph_signals": {
            "neighbors": [
                {"relation_type": "OWNS", "confidence": 0.8, "entity": {"canonical_key": "TXyz123"}},
                {"relation_type": "SANCTIONED", "confidence": 0.3, "entity": {"canonical_key": "BadActor"}},
            ],
            "depth": 2,
        },
        "evidence_signals": {
            "items": [
                {"entity_value": "Test Org RDE", "status": "verified", "confidence": 0.85, "title": "License doc"},
                {"entity_value": "Test Org RDE", "status": "verified", "confidence": 0.9, "title": "Registration"},
            ],
        },
    }


def test_rde_manifest_stages_and_factor_groups():
    m = rde_manifest()
    assert m["rfc"] == "RFC-0016"
    assert m["schema_version"] == "2.0.0"
    assert len(m["pipeline"]) == 8
    assert RDEStage.FACT_ACQUISITION.value in m["pipeline"]
    assert RDEStage.DELIVER.value in m["pipeline"]
    assert len(m["factor_groups"]) == len(FactorGroup)
    assert FactorGroup.BLOCKCHAIN.value in m["factor_groups"]
    assert RiskLevel.CRITICAL.value in m["risk_levels"]
    assert "sdk" in m
    assert "security" in m


def test_rde_full_assessment_pipeline(sample_signals):
    async def _run():
        return await run_rde_assessment(
            entity_key="Test Org RDE",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            case_ref="RFC16-TEST",
            signals=sample_signals,
        )

    import asyncio

    result = asyncio.run(_run())
    assert result.ok
    assert RDEStage.FACT_ACQUISITION.value in result.stages
    assert RDEStage.NORMALIZE.value in result.stages
    assert RDEStage.CORRELATE.value in result.stages
    assert RDEStage.AGGREGATE_FACTORS.value in result.stages
    assert RDEStage.CALCULATE_SCORES.value in result.stages
    assert RDEStage.RULE_CHECK.value in result.stages
    assert RDEStage.EXPLAIN.value in result.stages
    assert RDEStage.DELIVER.value in result.stages
    assert result.composite_score > 0
    assert len(result.factor_scores) == 5
    assert len(result.recommendations) >= 1


def test_confidence_score_components(sample_signals):
    from flowsint_crypto_compliance.platform.v2.rde.normalizer import normalize_signals
    from flowsint_crypto_compliance.platform.v2.rde.factors import calculate_all_factors
    from flowsint_crypto_compliance.platform.v2.rde.correlator import correlate_signals

    normalized = normalize_signals(sample_signals)
    factors = calculate_all_factors(normalized)
    correlations = correlate_signals(normalized)
    confidence = calculate_confidence(normalized, correlations=correlations, factor_results=factors)

    assert confidence.independent_sources > 0
    assert confidence.quality > 0
    assert confidence.completeness > 0
    assert confidence.composite > 0
    d = confidence.to_dict()
    assert "independent_sources" in d
    assert "consistency" in d
    assert "freshness" in d


def test_risk_level_with_explanation():
    high = map_score_to_risk_level(75.0)
    assert high["risk_level"] == RiskLevel.HIGH.value
    assert "explanation_ru" in high

    transition = map_score_to_risk_level(75.0, previous_level=RiskLevel.MEDIUM)
    assert transition["transition_ru"] is not None
    assert transition["previous_level"] == "medium"


def test_rules_engine_elevated_attention():
    engine = get_rules_engine()
    events = engine.evaluate({
        "activity_spike": True,
        "new_links": True,
        "multi_source_evidence": True,
    })
    assert len(events) == 1
    assert events[0].event_type == "ElevatedAttentionEvent"
    assert events[0].rule_id == "elevated_attention"


def test_architectural_constraints():
    import flowsint_crypto_compliance.platform.v2.rde.orchestrator as orch_mod

    constraints = rde_architectural_constraints()
    assert "mutate_source_data" in constraints["forbidden_actions"]
    assert "auto_decision" in constraints["forbidden_actions"]
    source = inspect.getsource(orch_mod)
    assert "mutate" not in source.lower() or "mutation" in source.lower()
    assert "from flowsint_crypto_compliance.platform.v2.investigation_platform" not in source


def test_decision_support_recommendations_only_no_auto_decision(sample_signals):
    async def _run():
        return await run_rde_assessment(
            entity_key="Test Org RDE",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            case_ref="RFC16-TEST",
            signals=sample_signals,
        )

    import asyncio

    result = asyncio.run(_run())
    d = result.to_dict()
    assert d["auto_decision"] is False
    assert d["source_mutation"] is False
    for rec in d["recommendations"]:
        assert rec["requires_analyst"] is True


def test_rde_api_assess_endpoint(v2_client, sample_signals):
    manifest = v2_client.get("/api/platform/v2/rde/manifest")
    assert manifest.status_code == 200
    body = manifest.json()
    assert body["rfc"] == "RFC-0016"
    assert "factor_groups" in body

    assess = v2_client.post(
        "/api/platform/v2/rde/assess",
        json={
            "entity_key": "Test Org RDE",
            "case_ref": "RFC16-API",
            "signals": sample_signals,
        },
    )
    assert assess.status_code == 200
    data = assess.json()
    assert data["ok"] is True
    assert data["entity_key"] == "Test Org RDE"
    assert "stages" in data
    assert data["auto_decision"] is False
    assert "risk_level" in data


def test_rde_auto_acquires_subsystem_signals():
    """Integration — RDE pulls blockchain index + CRIF sanctions without manual signals."""
    import asyncio
    import uuid

    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.sync_store import (
        get_block_sync_store,
    )

    addr = "T9yD14Nj9j7xRZ4nFf8vieT9j7xRZ4nFf8v"
    get_block_sync_store().index_transfer(
        "tron",
        {
            "tx_hash": "autosig1",
            "source": "TSender",
            "target": addr,
            "asset": "TRX",
            "amount": 150_000.0,
        },
    )

    async def _run():
        return await run_rde_assessment(
            entity_key=addr,
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            case_ref=None,
            signals=None,
        )

    result = asyncio.run(_run())
    assert result.ok
    acquired = result.explain.get("acquired_groups") or []
    assert "blockchain_signals" in acquired or "registry_signals" in acquired
    assert result.factor_scores.get("blockchain", 0) >= 0
    assert result.explain.get("why") or result.explain.get("facts")


def test_rde_handles_missing_transaction_count():
    """Smoke path — minimal blockchain_signals without tx_count must not crash rule context."""
    import asyncio
    import uuid

    async def _run():
        return await run_rde_assessment(
            entity_key="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            case_ref="FSK-LIVE-001",
            signals={
                "blockchain_signals": {
                    "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                    "chain": "tron",
                }
            },
        )

    result = asyncio.run(_run())
    assert result.ok, result.errors

