"""Tests for additive enterprise report sections (Wave 1).

Verifies backward compatibility (flag off = legacy output), correct enrichment
(flag on), defensiveness, and the feature-flag registry itself.
"""

from __future__ import annotations

import pytest

from flowsint_crypto_compliance import feature_flags
from flowsint_crypto_compliance.reporting.enterprise_sections import (
    enrich_enterprise_sections,
)
from flowsint_crypto_compliance.reporting.finskalp_report import FinSkalpReportBuilder
from flowsint_crypto_compliance.reporting.sar_report import SarReportBuilder

_ENV = "FINSKALP_ENTERPRISE_REPORT_SECTIONS"


def _build_sar() -> dict:
    return SarReportBuilder().build(
        investigation_id="inv-es-1",
        case_ref="CASE-ES-1",
        address="TRU_HUB_MSK",
        chain="tron",
        screening={
            "risk_score": 72,
            "risk_level": "high",
            "onchain_summary": {
                "inbound_count": 10,
                "outbound_count": 5,
                "counterparties": 7,
                "first_activity": "2024-01-01",
                "last_activity": "2024-06-01",
            },
        },
        fusion_report={"illegal_flow_score": 68, "evidence_graph": {"nodes": 12, "edges": 18}},
        forensic_report={
            "executive_summary": {"text_ru": "Форензическое резюме", "key_findings_ru": ["A"]},
            "evidence_inventory": [{"exhibit_id": "E1", "description": "x", "sha256": "abc", "tier": "1"}],
        },
    )


# --- feature flag registry ----------------------------------------------------


def test_flag_defaults_off(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    assert feature_flags.enterprise_report_sections_enabled() is False
    assert feature_flags.is_enabled("enterprise_report_sections") is False


@pytest.mark.parametrize("truthy", ["1", "true", "YES", "on"])
def test_flag_enabled_values(monkeypatch, truthy):
    monkeypatch.setenv(_ENV, truthy)
    assert feature_flags.enterprise_report_sections_enabled() is True


@pytest.mark.parametrize("falsy", ["0", "false", "no", "off", ""])
def test_flag_disabled_values(monkeypatch, falsy):
    monkeypatch.setenv(_ENV, falsy)
    assert feature_flags.enterprise_report_sections_enabled() is False


def test_flag_snapshot_shape(monkeypatch):
    monkeypatch.setenv(_ENV, "1")
    snap = feature_flags.flag_snapshot()
    assert "enterprise_report_sections" in snap
    entry = snap["enterprise_report_sections"]
    assert entry["env_var"] == _ENV
    assert entry["enabled"] is True
    assert entry["read_count"] >= 1


# --- enrichment ---------------------------------------------------------------


def test_enrich_adds_namespaced_key_without_clobbering():
    report = _build_sar()
    original_keys = set(report.keys())
    enriched = enrich_enterprise_sections(report)
    es = enriched["enterprise_sections"]
    # only a single additive key introduced (plus whatever builders already set)
    assert set(enriched.keys()) - original_keys == {"enterprise_sections"}
    assert es["_schema"].startswith("enterprise-sections/")
    assert "case_metadata" in es
    assert es["case_metadata"]["case_ref"] == "CASE-ES-1"


def test_enrich_is_defensive_on_empty_report():
    # An almost-empty report must not raise and must not fabricate sections.
    out = enrich_enterprise_sections({})
    assert "enterprise_sections" not in out or isinstance(out["enterprise_sections"], dict)


def test_metrics_derived_from_existing_onchain_data():
    # Mirrors the shape of address/forensic reports which expose on-chain counts.
    report = {
        "report_type": "address",
        "case_ref": "CASE-M-1",
        "report_id": "inv-m-1",
        "onchain": {"inbound_count": 10, "outbound_count": 5, "counterparties": 7},
        "findings": [{"code": "MIXER"}, {"code": "SANCTION"}],
    }
    es = enrich_enterprise_sections(report)["enterprise_sections"]
    assert "investigation_metrics" in es
    metrics = es["investigation_metrics"]["metrics"]
    assert metrics.get("inbound_tx") == 10
    assert metrics.get("findings") == 2


# --- render integration (backward compatibility) ------------------------------


def test_render_flag_off_is_legacy(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    report = _build_sar()
    html = FinSkalpReportBuilder().render_html(report)
    assert "Enterprise Appendix" not in html
    # legacy content still present
    assert "report_type" not in html  # sanity: it's HTML, not a dict dump
    assert report.get("enterprise_sections") is None


def test_render_flag_on_appends_sections(monkeypatch):
    monkeypatch.setenv(_ENV, "1")
    report = _build_sar()
    html = FinSkalpReportBuilder().render_html(report)
    assert "Enterprise Appendix" in html
    assert "Матрица" in html or "Метаданные дела" in html


def test_render_pdf_still_works_with_flag_on(monkeypatch):
    monkeypatch.setenv(_ENV, "1")
    report = _build_sar()
    content, media, ext = FinSkalpReportBuilder().render_pdf(report)
    assert media.startswith("application/pdf") or media.startswith("text/html")
    assert len(content) > 1000
    assert ext in ("pdf", "html")
