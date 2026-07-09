import pytest

from flowsint_crypto_compliance.demo.operations_center import OperationsCenter
from flowsint_crypto_compliance.reporting.fz115_report import FZ115ReportBuilder


@pytest.mark.asyncio
async def test_alert_has_official_code_and_typology():
    center = OperationsCenter()
    inbox = await center.list_inbox()
    assert inbox[0]["alert_code"].startswith("STR-") or inbox[0]["alert_code"].startswith("MON-PAT")
    assert inbox[0]["typology_code"].startswith("ПФТ-")
    assert inbox[0]["legal_signs_ru"]


@pytest.mark.asyncio
async def test_fz115_report_generated_after_investigation():
    from flowsint_crypto_compliance.demo.investigation_pipeline import InvestigationPipeline

    center = OperationsCenter()
    alert = await center.get_alert((await center.list_inbox())[0]["id"])
    pipeline = InvestigationPipeline(step_delay_ms=0)
    steps, report = await pipeline.run(alert["scenario_id"])
    fz115 = FZ115ReportBuilder().build(alert=alert, investigation_report=report).to_dict()

    assert fz115["report_id"].startswith("ОТЧ-115-")
    assert "115-ФЗ" in fz115["report_type_ru"]
    assert fz115["decision_ru"]
    assert len(fz115["recommended_actions_ru"]) >= 2
    assert fz115["suspicion_signs"]
