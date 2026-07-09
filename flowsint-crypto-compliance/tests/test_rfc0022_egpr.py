"""RFC-0022 Enterprise Governance & Product Roadmap — tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.egpr.adr_registry import adr_registry_manifest, list_adrs
from flowsint_crypto_compliance.platform.v2.egpr.architecture_board import (
    board_workflow_manifest,
    submit_board_review,
)
from flowsint_crypto_compliance.platform.v2.egpr.manifest import egpr_manifest
from flowsint_crypto_compliance.platform.v2.egpr.maturity import maturity_manifest
from flowsint_crypto_compliance.platform.v2.egpr.orchestrator import evaluate_maturity
from flowsint_crypto_compliance.platform.v2.egpr.roadmap import roadmap_manifest
from flowsint_crypto_compliance.platform.v2.egpr.rfc_lifecycle import get_rfc_catalog
from flowsint_crypto_compliance.platform.v2.egpr.tech_debt import tech_debt_manifest
from flowsint_crypto_compliance.platform.v2.egpr.types import RoadmapPhase, StrategicPrinciple
from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION


@pytest.fixture
def v2_client():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_egpr_manifest_mission_and_principles():
    m = egpr_manifest()
    assert m["rfc"] == "RFC-0022"
    assert m["schema_version"] == SCHEMA_VERSION
    assert m["volume_i_status"] == "complete"
    assert m["volume_i_badge_ru"] == "Volume I Complete"
    assert len(m["strategic_principles"]) == len(StrategicPrinciple)
    assert m["mission"]["chapter"] == 1
    assert "mission_ru" in m["mission"]
    assert m["principles"]["principle_count"] == 10


def test_rfc_catalog_includes_0000_through_0021():
    catalog = get_rfc_catalog()
    assert len(catalog) == 22
    ids = {r["id"] for r in catalog}
    for n in range(22):
        assert f"RFC-{n:04d}" in ids
    stages = {r["stage"] for r in catalog}
    assert "complete" in stages
    assert "accepted" in stages
    assert "draft" in stages


def test_adr_registry_structure():
    manifest = adr_registry_manifest()
    adrs = list_adrs()
    assert manifest["count"] == 3
    assert len(adrs) == 3
    for adr in adrs:
        assert "id" in adr
        assert "context" in adr
        assert "options" in adr
        assert "decision" in adr
        assert "rationale" in adr
        assert "consequences" in adr
        assert "related_rfc" in adr
    related = {a["related_rfc"] for a in adrs}
    assert related == {"RFC-0002", "RFC-0009", "RFC-0019"}


def test_roadmap_four_phases():
    roadmap = roadmap_manifest()
    assert roadmap["phase_count"] == 4
    phases = [p["phase"] for p in roadmap["phases"]]
    assert phases == [p.value for p in RoadmapPhase]
    complete = [p for p in roadmap["phases"] if p["status"] == "complete"]
    assert len(complete) == 3
    assert roadmap["volume_i_status"] == "complete"


def test_maturity_evaluation():
    result = evaluate_maturity()
    assert result["ok"] is True
    assert result["volume_i_status"] == "complete"
    assert result["maturity"]["total_count"] >= 8
    assert result["maturity"]["maturity_score_percent"] >= 75.0
    assert result["rfc_summary"]["total"] == 22

    mat = maturity_manifest()
    assert mat["volume_i_ready"] is True


def test_tech_debt_bridge():
    debt = tech_debt_manifest()
    assert debt["source"] == "docs/audit/technical-debt.md"
    assert debt["total"] >= 8
    assert "critical" in debt["by_severity"]
    assert debt["open_count"] >= 1
    ids = {i["id"] for i in debt["items"]}
    assert "TD-C1" in ids
    assert "TD-C4" in ids


def test_architecture_board_workflow():
    board = board_workflow_manifest()
    assert board["chapter"] == 3
    assert board["quorum"] == 3
    assert len(board["workflow"]["steps"]) == 5
    review = submit_board_review(
        subject="RFC-0023 proposal",
        requester="platform_lead",
        details={"rfc_id": "RFC-0023"},
    )
    assert review["ok"] is True
    assert review["review"]["status"] == "pending"


def test_egpr_manifest_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/egpr/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["rfc"] == "RFC-0022"
    assert data["title_ru"] == "Корпоративное управление и дорожная карта продукта v2.0"
    assert data["api"]["maturity"] == "/api/platform/v2/egpr/maturity"
    assert data["volume_i_badge_ru"] == "Volume I Complete"


def test_egpr_rfc_catalog_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/egpr/rfc-catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["count"] == 22


def test_egpr_maturity_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/egpr/maturity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["volume_i_status"] == "complete"
