"""RFC-0020 Enterprise Security Architecture — tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.esa.api_protection import api_protection_pipeline
from flowsint_crypto_compliance.platform.v2.esa.audit_system import get_security_audit_log, reset_security_audit_log
from flowsint_crypto_compliance.platform.v2.esa.authorization import evaluate_access
from flowsint_crypto_compliance.platform.v2.esa.constraints import zero_trust_constraints
from flowsint_crypto_compliance.platform.v2.esa.data_classification import classification_rules, data_classification_manifest
from flowsint_crypto_compliance.platform.v2.esa.evidence_security import evidence_security_manifest, verify_evidence_security
from flowsint_crypto_compliance.platform.v2.esa.manifest import esa_manifest
from flowsint_crypto_compliance.platform.v2.esa.orchestrator import evaluate_security_request, record_security_event
from flowsint_crypto_compliance.platform.v2.esa.security_monitoring import reset_security_metrics
from flowsint_crypto_compliance.platform.v2.esa.types import (
    DataClassification,
    EnterpriseRole,
    SecurityPrinciple,
    SecurityResource,
    SecurityUser,
)
from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import AuditAction, get_audit_trail, reset_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.repository import reset_eccf_repository
from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION


@pytest.fixture(autouse=True)
def reset_esa_state():
    reset_security_audit_log()
    reset_security_metrics()
    reset_audit_trail()
    reset_eccf_repository()
    yield
    reset_security_audit_log()
    reset_security_metrics()
    reset_audit_trail()
    reset_eccf_repository()


@pytest.fixture
def v2_client():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_esa_manifest_principles_and_roles():
    m = esa_manifest()
    assert m["rfc"] == "RFC-0020"
    assert m["schema_version"] == SCHEMA_VERSION
    assert m["principle"] == "Zero Trust"
    assert len(m["security_principles"]) == len(SecurityPrinciple)
    assert set(m["enterprise_roles"]) == {r.value for r in EnterpriseRole}
    assert set(m["data_classifications"]) == {c.value for c in DataClassification}
    assert m["authentication"]["require_mfa_for_admin"] is True
    assert m["authorization"]["model"] == "RBAC+ABAC"


def test_rbac_abac_evaluate_access():
    user = SecurityUser(user_id="u1", role=EnterpriseRole.ANALYST, tenant_id="t1")
    resource = SecurityResource(
        resource_type="case",
        resource_id="case-1",
        data_classification=DataClassification.INTERNAL,
        tenant_id="t1",
    )
    allowed = evaluate_access(user, resource, "read")
    assert allowed.allowed is True
    assert allowed.rbac_ok is True
    assert allowed.abac_ok is True

    restricted = SecurityResource(
        resource_type="evidence",
        resource_id="ev-1",
        data_classification=DataClassification.RESTRICTED,
        tenant_id="t1",
    )
    denied = evaluate_access(user, restricted, "export")
    assert denied.allowed is False

    admin_no_mfa = SecurityUser(
        user_id="admin1",
        role=EnterpriseRole.ADMIN,
        tenant_id="t1",
        mfa_verified=False,
    )
    admin_denied = evaluate_access(admin_no_mfa, resource, "read")
    assert admin_denied.allowed is False
    assert admin_denied.reason == "mfa_required_for_admin"


def test_data_classification_rules():
    manifest = data_classification_manifest()
    assert len(manifest["levels"]) == 4
    restricted = classification_rules(DataClassification.RESTRICTED)
    assert restricted["rules"]["storage"]["encryption_required"] is True
    assert restricted["rules"]["export"]["dual_control"] is True
    public = classification_rules(DataClassification.PUBLIC)
    assert public["rules"]["transfer"]["external_sharing"] is True


def test_audit_append_only():
    log = get_security_audit_log()
    e1 = record_security_event(
        event_type="login",
        actor="user1",
        action="authenticate",
        outcome="success",
    )
    e2 = record_security_event(
        event_type="export",
        actor="user1",
        action="export_evidence",
        resource="EV-001",
    )
    assert e1["ok"] is True
    assert e2["ok"] is True
    entries = log.all_entries()
    assert len(entries) == 2
    assert entries[0].entry_id == 1
    assert entries[1].entry_id == 2
    assert not hasattr(log, "delete")
    assert not hasattr(log, "remove")


def test_evidence_security_links_eccf():
    manifest = evidence_security_manifest()
    assert "eccf_bridge" in manifest
    assert manifest["eccf_bridge"]["immutable_audit"] is True
    assert "eccf:view" in manifest["eccf_bridge"]["access_control"]["permissions"]

    trail = get_audit_trail()
    trail.append("EV-TEST-001", AuditAction.CREATED, actor="test")
    check = verify_evidence_security("EV-TEST-001")
    assert check["eccf_linked"] is True
    assert check["integrity_ok"] is True
    assert check["immutable_audit"] is True


def test_api_protection_pipeline_stages():
    pipeline = api_protection_pipeline()
    assert len(pipeline) == 5
    names = [s["name"] for s in pipeline]
    assert names == ["authentication", "authorization", "schema_validation", "rate_limiting", "audit"]
    assert all(s["required"] for s in pipeline)


def test_constraints_zero_trust():
    constraints = zero_trust_constraints()
    assert "verify_explicitly" in constraints["principles"]
    assert "bypass_authentication" in constraints["forbidden_actions"]
    assert "admin_without_mfa" in constraints["forbidden_actions"]
    assert constraints["enforcement"]["authentication"] == "required_on_every_request"


def test_esa_manifest_and_evaluate_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/esa/manifest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rfc"] == "RFC-0020"
    assert body["zero_trust"]["principle_ru"]
    assert "api" in body

    eval_resp = v2_client.post(
        "/api/platform/v2/esa/access/evaluate",
        json={
            "user": {"user_id": "u1", "role": "senior_analyst", "tenant_id": "t1", "mfa_verified": True},
            "resource": {
                "resource_type": "case",
                "resource_id": "c1",
                "data_classification": "internal",
                "tenant_id": "t1",
            },
            "action": "read",
        },
    )
    assert eval_resp.status_code == 200
    result = eval_resp.json()
    assert result["ok"] is True
    assert result["allowed"] is True
    assert result["pipeline_stages"] == 5


def test_evaluate_security_request_orchestrator():
    result = evaluate_security_request(
        user={"user_id": "lead1", "role": "lead", "tenant_id": "t1", "mfa_verified": True},
        resource={
            "resource_type": "evidence",
            "data_classification": "confidential",
            "tenant_id": "t1",
        },
        action="export",
    )
    assert result["allowed"] is True
    assert "decision" in result
