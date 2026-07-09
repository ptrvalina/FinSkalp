"""Volumetric report — sovereign attribution section serialization."""

from flowsint_crypto_compliance.reporting.volumetric_report import (
    VolumetricReportBuilder,
    _serialize_attribution,
)
from flowsint_types.fiat_crypto import Chain, EntityKind, FusedAttribution


def test_serialize_fused_attribution_uses_address_and_labels():
    attr = FusedAttribution(
        attribution_id="vol-1",
        address="TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL",
        chain=Chain.TRON,
        primary_region="RU",
        sovereign_label="Demo Exchange",
        watchlist_label="OFAC Entity",
        label_source="rosfinmonitoring",
        confidence=0.87,
        black_zone=True,
        gray_zone=False,
        sanctioned=True,
    )
    row = _serialize_attribution(attr)
    assert row["wallet"] == "TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL"
    assert row["entity"] == "Demo Exchange"
    assert row["primary_region"] == "RU"
    assert row["confidence"] == 0.87
    assert row["zone"] == "black"
    assert row["black_zone"] is True
    assert row["gray_zone"] is False
    assert row["label_source"] == "rosfinmonitoring"
    assert row["sanctioned"] is True


def test_serialize_attribution_dict_fallback():
    row = _serialize_attribution(
        {
            "address": "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE",
            "watchlist_label": "Mixer",
            "entity_kind": "mixer",
            "primary_region": "EU",
            "confidence": 0.6,
            "gray_zone": True,
            "label_source": "graphsense",
        }
    )
    assert row["wallet"] == "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"
    assert row["entity"] == "Mixer"
    assert row["zone"] == "gray"


def test_serialize_attribution_entity_kind_when_no_label():
    attr = FusedAttribution(
        attribution_id="vol-2",
        address="T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
        chain=Chain.TRON,
        entity_kind=EntityKind.CEX,
        confidence=0.4,
    )
    row = _serialize_attribution(attr)
    assert row["entity"] == EntityKind.CEX.value


def test_volumetric_builder_attribution_section_not_empty():
    from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph
    from flowsint_crypto_compliance.osint_core.fusion_engine import FusionResult

    fusion_attr = FusedAttribution(
        attribution_id="vol-3",
        address="TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL",
        chain=Chain.TRON,
        sovereign_label="Labeled VASP",
        confidence=0.75,
    )
    fusion = FusionResult(
        case_id="case-1",
        graph=EvidenceGraph(),
        attributions=[fusion_attr],
        bridges=[],
        linkage_scores=[],
    )
    report = VolumetricReportBuilder().build(
        investigation_id="inv-1",
        case_ref="CASE-1",
        address="TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL",
        chain="tron",
        screening={"findings": []},
        fusion_report={"findings": [], "evidence_graph": {"nodes": 0, "edges": 0}},
        fusion=fusion,
    )
    attr_section = next(s for s in report["sections"] if s["id"] == "attribution")
    assert attr_section["count"] == 1
    assert attr_section["items"][0]["wallet"]
    assert attr_section["items"][0]["entity"] == "Labeled VASP"
