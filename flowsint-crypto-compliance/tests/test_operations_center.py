import pytest

from flowsint_crypto_compliance.demo.investigation_pipeline import InvestigationPipeline
from flowsint_crypto_compliance.demo.operations_center import OperationsCenter


@pytest.fixture(autouse=True)
def _offline_demo(monkeypatch):
    """Demo inbox seeds require COMPLIANCE_COMBAT_MODE=0."""
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "0")

@pytest.mark.asyncio
async def test_operations_center_seed_inbox():
    center = OperationsCenter()
    inbox = await center.list_inbox()
    assert len(inbox) >= 2
    sources = {a["source"] for a in inbox}
    assert "bank_hub" in sources
    assert "pattern_monitor" in sources


@pytest.mark.asyncio
async def test_receive_bank_str_adds_alert():
    center = OperationsCenter()
    before = len(await center.list_inbox())
    alert = await center.receive_bank_str("cross_border_do")
    assert alert["source"] == "bank_hub"
    assert alert["bank_name"]
    after = len(await center.list_inbox())
    assert after == before + 1


@pytest.mark.asyncio
async def test_pattern_scan_finds_remaining():
    center = OperationsCenter()
    found = await center.run_pattern_scan()
    assert len(found) >= 1
    # second scan should not duplicate
    found2 = await center.run_pattern_scan()
    assert len(found2) == 0


@pytest.mark.asyncio
async def test_investigation_pipeline_produces_report():
    pipeline = InvestigationPipeline(step_delay_ms=0)
    steps, report = await pipeline.run("sbp_gray_hub")
    assert len(steps) >= 6
    assert all(s["status"] == "done" for s in steps)
    assert report["illegal_flow_score"] >= 40
    assert report["case_ref"] == "DEMO-RU-004"


@pytest.mark.asyncio
async def test_full_investigate_flow():
    center = OperationsCenter()
    inbox = await center.list_inbox()
    alert_id = inbox[0]["id"]
    scenario_id = inbox[0]["scenario_id"]

    pipeline = InvestigationPipeline(step_delay_ms=0)
    steps, report = await pipeline.run(scenario_id)
    await center.update_alert(alert_id, status="completed", report=report, steps=steps)

    updated = await center.get_alert(alert_id)
    assert updated["status"] == "completed"
    assert updated["has_report"]
