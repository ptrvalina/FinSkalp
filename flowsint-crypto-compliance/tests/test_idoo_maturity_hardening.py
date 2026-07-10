"""Wave 4 — IDOO maturity hardening (real probes, backup runner, OTEL flag)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from flowsint_crypto_compliance.feature_flags import flag_snapshot
from flowsint_crypto_compliance.platform.v2.idoo.backup import backup_manifest
from flowsint_crypto_compliance.platform.v2.idoo.backup_runner import run_backup
from flowsint_crypto_compliance.platform.v2.idoo.disaster_recovery import dr_readiness_snapshot
from flowsint_crypto_compliance.platform.v2.idoo.health_probes import (
    probe_neo4j,
    probe_postgres,
    probe_redis,
)
from flowsint_crypto_compliance.platform.v2.idoo.monitoring import reset_idoo_metrics
from flowsint_crypto_compliance.platform.v2.idoo.orchestrator import get_platform_health
from flowsint_crypto_compliance.platform.v2.idoo.types import ServiceHealth


@pytest.fixture(autouse=True)
def reset_idoo_state():
    reset_idoo_metrics()
    yield
    reset_idoo_metrics()


def test_health_stub_mode_by_default(monkeypatch):
    monkeypatch.delenv("FINSKALP_IDOO_REAL_HEALTH_PROBES", raising=False)
    health = get_platform_health()
    assert health["probe_mode"] == "stub"
    assert health["healthy_count"] == 5
    assert health["probes"][0]["details"]["mode"] == "stub"
    assert "feature_flags" in health


def test_real_probe_postgres_success(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://local/test")
    session = MagicMock()
    with patch("flowsint_core.core.postgre_db.SessionLocal", return_value=session):
        result = probe_postgres("pg_isready")
    assert result.status == ServiceHealth.HEALTHY
    assert result.details["mode"] == "real"
    session.execute.assert_called_once()
    session.close.assert_called_once()


def test_real_probe_redis_skipped_without_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    result = probe_redis("redis-cli ping")
    assert result.status == ServiceHealth.DEGRADED
    assert result.details["mode"] == "skipped"


def test_real_probe_neo4j_skipped_without_uri(monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_URL", raising=False)
    result = probe_neo4j("cypher-shell")
    assert result.status == ServiceHealth.DEGRADED
    assert result.details["reason"] == "NEO4J_URI not configured"


def test_real_health_mode_when_flag_on(monkeypatch):
    monkeypatch.setenv("FINSKALP_IDOO_REAL_HEALTH_PROBES", "1")
    healthy = MagicMock(
        service="postgres",
        status=ServiceHealth.HEALTHY,
        endpoint="pg",
        latency_ms=1.0,
        details={"mode": "real"},
    )
    healthy.to_dict = lambda: {
        "service": "postgres",
        "status": "healthy",
        "endpoint": "pg",
        "latency_ms": 1.0,
        "details": {"mode": "real"},
    }
    with patch(
        "flowsint_crypto_compliance.platform.v2.idoo.health_probes.run_real_probe",
        return_value=healthy,
    ):
        health = get_platform_health()
    assert health["probe_mode"] == "real"
    assert health["probes"][0]["details"]["mode"] == "real"


def test_backup_manifest_without_runner_flag(monkeypatch):
    monkeypatch.delenv("FINSKALP_IDOO_BACKUP_RUNNER", raising=False)
    manifest = backup_manifest()
    assert "runtime" not in manifest
    assert "dr_readiness" not in manifest


def test_backup_manifest_with_runner_flag(monkeypatch):
    monkeypatch.setenv("FINSKALP_IDOO_BACKUP_RUNNER", "1")
    manifest = backup_manifest()
    assert manifest["runtime"]["runner_enabled"] is True
    assert "dr_readiness" in manifest


def test_backup_runner_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("FINSKALP_BACKUP_DIR", str(tmp_path))
    result = run_backup(dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert not any(tmp_path.iterdir())


def test_backup_runner_writes_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("FINSKALP_BACKUP_DIR", str(tmp_path))
    result = run_backup(dry_run=False)
    assert result["ok"] is True
    manifest_path = result["manifest_path"]
    assert os.path.isfile(manifest_path)
    readiness = dr_readiness_snapshot()
    assert readiness["last_backup_at"] is not None


def test_otel_flag_enables_tracing(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("FINSKALP_OTEL_ENABLED", "1")
    from flowsint_crypto_compliance.observability.tracing import otel_enabled

    assert otel_enabled() is True


def test_flag_snapshot_includes_wave4_flags():
    snap = flag_snapshot()
    assert "idoo_real_health_probes" in snap
    assert "idoo_backup_runner" in snap
    assert "otel_tracing" in snap
