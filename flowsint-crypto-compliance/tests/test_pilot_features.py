import pytest

from flowsint_crypto_compliance.ingestion.regulator_connector import RegulatorHubConfig
from flowsint_crypto_compliance.reporting.excel_report import render_regulator_xlsx
from flowsint_crypto_compliance.reporting.pdf_report import render_regulator_html
from flowsint_crypto_compliance.storage.neo4j_pivots import ComplianceNeo4jPivotExporter
from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind


def test_regulator_hub_config_from_env(monkeypatch):
    monkeypatch.setenv("REGULATOR_HUB_URL", "https://hub.example.ru")
    cfg = RegulatorHubConfig.from_env()
    assert cfg is not None
    assert cfg.base_url == "https://hub.example.ru"


def test_excel_report_bytes():
    data = render_regulator_xlsx(
        {
            "case_ref": "DEMO-1",
            "scenario_title_ru": "test",
            "illegal_flow_score": 80,
            "risk_level": "high",
            "executive_summary_ru": "summary",
            "findings": [{"severity": "high", "code": "X", "title_ru": "t", "confidence": 0.9}],
            "metrics": {"risk_scoring": {"heuristic_score": 70, "xgboost": {"model_version": "v1", "model_score": 75, "blended_score": 80}}},
        }
    )
    assert data[:2] == b"PK"


def test_jinja_regulator_html():
    html = render_regulator_html(
        {
            "case_ref": "DEMO-1",
            "scenario_title_ru": "Test",
            "illegal_flow_score": 55,
            "risk_level": "medium",
            "executive_summary_ru": "ok",
            "findings": [],
            "metrics": {},
        }
    )
    assert "DEMO-1" in html


def test_neo4j_pivots_graceful():
    graph = EvidenceGraph()
    graph.upsert_node(kind=NodeKind.WALLET, primary_key="tron:TRU1", confidence=0.8)
    result = ComplianceNeo4jPivotExporter().export(graph, case_ref="CASE-P")
    assert result["exported"] is False
