import pytest

from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache, seed_demo_registry
from flowsint_crypto_compliance.reporting.pdf_report import render_fz115_html, render_pdf_bytes
from flowsint_crypto_compliance.services.demo_compliance_service import get_demo_compliance_service


@pytest.mark.asyncio
async def test_demo_seed_scenario_without_database():
    svc = get_demo_compliance_service()
    payload = await svc.seed_scenario("p2p_rub_offshore")
    assert payload["case_ref"] == "DEMO-RU-001"
    assert payload.get("illegal_flow_score", 0) >= 0
    assert "evidence_graph" in payload
    assert payload["metrics"]["risk_scoring"].get("xgboost")


@pytest.mark.asyncio
async def test_demo_fuse_stream_case_in_memory():
    svc = get_demo_compliance_service()
    payload = await svc.seed_scenario("p2p_rub_offshore")
    assert payload["graph_stats"]["nodes"] >= 1


def test_demo_registry_seeded():
    cache = get_demo_label_cache()
    assert cache.count() >= seed_demo_registry()


def test_fz115_html_and_pdf_fallback():
    html = render_fz115_html(
        {
            "report_id": "ОТЧ-115-TEST",
            "report_type_ru": "Справка 115-ФЗ",
            "classification_ru": "ДСП",
            "case_ref": "DEMO-RU-001",
            "executive_summary_ru": "Тест",
            "illegal_flow_score": 72.5,
            "risk_level": "high",
            "decision_ru": "Направить в Росфинмониторинг",
            "decision_basis_ru": "Достаточная доказательная база",
            "legal_basis_ru": ["115-ФЗ ст. 6"],
            "suspicion_signs": [{"article_ru": "признак", "confirmed": "да"}],
            "findings_summary_ru": ["[HIGH] тест"],
            "evidence_items": ["evidence-1"],
            "recommended_actions_ru": ["действие"],
            "responsible_officer_ru": "Аналитик",
            "generated_at": "2026-07-01T00:00:00Z",
        }
    )
    assert "115-ФЗ" in html
    content, media_type = render_pdf_bytes(html)
    assert content
    assert "pdf" in media_type or "html" in media_type
