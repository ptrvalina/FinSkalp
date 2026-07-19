"""Tests for RFC-18 operator event catalog and publishing."""

from flowsint_crypto_compliance.platform.v2.event_bus import PlatformEventBus
from flowsint_crypto_compliance.platform.v2.events import EventType
from flowsint_crypto_compliance.platform.v2.operator_events import (
    OPERATOR_EVENT_SCHEMA_VERSION,
    OperatorEventType,
    operator_event_catalog,
    publish_operator_event,
)


def test_operator_event_catalog_lists_all_types():
    catalog = operator_event_catalog()
    assert catalog["schema_version"] == OPERATOR_EVENT_SCHEMA_VERSION
    types = {entry["type"] for entry in catalog["events"]}
    assert types == {t.value for t in OperatorEventType}
    for entry in catalog["events"]:
        assert entry["versioned"] is True
        assert entry["platform_event"]


def test_publish_operator_event_envelope():
    bus = PlatformEventBus()
    from flowsint_crypto_compliance.platform.v2 import operator_events as mod

    original = mod.get_platform_event_bus
    mod.get_platform_event_bus = lambda: bus
    try:
        out = publish_operator_event(
            OperatorEventType.EVIDENCE_ADDED,
            payload={"case_ref": "CASE-001", "evidence_id": "ev-1"},
            actor="analyst-1",
        )
    finally:
        mod.get_platform_event_bus = original

    assert out["v2"]["event_type"] == EventType.EVIDENCE_CREATED.value
    assert out["v2"]["payload"]["operator_event_type"] == "EvidenceAdded"
    assert out["v2"]["payload"]["operator_schema_version"] == OPERATOR_EVENT_SCHEMA_VERSION
    assert out["v2"]["payload"]["case_ref"] == "CASE-001"
    assert out["legacy"]["type"] == "evidence_created"


def test_operator_to_platform_mapping_report_generated():
    catalog = operator_event_catalog()
    report = next(e for e in catalog["events"] if e["type"] == "ReportGenerated")
    assert report["platform_event"] == EventType.REPORT_GENERATED.value


def test_operator_to_platform_mapping_graph_updated():
    catalog = operator_event_catalog()
    graph = next(e for e in catalog["events"] if e["type"] == "GraphUpdated")
    assert graph["platform_event"] == EventType.GRAPH_EXPANDED.value
