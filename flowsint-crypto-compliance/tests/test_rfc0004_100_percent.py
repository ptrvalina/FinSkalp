"""RFC-0004 Intelligence Platform — 100% readiness tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.chains import get_chain_adapter_for_key
from flowsint_crypto_compliance.platform.v2.intelligence import intelligence_platform_manifest
from flowsint_crypto_compliance.platform.v2.intelligence.blockchain_capabilities import (
    blockchain_capabilities_manifest,
)
from flowsint_crypto_compliance.platform.v2.intelligence.engines import (
    BehavioralIntelligenceEngine,
    CorrelationIntelligenceEngine,
    RiskIntelligenceEngine,
)
from flowsint_crypto_compliance.platform.v2.intelligence.types import IntelligenceContext

PRIORITY_CHAINS = ("btc", "eth", "tron", "ltc", "bsc", "polygon", "sol")


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000099")


def test_all_priority_chain_adapters_resolve():
    for key in PRIORITY_CHAINS:
        adapter = get_chain_adapter_for_key(key, use_memory=True)
        assert adapter is not None, key
    adapter_bnb = get_chain_adapter_for_key("bnb", use_memory=True)
    assert adapter_bnb is not None


def test_blockchain_capabilities_manifest_seven_production_chains():
    m = blockchain_capabilities_manifest()
    assert len(m["priority_chains"]) == 7
    production = [c for c in m["chains"] if c["status"] == "production"]
    assert len(production) == 7
    chain_keys = {c["chain"] for c in production}
    assert chain_keys == set(PRIORITY_CHAINS)


def test_manifest_includes_blockchain_capabilities_and_11_engines():
    m = intelligence_platform_manifest()
    assert m["rfc"] == "RFC-0004"
    assert len(m["engines"]) == 11
    assert m["engines"][0]["maturity"] == "production"
    bc = m["blockchain_capabilities"]
    assert len(bc["priority_chains"]) == 7
    assert all(c["status"] == "production" for c in bc["chains"])


def test_intelligence_analyze_endpoint():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    client = TestClient(app)

    resp = client.post(
        "/api/platform/v2/intelligence/analyze",
        json={
            "address": "TTestAddr123",
            "chain": "tron",
            "case_ref": "RFC4-TEST",
            "screening": {"risk_score": 20, "onchain_summary": {"inbound_count": 1, "outbound_count": 1}},
            "mentions": [{"entity_type": "domain", "entity_value": "example.com", "confidence": 0.5}],
            "publish": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert len(body["engines_run"]) == 11
    assert body["aggregate_risk_score"] >= 0


def test_behavioral_engine_uses_helpers(tenant_id: uuid.UUID):
    engine = BehavioralIntelligenceEngine()
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        address="addr1",
        chain="eth",
        screening={"regions": ["RU", "AE"], "observed_regions": ["RU", "AE"]},
        mentions=[
            {"timestamp": "2026-07-08T10:00:00+00:00", "entity_value": "a"},
            {"timestamp": "2026-07-08T12:00:00+00:00", "entity_value": "b"},
        ],
    )
    result = engine.analyze(ctx)
    codes = {f.code for f in result.findings}
    assert "BEHAVIOR_TEMPORAL" in codes
    assert "CORRIDOR_MATCH" in codes


def test_correlation_engine_cross_engine_and_temporal(tenant_id: uuid.UUID):
    engine = CorrelationIntelligenceEngine()
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        address="addr1",
        mentions=[
            {"timestamp": "2026-07-08T10:00:00+00:00", "phone": "+7999"},
            {"timestamp": "2026-07-08T11:00:00+00:00", "phone": "+7999"},
        ],
        screening={
            "_intel_findings": [
                {"engine": "blockchain", "code": "TX_ACTIVITY", "severity": "info"},
                {"engine": "osint", "code": "OSINT_MENTION", "severity": "info"},
            ]
        },
    )
    result = engine.analyze(ctx)
    codes = {f.code for f in result.findings}
    assert "TEMPORAL_CORRELATION" in codes
    assert "CROSS_ENGINE_CORRELATION" in codes


def test_risk_engine_uses_illegal_flow_boost(tenant_id: uuid.UUID):
    engine = RiskIntelligenceEngine()
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        address="addr1",
        screening={
            "risk_score": 30,
            "_intel_findings": [{"code": "OSINT_MENTION", "severity": "info", "confidence": 0.5}],
            "bank_feed_count": 2,
            "control_purchase_count": 1,
        },
        attribution={"labels": {}},
    )
    result = engine.analyze(ctx)
    assert "illegal_flow_boost" in result.explain
    assert result.explain["aggregate_risk_score"] >= 30
