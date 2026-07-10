"""Wave 5 closure tests — KG, maturity, enterprise RDE/ECCF, demo inbox."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from flowsint_crypto_compliance.platform.v2.kg.confidence_propagation import propagate_graph_confidence
from flowsint_crypto_compliance.platform.v2.kg.graph_diff import diff_graph_snapshots
from flowsint_crypto_compliance.platform.v2.maturity.checklist import build_maturity_snapshot
from flowsint_crypto_compliance.reporting.enterprise_sections import enrich_enterprise_sections


def test_graph_diff_detects_added_entity():
    graph_a = {
        "as_of": "2026-01-01T00:00:00Z",
        "entities": [{"id": "e1", "display_name": "A", "version": 1}],
        "relations": [],
    }
    graph_b = {
        "as_of": "2026-01-02T00:00:00Z",
        "entities": [
            {"id": "e1", "display_name": "A", "version": 1},
            {"id": "e2", "display_name": "B", "version": 1},
        ],
        "relations": [],
    }
    diff = diff_graph_snapshots(graph_a, graph_b)
    assert diff["entity_diff"]["added"] == 1
    assert diff["summary"]["net_entities"] == 1


def test_confidence_propagation_from_seed():
    graph = {
        "entities": [
            {"id": "a", "display_name": "Seed"},
            {"id": "b", "display_name": "Neighbor"},
        ],
        "relations": [
            {
                "id": "r1",
                "from_entity_id": "a",
                "to_entity_id": "b",
                "confidence": 0.9,
            }
        ],
    }
    result = propagate_graph_confidence(graph, seed_entity_id="a", min_confidence=0.1)
    assert result["ok"] is True
    assert result["entity_count"] >= 2
    scores = {row["entity_id"]: row["propagated_confidence"] for row in result["propagated"]}
    assert scores["a"] == 1.0
    assert scores["b"] > 0.5


def test_maturity_snapshot_has_dimensions():
    snap = build_maturity_snapshot()
    assert snap["ok"] is True
    assert snap["dimension_count"] >= 19
    assert "knowledge_graph" in snap["dimensions"]
    assert "workspace" in snap["dimensions"]


def test_enterprise_sections_rde_priorities(monkeypatch):
    monkeypatch.setenv("FINSKALP_ENTERPRISE_REPORT_SECTIONS", "1")

    def fake_priorities(case_ref):
        return {"case_ref": case_ref, "priorities": [{"entity": "x", "score": 0.9}]}

    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.gateway.get_rde_priorities",
        fake_priorities,
    )
    report = {"case_ref": "FSK-TEST", "report_type": "forensic"}
    enriched = enrich_enterprise_sections(report, context={"case_ref": "FSK-TEST"})
    assert "rde_priorities" in enriched["enterprise_sections"]


@pytest.mark.asyncio
async def test_demo_inbox_never_empty_in_combat_mode():
    from flowsint_crypto_compliance.demo.operations_center import OperationsCenter

    center = OperationsCenter()
    inbox = await center.list_inbox()
    assert len(inbox) >= 1


@pytest.mark.asyncio
async def test_fz115_report_generated_after_investigation():
    from flowsint_crypto_compliance.demo.investigation_pipeline import InvestigationPipeline
    from flowsint_crypto_compliance.demo.operations_center import OperationsCenter
    from flowsint_crypto_compliance.reporting.fz115_report import FZ115ReportBuilder

    center = OperationsCenter()
    inbox = await center.list_inbox()
    assert inbox
    alert = await center.get_alert(inbox[0]["id"])
    pipeline = InvestigationPipeline(step_delay_ms=0)
    _steps, report = await pipeline.run(alert["scenario_id"])
    fz115 = FZ115ReportBuilder().build(alert=alert, investigation_report=report).to_dict()

    assert fz115["report_id"].startswith("ОТЧ-115-")
    assert "115-ФЗ" in fz115["report_type_ru"]
    assert fz115["decision_ru"]
    assert len(fz115["recommended_actions_ru"]) >= 2
    assert fz115["suspicion_signs"]
