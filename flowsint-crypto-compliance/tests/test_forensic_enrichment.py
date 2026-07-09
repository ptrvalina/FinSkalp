"""Tests for sanctions screening narrative and forensic enrichment."""

from flowsint_crypto_compliance.reporting.forensic_enrichment import build_risk_score_breakdown
from flowsint_crypto_compliance.reporting.forensic_builder import build_forensic_report_v2
from flowsint_crypto_compliance.reporting.sanctions_screening import (
    build_screening_status,
    sanctions_narrative_ru,
)
from flowsint_crypto_compliance.attribution.attribution_engine import AttributionResult


def test_no_false_negative_when_opensanctions_degraded():
    status = build_screening_status(
        source_status={"opensanctions_api": "degraded:401"},
        sanctions_hits=[],
    )
    assert status["OpenSanctions"] == "unavailable"
    narr = sanctions_narrative_ru(
        screening_status=status,
        source_status={"opensanctions_api": "degraded:401"},
        sanctions_hits=[],
    )
    assert "не завершена" in narr["status_ru"] or "unavailable" in narr["status_en"].lower()
    assert "совпадений" not in narr["status_ru"] or "не зафиксировано" in narr["status_ru"]


def test_clear_when_opensanctions_ok():
    status = build_screening_status(
        source_status={"opensanctions_api": "ok", "ofac_store": "no_match"},
        sanctions_hits=[],
    )
    narr = sanctions_narrative_ru(
        screening_status=status,
        source_status={"opensanctions_api": "ok"},
        sanctions_hits=[],
    )
    assert narr["conclusion_type"] == "clear"


def test_risk_breakdown_sums_to_total():
    screening = {"risk_score": 80.0, "findings": [], "onchain_summary": {"kyt_exposure": {}}}
    bd = build_risk_score_breakdown(
        screening=screening,
        attribution={"sanctions_hits": [], "tier_summary": {}},
        open_osint=None,
        pattern="standard",
    )
    assert bd["total"] == 80.0
    assert len(bd["components"]) >= 5


def test_forensic_report_includes_enrichments():
    attr = AttributionResult(
        connections=[
            {
                "entity_name": "Binance",
                "address": "TX123",
                "total_received": 100.0,
                "tier": 2,
                "confidence": 0.8,
                "source": "tronscan",
                "behavior": "direct",
                "risk_pct": 20,
                "risk_tier": "low",
                "hops": 1,
            }
        ],
        source_status={"opensanctions_api": "degraded:401", "ofac_store": "no_match"},
    )
    screening = {
        "risk_score": 65.0,
        "risk_level": "high",
        "onchain_summary": {
            "inbound_count": 10,
            "outbound_count": 2,
            "inbound_amount": 1000,
            "outbound_amount": 900,
            "first_activity": "2026-01-01",
            "last_activity": "2026-07-01",
            "counterparties": 5,
            "sample_tx": [],
        },
        "findings": [],
        "source_status": {"onchain": "ok"},
    }
    report = build_forensic_report_v2(
        investigation_id="inv-test",
        case_ref="FSK-TEST",
        address="TSubject123456789012345678901234567",
        chain="tron",
        screening=screening,
        attribution=attr,
        fusion_report={},
        fusion_graph=None,
        graph_section=None,
        evidence_sources={"onchain_verification": {"address": "TSubject"}},
    )
    assert report.get("screening_status")
    assert report["screening_status"]["OpenSanctions"] == "unavailable"
    assert report.get("risk_score_breakdown")
    assert report.get("digital_signature", {}).get("report_sha256")
    assert report.get("overall_attribution_confidence", {}).get("pct") is not None
    assert report.get("flow_visualization", {}).get("svg")


def test_forensic_report_includes_fusion_graph_section():
    fusion = {
        "nodes": [
            {"id": "tron:subj", "address": "TSubject123456789012345678901234567", "label": "Subject", "hop": 0},
            {"id": "tron:cp1", "address": "TX123456789012345678901234567890", "label": "CP1", "hop": 1},
        ],
        "edges": [{"from": "tron:cp1", "to": "tron:subj"}],
        "risk_annotations": [{"type": "illicit_hit", "chain": "tron", "address": "TX123", "hop": 1, "sources": ["ofac"]}],
    }
    attr = AttributionResult(connections=[], source_status={"opensanctions_api": "ok"})
    screening = {
        "risk_score": 55.0,
        "risk_level": "medium",
        "onchain_summary": {"inbound_count": 1, "outbound_count": 0, "sample_tx": []},
        "findings": [],
    }
    report = build_forensic_report_v2(
        investigation_id="inv-fusion",
        case_ref="FSK-FUS",
        address="TSubject123456789012345678901234567",
        chain="tron",
        screening=screening,
        attribution=attr,
        fusion_report={},
        fusion_graph=fusion,
        graph_section=None,
        evidence_sources={},
    )
    gs = report.get("graph_section") or {}
    assert gs.get("has_svg") or gs.get("has_png")
    assert gs.get("node_count") == 2
    assert report["flow_visualization"].get("fusion_linked") is True
    from flowsint_crypto_compliance.reporting.finskalp_report import FinSkalpReportBuilder

    html = FinSkalpReportBuilder().render_html(report)
    assert "Multi-hop fusion graph" in html
    assert "Flow graph (counterparty heuristic)" in html


def test_fusion_graph_svg_trongrid_style():
    from flowsint_crypto_compliance.reporting.graph_report import graph_section_for_report

    fusion = {
        "nodes": [
            {"id": "tron:subj", "address": "TSubject123456789012345678901234567", "label": "Subject", "hop": 0, "risk_score": 72},
            {"id": "tron:cp1", "address": "TX123456789012345678901234567890", "label": "CP1", "hop": 1, "risk_score": 85},
            {"id": "tron:cp2", "address": "TY987654321098765432109876543210", "label": "CP2", "hop": 1, "risk_score": 22},
        ],
        "edges": [
            {"from": "tron:cp1", "to": "tron:subj"},
            {"from": "tron:cp2", "to": "tron:subj"},
            {"from": "tron:cp1", "to": "tron:cp2"},
        ],
        "risk_annotations": [{"type": "illicit_hit", "chain": "tron", "address": "TX123", "hop": 1, "sources": ["ofac"]}],
    }
    sec = graph_section_for_report(fusion)
    svg = sec.get("svg") or ""
    assert sec.get("has_svg")
    assert 'fill="#0a0a0f"' in svg or 'fill="#0f172a"' in svg
    assert "stroke-dasharray" in svg
    assert 'stroke="#ffffff"' in svg
    assert "<circle" in svg
    assert "#ef4444" in svg


def test_flow_visualization_svg_trongrid_style():
    from flowsint_crypto_compliance.reporting.forensic_enrichment import build_flow_visualizations

    flow = build_flow_visualizations(
        address="TSubject123456789012345678901234567",
        onchain={"inbound_amount": 1000, "outbound_amount": 500},
        connections=[
            {"entity_name": "Binance", "address": "TX1", "total_received": 400, "risk_pct": 80, "behavior": "direct"},
            {"entity_name": "Unknown", "address": "TX2", "total_received": 100, "risk_pct": 25, "behavior": "direct"},
        ],
        priority_lead={"lead_address": "TDest123456789012345678901234567"},
        fusion_graph=None,
        risk_score=65,
    )
    svg = flow.get("svg") or ""
    sankey = flow.get("sankey_svg") or ""
    assert flow.get("has_svg")
    assert "stroke-dasharray" in svg
    assert "<circle" in svg
    assert 'fill="#0a0a0f"' in svg
    assert "stroke-dasharray" in sankey
    assert "<circle" in sankey
