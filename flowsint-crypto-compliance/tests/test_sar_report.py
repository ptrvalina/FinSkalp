"""Tests for SAR report builder and PDF render."""

from flowsint_crypto_compliance.reporting.finskalp_report import FinSkalpReportBuilder
from flowsint_crypto_compliance.reporting.sar_report import SarReportBuilder


def test_sar_report_builds_structured_sections():
    screening = {
        "risk_score": 72,
        "risk_level": "high",
        "summary_ru": "Повышенный риск",
        "findings": [{"code": "MIXER", "title_ru": "Mixer exposure", "severity": "high"}],
        "onchain_summary": {
            "inbound_count": 10,
            "outbound_count": 5,
            "counterparties": 7,
            "balance_usd": 1200,
            "first_activity": "2024-01-01",
            "last_activity": "2024-06-01",
            "attribution": {"sanctions_hits": [], "connections": []},
            "kyt_exposure": {"connection_count": 7},
        },
    }
    fusion_report = {
        "illegal_flow_score": 68,
        "findings": [{"code": "CORRIDOR", "title_ru": "CIS corridor", "severity": "high"}],
        "evidence_graph": {"nodes": 12, "edges": 18},
    }
    forensic = {
        "executive_summary": {
            "text_ru": "Форензическое резюме",
            "key_findings_ru": ["Finding A"],
        },
        "address_profile": {"entity_classification_ru": "EOA"},
        "evidence_inventory": [{"description": "exhibit-1", "sha256": "abc"}],
    }
    sar = SarReportBuilder().build(
        investigation_id="inv-sar-1",
        case_ref="CASE-SAR-1",
        address="TRU_HUB_MSK",
        chain="tron",
        screening=screening,
        fusion_report=fusion_report,
        forensic_report=forensic,
        open_osint={"mentions_count": 2, "independent_sources": 1, "open_risk_score": 40, "mentions": []},
        subject_id="subj-1",
        bank_name="Demo Bank",
        amount=2_000_000,
        currency="RUB",
    )
    assert sar["report_type"] == "sar"
    assert len(sar["evidence_sections"]) >= 5
    assert sar["decision"]["str_recommended"] is True
    assert any(i["confirmed"] == "да" for i in sar["suspicion_indicators"])


def test_sar_report_renders_pdf():
    sar = SarReportBuilder().build(
        investigation_id="inv-sar-2",
        case_ref="CASE-SAR-2",
        address="TRU_HUB_MSK",
        chain="tron",
        screening={"risk_score": 30, "risk_level": "medium", "onchain_summary": {}},
        fusion_report={"illegal_flow_score": 20, "evidence_graph": {"nodes": 1, "edges": 0}},
        forensic_report={"executive_summary": {"text_ru": "ok"}},
    )
    content, media, ext = FinSkalpReportBuilder().render_pdf(sar)
    assert media.startswith("application/pdf") or media.startswith("text/html")
    assert len(content) > 1000
    assert ext in ("pdf", "html")
