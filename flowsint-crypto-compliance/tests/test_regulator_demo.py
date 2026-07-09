import pytest

from flowsint_crypto_compliance.demo.runner import RegulatorDemoRunner
from flowsint_crypto_compliance.detection.illegal_flow import IllegalFlowDetector


@pytest.mark.asyncio
async def test_demo_p2p_offshore_high_risk():
    report = await RegulatorDemoRunner().run("p2p_rub_offshore")
    assert report.illegal_flow_score >= 40
    assert report.risk_level in ("high", "critical", "medium")
    assert report.metrics["wallets_analyzed"] >= 3
    assert "Сбер" in report.executive_summary_ru or "DEMO-RU-001" in report.case_ref


@pytest.mark.asyncio
async def test_demo_sbp_hub_detects_mixer():
    report = await RegulatorDemoRunner().run("sbp_gray_hub")
    codes = {f.code for f in report.findings}
    assert "FIAT_CRYPTO_LINK_RF" in codes or "BLACK_ZONE_LAYERING" in codes or "KYT_MIXER_EXPOSURE" in codes
    assert report.metrics["gray_zone_reduction_pct"] > 0


@pytest.mark.asyncio
async def test_demo_cross_border_do():
    report = await RegulatorDemoRunner().run("cross_border_do")
    codes = {f.code for f in report.findings}
    assert "CROSS_BORDER_OFFSHORE" in codes or "RU_LAYERING_CHAIN" in codes


@pytest.mark.asyncio
async def test_demo_all_scenarios_complete():
    reports = await RegulatorDemoRunner().run_all()
    assert len(reports) == 4
    for r in reports:
        assert r.executive_summary_ru
        assert r.evidence_graph["nodes"] >= 3


def test_list_scenarios():
    scenarios = RegulatorDemoRunner.list_scenarios()
    assert len(scenarios) == 4
    ids = {s["id"] for s in scenarios}
    assert "p2p_rub_offshore" in ids
