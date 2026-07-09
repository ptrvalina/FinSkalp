"""Comprehensive integration tests for RFC-0002 platform v2."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from flowsint_crypto_compliance.platform.v2.canonical import EntityType, TrustLevel
from flowsint_crypto_compliance.platform.v2.entity_resolution import EntityResolutionEngine
from flowsint_crypto_compliance.platform.v2.evidence_center import (
    content_hash_from_finding,
    dual_write_osint_finding,
    osint_finding_to_evidence,
)
from flowsint_crypto_compliance.platform.v2.event_bus import PlatformEventBus
from flowsint_crypto_compliance.platform.v2.event_subscriber import PlatformEventSubscriber
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.gateway import architecture_manifest, emit_scalpel_collect_event
from flowsint_crypto_compliance.platform.v2.investigation_workspace import InvestigationWorkspace
from flowsint_crypto_compliance.platform.v2.neo4j_projection import V2_NEO4J_LABELS, neo4j_label_for
from flowsint_crypto_compliance.platform.v2.plugin_registry import create_scalpel_collector, get_plugin_registry


TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_evidence_center_dual_write_mapping():
    row = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(TENANT),
        "case_id": str(uuid.uuid4()),
        "case_ref": "FS-TEST-001",
        "entity_type": "domain",
        "entity_value": "evil.example",
        "source_type": "scalpel_extract",
        "confidence": 0.72,
        "payload": {"url": "https://evil.example"},
    }
    evidence = osint_finding_to_evidence(row)
    assert evidence.source_type == "scalpel_extract"
    assert evidence.payload["entity_value"] == "evil.example"
    assert evidence.trust.composite > 0.3
    h1 = content_hash_from_finding(
        entity_type="domain",
        entity_value="evil.example",
        source_type="scalpel_extract",
        payload={"url": "https://evil.example"},
    )
    h2 = content_hash_from_finding(
        entity_type="domain",
        entity_value="evil.example",
        source_type="scalpel_extract",
        payload={"url": "https://evil.example"},
    )
    assert h1 == h2


def test_dual_write_skips_without_db():
    row = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(TENANT),
        "case_id": str(uuid.uuid4()),
        "case_ref": "FS-001",
        "entity_type": "email",
        "entity_value": "a@b.c",
        "source_type": "osint",
        "confidence": 0.5,
        "payload": {},
    }
    with patch("flowsint_core.core.postgre_db.SessionLocal", side_effect=ImportError):
        assert dual_write_osint_finding(row) is None


def test_entity_resolution_merge_signals():
    engine = EntityResolutionEngine()
    signals = [
        ("phone", "+7-999-123-45-67"),
        ("email", "User@Example.COM"),
        ("crypto_address", "tron:T9yD14Nj9j7xAR4oQL3FzRPiRYiH5b8q"),
        ("domain", "HTTPS://Shop.Example/onion"),
    ]
    entities = engine.merge_signals(signals, tenant_id=TENANT)
    types = {e.entity_type for e in entities}
    assert EntityType.PHONE in types
    assert EntityType.EMAIL in types
    assert EntityType.WALLET in types
    assert EntityType.DOMAIN in types
    keys = {e.canonical_key for e in entities}
    assert "tron:T9yD14Nj9j7xAR4oQL3FzRPiRYiH5b8q" in keys


def test_neo4j_unified_labels():
    assert neo4j_label_for(EntityType.WALLET) == "FinskalpWallet"
    assert neo4j_label_for(EntityType.CASE) == "FinskalpCase"
    assert "FinskalpWallet" in V2_NEO4J_LABELS.values()


def test_platform_event_subscriber_case_opened():
    sub = PlatformEventSubscriber(
        knowledge=MagicMock(),
        resolver=EntityResolutionEngine(),
        neo4j=MagicMock(),
    )
    sub._knowledge.upsert_entity.side_effect = lambda e: e
    ev = PlatformEvent(
        event_type=EventType.CASE_OPENED,
        source="test",
        tenant_id=TENANT,
        payload={"case_ref": "FS-INT-001", "address": "TAddr", "chain": "tron"},
    )
    out = sub.dispatch(ev)
    assert sub._knowledge.upsert_entity.call_count >= 2
    assert any(h.get("builtin") == "CaseOpened" for h in out["handlers"] if isinstance(h, dict))


def test_platform_event_bus_persists_and_dispatches():
    bus = PlatformEventBus()
    ev = PlatformEvent(
        event_type=EventType.EVIDENCE_CREATED,
        source="test",
        tenant_id=TENANT,
        payload={
            "case_ref": "FS-001",
            "entity_type": "domain",
            "entity_value": "x.example",
            "content_hash": "abc",
            "confidence": 0.6,
        },
    )
    with patch.object(bus, "_persist_postgres") as pg, patch.object(bus, "_dispatch_subscribers") as sub:
        with patch("flowsint_crypto_compliance.infrastructure.compliance_events.get_event_bus") as legacy:
            legacy.return_value.publish.return_value = {"ok": True}
            out = bus.publish(ev)
    pg.assert_called_once()
    sub.assert_called_once()
    assert out["v2"]["event_type"] == "EvidenceCreated"


def test_investigation_workspace_open_case_emits_event():
    ws = InvestigationWorkspace(
        knowledge=MagicMock(),
        resolver=EntityResolutionEngine(),
        neo4j=MagicMock(),
    )
    ws._knowledge.upsert_entity.side_effect = lambda e: e
    with patch("flowsint_crypto_compliance.platform.v2.investigation_workspace.get_platform_event_bus") as bus_mock:
        bus = MagicMock()
        bus_mock.return_value = bus
        result = ws.open_case(case_ref="FS-WS-001", tenant_id=TENANT)
    assert result["case_ref"] == "FS-WS-001"
    bus.publish.assert_called_once()
    assert bus.publish.call_args[0][0].event_type == EventType.CASE_OPENED


def test_plugin_registry_scalpel_factory():
    reg = get_plugin_registry()
    desc = reg.get("scalpel.onchain")
    assert desc is not None
    assert desc.factory is not None
    collector = create_scalpel_collector("scalpel.onchain")
    assert collector is not None


def test_gateway_architecture_manifest():
    manifest = architecture_manifest()
    assert manifest["rfc"] == "RFC-0002"
    assert "Entity Resolution Engine" in manifest["core_components"]
    assert len(manifest["plugins"]) >= 5


def test_emit_scalpel_collect_event():
    with patch("flowsint_crypto_compliance.platform.v2.event_bus.get_platform_event_bus") as bus_mock:
        bus = MagicMock()
        bus_mock.return_value = bus
        n = emit_scalpel_collect_event(
            case_ref="FS-SCP",
            tenant_id=TENANT,
            investigation_id=None,
            mentions=[{"entity_type": "domain", "entity_value": "a.example", "confidence": 0.7}],
        )
    assert n == 1
    bus.publish.assert_called_once()
    assert bus.publish.call_args[0][0].event_type == EventType.OSINT_MENTION_FOUND


@pytest.mark.asyncio
async def test_fusion_pipeline_with_subscriber_mock():
    from flowsint_crypto_compliance.platform.v2.fusion_pipeline import FusionPipeline

    with patch("flowsint_crypto_compliance.platform.v2.fusion_pipeline.get_platform_event_bus") as bus_mock:
        bus = MagicMock()
        bus_mock.return_value = bus
        pipe = FusionPipeline.with_bayesian_confidence()
        emitted = await pipe.run(
            [{"source_type": "explorer_tag", "confidence": 0.8, "source_name": "TronScan"}],
            tenant_id=TENANT,
        )
    assert len(emitted) == 7
    assert bus.publish.call_count == 7
