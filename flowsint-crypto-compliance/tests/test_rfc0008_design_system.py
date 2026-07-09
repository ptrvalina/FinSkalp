"""RFC-0008 Enterprise Design System — tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.design_system import design_system_manifest
from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router


@pytest.fixture
def v2_client():
    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_design_system_manifest_structure():
    m = design_system_manifest()
    assert m["rfc"] == "RFC-0008"
    assert len(m["principles"]) == 5
    assert set(m["themes"]) == {"light", "dark", "high-contrast"}
    assert m["spacing_px"] == [4, 8, 16, 24, 32, 48]
    assert "wallet" in m["graph_entity_colors"]
    assert "investigation" in m["entity_icons"]
    assert "navigation" in m["components"]


def test_design_system_api_route(v2_client):
    resp = v2_client.get("/api/platform/v2/design-system/manifest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rfc"] == "RFC-0008"
    assert body["philosophy_ru"]
