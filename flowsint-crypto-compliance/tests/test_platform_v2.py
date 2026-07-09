"""Tests for RFC-0002 platform v2 scaffolding."""

import uuid

import pytest

from flowsint_crypto_compliance.platform.v2.canonical import (
    Entity,
    EntityAttribute,
    EntityType,
    Evidence,
    TrustLevel,
)
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.event_bus import PlatformEventBus
from flowsint_crypto_compliance.platform.v2.fusion_pipeline import FusionPipeline
from flowsint_crypto_compliance.platform.v2.plugin_registry import PluginKind, get_plugin_registry


def test_entity_first_model():
    tenant = uuid.UUID("00000000-0000-0000-0000-000000000001")
    ent = Entity(
        tenant_id=tenant,
        entity_type=EntityType.WALLET,
        canonical_key="tron:T9yD14Nj9j7xAR4oQL3FzRPiRYiH5b8q",
        display_name="TRON wallet",
    )
    assert ent.entity_type == EntityType.WALLET
    updated = ent.with_attribute(EntityAttribute(key="risk_score", value=72, source="fusion"))
    assert updated.version == 2
    assert len(updated.attributes) == 1


def test_evidence_trust_composite():
    ev = Evidence(
        tenant_id=uuid.uuid4(),
        source_type="darknet_index",
        content_hash="a" * 64,
        trust=TrustLevel(source_reliability=0.8, information_credibility=0.7, sample_size=10),
    )
    assert 0.5 < ev.trust_level < 0.6


def test_platform_event_legacy_mapping():
    ev = PlatformEvent(
        event_type=EventType.CASE_OPENED,
        source="test",
        payload={"case_ref": "FS-001"},
    )
    assert ev.legacy_type() == "case_new"


def test_platform_event_bus_publish():
    bus = PlatformEventBus()
    ev = PlatformEvent(
        event_type=EventType.EVIDENCE_CREATED,
        source="test",
        payload={"content_hash": "abc123"},
    )
    out = bus.publish(ev)
    assert out["v2"]["event_type"] == "EvidenceCreated"
    assert out["legacy"]["type"] == "evidence_created"


@pytest.mark.asyncio
async def test_fusion_pipeline_stages_emit_events():
    pipe = FusionPipeline.with_bayesian_confidence()
    records = [
        {"source_type": "explorer_tag", "confidence": 0.8, "source_name": "TronScan"},
        {"source_type": "sanctions", "confidence": 0.9, "source_name": "OFAC"},
    ]
    emitted = await pipe.run(records, tenant_id=uuid.uuid4())
    assert len(emitted) == 7
    assert emitted[-1].event_type == EventType.FUSED_INTELLIGENCE_READY
    assert records[0].get("fusion_confidence") is not None


def test_plugin_registry_defaults():
    reg = get_plugin_registry()
    plugins = reg.list(PluginKind.BLOCKCHAIN)
    assert any(p.plugin_id == "scalpel.onchain" for p in plugins)
    manifest = reg.manifest()
    assert len(manifest) >= 5
