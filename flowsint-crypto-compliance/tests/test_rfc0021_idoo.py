"""RFC-0021 Infrastructure, DevOps & Observability — tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION
from flowsint_crypto_compliance.platform.v2.idoo.constraints import constraints_manifest
from flowsint_crypto_compliance.platform.v2.idoo.logging import LOG_SCHEMA_FIELDS, logging_manifest
from flowsint_crypto_compliance.platform.v2.idoo.manifest import idoo_manifest
from flowsint_crypto_compliance.platform.v2.idoo.monitoring import reset_idoo_metrics
from flowsint_crypto_compliance.platform.v2.idoo.observability import observability_manifest
from flowsint_crypto_compliance.platform.v2.idoo.orchestrator import get_platform_health
from flowsint_crypto_compliance.platform.v2.idoo.queues import queues_manifest
from flowsint_crypto_compliance.platform.v2.idoo.topology import topology_manifest
from flowsint_crypto_compliance.platform.v2.idoo.types import (
    Environment,
    InfraPrinciple,
    ObservabilitySignal,
)


@pytest.fixture(autouse=True)
def reset_idoo_state():
    reset_idoo_metrics()
    yield
    reset_idoo_metrics()


@pytest.fixture
def v2_client():
    from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router

    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


def test_idoo_manifest_principles():
    m = idoo_manifest()
    assert m["rfc"] == "RFC-0021"
    assert m["schema_version"] == SCHEMA_VERSION
    assert m["principle"] == "Infrastructure as Code"
    assert len(m["infra_principles"]) == len(InfraPrinciple)
    assert set(m["environments"]) == {e.value for e in Environment}
    assert set(m["observability_signals"]) == {s.value for s in ObservabilitySignal}
    assert m["principles"]["chapter"] == 1
    assert len(m["constraints"]["forbidden_practices"]) >= 5


def test_topology_pipeline_stages():
    topo = topology_manifest()
    stages = [s["stage"] for s in topo["pipeline"]]
    assert stages == [
        "git",
        "ci",
        "artifact",
        "cd",
        "k8s",
        "services",
        "db",
        "monitoring",
        "backup",
        "dr",
    ]
    assert topo["stage_count"] == 10
    assert "docker-compose.dev.yml" in topo["compose_files"]


def test_observability_three_pillars():
    obs = observability_manifest()
    assert set(obs["pillars"]) == {"metrics", "logs", "traces"}
    assert obs["metrics"]["backend"] == "Prometheus"
    assert obs["logs"]["backend"] == "Loki"
    assert obs["traces"]["backend"] == "Tempo"
    manifest_obs = idoo_manifest()["observability"]
    assert manifest_obs["pillars"] == obs["pillars"]


def test_queue_catalog_includes_celery_beats():
    q = queues_manifest()
    task_names = {t["task"] for t in q["beat_schedule"]}
    assert "icf_run_scheduled_collections" in task_names
    assert "crif_sync_registries" in task_names
    assert "rde_batch_reassess" in task_names
    assert "eccf_verify_integrity_batch" in task_names
    assert "eia_warm_context_cache" in task_names
    assert "aspp_deliver_webhooks" in task_names
    assert "esa_security_scan_batch" in task_names
    assert "idoo_health_probe_batch" in task_names
    assert q["platform_task_count"] >= 8


def test_logging_schema_fields():
    log = logging_manifest()
    assert "timestamp" in log["required_fields"]
    assert "service" in log["required_fields"]
    assert "version" in log["required_fields"]
    assert "correlation_id" in log["required_fields"]
    assert log["required_fields"] == LOG_SCHEMA_FIELDS
    assert log["format"] == "json"


def test_constraints_forbidden_practices():
    c = constraints_manifest()
    assert "secrets_in_git" in c["forbidden_practices"]
    assert "manual_production_changes" in c["forbidden_practices"]
    assert "deploy_without_tests" in c["forbidden_practices"]
    assert c["enforcement"]["ci_gates"] == "tests must pass before merge"


def test_health_snapshot():
    health = get_platform_health()
    assert health["ok"] is True
    assert health["service_count"] == 5
    assert health["healthy_count"] == 5
    assert health["overall_status"] == "healthy"
    services = {p["service"] for p in health["probes"]}
    assert services == {"api", "celery", "postgres", "redis", "neo4j"}


def test_idoo_manifest_endpoint(v2_client):
    resp = v2_client.get("/api/platform/v2/idoo/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["rfc"] == "RFC-0021"
    assert data["title_ru"] == "Инфраструктура, DevOps и наблюдаемость v2.0"
    assert data["api"]["health"] == "/api/platform/v2/idoo/health"
