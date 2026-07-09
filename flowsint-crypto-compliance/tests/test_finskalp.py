import pytest

from flowsint_crypto_compliance.reporting.finskalp_report import FinSkalpReportBuilder
from flowsint_crypto_compliance.services.finskalp_investigator import (
    FinSkalpInvestigationRequest,
    FinSkalpInvestigator,
    match_scenario_for_address,
)
from flowsint_types.fiat_crypto import Chain


def test_match_scenario_demo_hub():
    sid = match_scenario_for_address("TRU_SBP_HUB", Chain.TRON)
    assert sid == "sbp_gray_hub"


@pytest.mark.asyncio
async def test_finskalp_investigate_demo_address():
    inv = FinSkalpInvestigator()
    result = await inv.investigate(
        FinSkalpInvestigationRequest(address="TRU_HUB_MSK", chain=Chain.TRON)
    )
    assert result.investigation_id
    assert result.screening["risk_score"] >= 0
    assert len(result.phases) >= 8
    assert len(result.attachments) >= 4
    html = FinSkalpReportBuilder().render_html(result.address_report)
    assert "ФинСкальп" in html or "FinSkalp" in html


@pytest.mark.asyncio
async def test_finskalp_with_bank_context():
    inv = FinSkalpInvestigator()
    result = await inv.investigate(
        FinSkalpInvestigationRequest(
            address="TRU_OFFSHORE_EXIT",
            chain=Chain.TRON,
            bank_reference="STR-TEST-001",
            bank_name="Тестбанк",
            amount=2_000_000,
            notes="Демо расследование",
        )
    )
    assert result.fusion_report["evidence_graph"]["nodes"] > 0
    assert result.forensic_report["regulatory_ru"]["framework"]


@pytest.mark.asyncio
async def test_finskalp_open_osint_hub():
    inv = FinSkalpInvestigator()
    result = await inv.investigate(
        FinSkalpInvestigationRequest(address="TRU_HUB_MSK", chain=Chain.TRON)
    )
    assert result.open_osint["mentions_count"] >= 3
    assert result.open_osint["open_risk_score"] > 20
    assert result.open_osint.get("source_status", {}).get("vasp_registry") == "miss"
    open_phase = next(p for p in result.phases if p["id"] == "open_osint")
    assert "Scalpel" in open_phase["detail_ru"] or "сигналов" in open_phase["detail_ru"]
    graph_nodes = result.fusion_report["evidence_graph"]["nodes"]
    assert graph_nodes >= 5


@pytest.mark.asyncio
async def test_open_source_collector_corpus_and_otc():
    from flowsint_crypto_compliance.osint_core.open_source_collector import OpenSourceCollector

    coll = OpenSourceCollector()
    result = await coll.collect("TRU_HUB_MSK", Chain.TRON)
    assert len(result.mentions) >= 3
    assert result.independent_sources >= 2
    assert result.source_status.get("vasp_registry") == "miss"

    sfty = await coll.collect("TZGiyUbaNYSsCSszbYj6cxUgw3d5wmTGnz", Chain.TRON)
    assert len(sfty.mentions) >= 2
