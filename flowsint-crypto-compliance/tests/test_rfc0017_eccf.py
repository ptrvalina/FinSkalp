"""RFC-0017 Evidence & Chain of Custody Framework — tests."""

from __future__ import annotations

import inspect
import re
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import AuditAction, get_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.constraints import eccf_architectural_constraints
from flowsint_crypto_compliance.platform.v2.eccf.id_generator import allocate_evidence_id, reset_id_counters
from flowsint_crypto_compliance.platform.v2.eccf.integrity import verify_integrity
from flowsint_crypto_compliance.platform.v2.eccf.manifest import eccf_manifest
from flowsint_crypto_compliance.platform.v2.eccf.orchestrator import run_eccf_pipeline
from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository, reset_eccf_repository
from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFStage, EvidenceCategory
from flowsint_crypto_compliance.platform.v2.eccf.versioning import create_new_version
from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import reset_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.timeline import reset_evidence_timeline
from flowsint_crypto_compliance.platform.v2.eccf.archive import reset_evidence_archive
from flowsint_crypto_compliance.platform.v2.eccf.report_bridge import reset_report_bridge
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore


@pytest.fixture(autouse=True)
def memory_env(monkeypatch):
    import flowsint_crypto_compliance.platform.v2.knowledge_graph as kg_mod
    import flowsint_crypto_compliance.platform.v2.knowledge_store as ks_mod

    reset_eccf_repository()
    reset_audit_trail()
    reset_evidence_timeline()
    reset_evidence_archive()
    reset_report_bridge()
    reset_id_counters()

    ks_mod._kg_store = None
    kg_mod._kg_service = None
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    mem = KnowledgeGraphStore(use_memory=True)
    kg = kg_mod.KnowledgeGraphService(store=mem)

    def _kg():
        return kg

    for target in (
        "flowsint_crypto_compliance.platform.v2.knowledge_store.get_knowledge_graph_store",
        "flowsint_crypto_compliance.platform.v2.knowledge_graph.get_knowledge_graph_service",
    ):
        monkeypatch.setattr(target, _kg)
    monkeypatch.setattr(
        "flowsint_crypto_compliance.platform.v2.event_bus.PlatformEventBus._persist_postgres",
        lambda *a, **k: None,
    )
    yield


@pytest.fixture
def v2_client():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


@pytest.fixture
def sample_payload():
    return {
        "entity_type": "company",
        "entity_value": "ECCF Test Org",
        "source_type": "registry",
        "payload": {"license": "LIC-001", "confidence": 0.85},
    }


def test_eccf_manifest_stages():
    m = eccf_manifest()
    assert m["rfc"] == "RFC-0017"
    assert m["schema_version"] == "2.0.0"
    assert len(m["pipeline"]) == 9
    assert ECCFStage.SOURCE.value in m["pipeline"]
    assert ECCFStage.ARCHIVE.value in m["pipeline"]
    assert EvidenceCategory.BLOCKCHAIN.value in m["evidence_categories"]
    assert m["evidence_id_format"] == "EV-YYYY-NNNNNNNNNNNN"
    assert "access_control" in m
    assert "architectural_constraints" in m


def test_eccf_evidence_id_format():
    eid = allocate_evidence_id(year=2026)
    assert eid == "EV-2026-000000000001"
    assert re.match(r"^EV-\d{4}-\d{12}$", eid)


@pytest.mark.asyncio
async def test_eccf_full_pipeline_register(sample_payload):
    result = await run_eccf_pipeline(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        collector_payload=sample_payload,
        case_ref="RFC17-TEST",
        collector_id="test-collector",
    )
    assert result.ok
    assert result.evidence_id is not None
    assert result.evidence_id.startswith("EV-")
    assert len(result.stages) == 9
    assert result.integrity_ok
    assert result.record is not None
    assert result.record["immutable"] is True


@pytest.mark.asyncio
async def test_eccf_versioning_immutable(sample_payload):
    result = await run_eccf_pipeline(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        collector_payload=sample_payload,
        case_ref="RFC17-VERSION",
    )
    prior_id = result.evidence_id
    prior = get_eccf_repository().get(prior_id)
    assert prior is not None
    assert prior.immutable is True

    new_payload = {**sample_payload, "payload": {"license": "LIC-002", "confidence": 0.9}}
    new_rec, diff = create_new_version(prior_id, collector_payload=new_payload)
    assert new_rec.version == 2
    assert new_rec.prior_version_id == prior_id
    assert diff["from_version"] == 1
    assert prior.immutable is True


def test_eccf_audit_trail_append_only(sample_payload):
    import asyncio

    result = asyncio.run(
        run_eccf_pipeline(
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            collector_payload=sample_payload,
            case_ref="RFC17-AUDIT",
        )
    )
    trail = get_audit_trail().get_trail(result.evidence_id)
    actions = [e.action for e in trail]
    assert AuditAction.CREATED in actions
    assert AuditAction.HASH_CALCULATED in actions
    assert len(trail) >= 2
    # Append-only: entries have monotonically increasing entry_id
    ids = [e.entry_id for e in trail]
    assert ids == sorted(ids)


def test_eccf_integrity_verify(sample_payload):
    import asyncio

    result = asyncio.run(
        run_eccf_pipeline(
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            collector_payload=sample_payload,
        )
    )
    record = get_eccf_repository().get(result.evidence_id)
    verification = verify_integrity(
        content_hash=record.content_hash,
        size_bytes=record.size_bytes,
        mime_type=record.mime_type,
        payload=record.payload,
        entity_type=record.entity_type,
        entity_value=record.entity_value,
        source_type=record.source_type,
    )
    assert verification["ok"]


def test_eccf_architectural_constraints_no_delete():
    constraints = eccf_architectural_constraints()
    assert "delete_evidence" in constraints["forbidden_actions"]
    assert "modify_content" in constraints["forbidden_actions"]

    from flowsint_crypto_compliance.platform.v2.eccf import graph_bridge

    src = inspect.getsource(graph_bridge)
    assert "get_ingest_pipeline" in src
    assert "KnowledgeGraphService" not in src
    assert "link_relation" not in src


def test_eccf_api_register_and_audit(v2_client, sample_payload):
    reg = v2_client.post(
        "/api/platform/v2/eccf/register",
        json={
            "entity_type": sample_payload["entity_type"],
            "entity_value": sample_payload["entity_value"],
            "source_type": sample_payload["source_type"],
            "case_ref": "RFC17-API",
            "payload": sample_payload["payload"],
        },
    )
    assert reg.status_code == 200
    body = reg.json()
    assert body["ok"] is True
    eid = body["evidence_id"]

    audit = v2_client.get(f"/api/platform/v2/eccf/{eid}/audit")
    assert audit.status_code == 200
    audit_body = audit.json()
    assert audit_body["ok"] is True
    assert audit_body["count"] >= 2
    action_names = [e["action"] for e in audit_body["entries"]]
    assert "Created" in action_names


def test_eccf_manifest_api(v2_client):
    resp = v2_client.get("/api/platform/v2/eccf/manifest")
    assert resp.status_code == 200
    assert resp.json()["rfc"] == "RFC-0017"
