"""RFC-0009 RBAC Harmonization — tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.rbac.harmonization import (
    effective_compliance_role,
    harmonized_manifest,
    harmonized_user_has_permission,
)
from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router
from flowsint_crypto_compliance.services.compliance_rbac import ComplianceRole


def test_harmonized_manifest_structure():
    m = harmonized_manifest()
    assert m["rfc"] == "RFC-0009"
    assert "owner" in m["investigation_to_compliance"]
    assert m["investigation_to_compliance"]["owner"] == "admin"
    assert "case:read" in m["compliance_permissions"]
    assert "workspace:comment" in m["platform_permissions"]


def test_effective_role_takes_max_of_planes():
    base = ComplianceRole.VIEWER
    with_editor = effective_compliance_role(base, ["editor"])
    assert with_editor == ComplianceRole.SENIOR_ANALYST
    with_owner = effective_compliance_role(ComplianceRole.ANALYST, ["owner"])
    assert with_owner == ComplianceRole.ADMIN


def test_harmonized_permission_workspace_comment():
    assert harmonized_user_has_permission(ComplianceRole.ANALYST, "workspace:comment")
    assert not harmonized_user_has_permission(ComplianceRole.VIEWER, "workspace:comment")
    assert harmonized_user_has_permission(ComplianceRole.VIEWER, "case:read")


@pytest.fixture
def v2_client():
    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_rbac_manifest_api(v2_client):
    resp = v2_client.get("/api/platform/v2/rbac/manifest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rfc"] == "RFC-0009"
    assert body["rule_ru"]
