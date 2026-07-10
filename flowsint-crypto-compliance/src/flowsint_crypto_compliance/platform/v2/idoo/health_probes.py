"""RFC-0021 — real service health probes (Wave 4, behind feature flag).

When ``FINSKALP_IDOO_REAL_HEALTH_PROBES`` is unset, the orchestrator keeps the
legacy stub behaviour. These probes are best-effort: missing optional deps or
env vars yield ``degraded`` with ``mode: skipped``, not ``unhealthy``.
"""

from __future__ import annotations

import logging
import os
import socket
import time
from typing import Any
from urllib.parse import urlparse

from flowsint_crypto_compliance.platform.v2.idoo.types import HealthProbeResult, ServiceHealth

logger = logging.getLogger(__name__)

_PROBE_TIMEOUT_SEC = float(os.getenv("FINSKALP_HEALTH_PROBE_TIMEOUT_SEC", "3"))


def _redis_url() -> str | None:
    url = os.getenv("REDIS_URL", "").strip()
    if url:
        return url
    broker = os.getenv("CELERY_BROKER_URL", "").strip()
    if broker.startswith("redis://") or broker.startswith("rediss://"):
        return broker
    return None


def _api_health_url() -> str:
    explicit = os.getenv("FINSKALP_API_HEALTH_URL", "").strip()
    if explicit:
        return explicit
    base = os.getenv("COMPLIANCE_API_URL", "").strip().rstrip("/")
    if base:
        return f"{base}/api/health/live"
    port = os.getenv("COMPLIANCE_PORT", "8877").strip() or "8877"
    return f"http://127.0.0.1:{port}/api/health/live"


def probe_postgres(endpoint: str) -> HealthProbeResult:
    start = time.perf_counter()
    details: dict[str, Any] = {"mode": "real", "check": "select_1"}
    status = ServiceHealth.HEALTHY
    try:
        from sqlalchemy import text

        from flowsint_core.core.postgre_db import SessionLocal

        session = SessionLocal()
        try:
            session.execute(text("SELECT 1"))
        finally:
            session.close()
        details["database_url_configured"] = bool(os.getenv("DATABASE_URL"))
    except Exception as exc:
        status = ServiceHealth.UNHEALTHY
        details["error"] = str(exc)[:200]
        logger.warning("idoo health probe postgres failed: %s", exc)
    elapsed = (time.perf_counter() - start) * 1000.0
    return HealthProbeResult(
        service="postgres",
        status=status,
        endpoint=endpoint,
        latency_ms=elapsed,
        details=details,
    )


def probe_redis(endpoint: str) -> HealthProbeResult:
    start = time.perf_counter()
    details: dict[str, Any] = {"mode": "real", "check": "ping"}
    status = ServiceHealth.HEALTHY
    url = _redis_url()
    if not url:
        return HealthProbeResult(
            service="redis",
            status=ServiceHealth.DEGRADED,
            endpoint=endpoint,
            latency_ms=(time.perf_counter() - start) * 1000.0,
            details={**details, "mode": "skipped", "reason": "REDIS_URL not configured"},
        )
    try:
        import redis

        client = redis.from_url(url, socket_connect_timeout=_PROBE_TIMEOUT_SEC)
        pong = client.ping()
        details["pong"] = bool(pong)
    except Exception as exc:
        status = ServiceHealth.UNHEALTHY
        details["error"] = str(exc)[:200]
        logger.warning("idoo health probe redis failed: %s", exc)
    elapsed = (time.perf_counter() - start) * 1000.0
    return HealthProbeResult(
        service="redis",
        status=status,
        endpoint=endpoint,
        latency_ms=elapsed,
        details=details,
    )


def probe_neo4j(endpoint: str) -> HealthProbeResult:
    start = time.perf_counter()
    details: dict[str, Any] = {"mode": "real", "check": "tcp_connect"}
    uri = os.getenv("NEO4J_URI", "").strip() or os.getenv("NEO4J_URL", "").strip()
    if not uri:
        return HealthProbeResult(
            service="neo4j",
            status=ServiceHealth.DEGRADED,
            endpoint=endpoint,
            latency_ms=(time.perf_counter() - start) * 1000.0,
            details={**details, "mode": "skipped", "reason": "NEO4J_URI not configured"},
        )
    status = ServiceHealth.HEALTHY
    try:
        parsed = urlparse(uri.replace("neo4j://", "bolt://").replace("neo4j+s://", "bolt+s://"))
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 7687
        with socket.create_connection((host, port), timeout=_PROBE_TIMEOUT_SEC):
            details["host"] = host
            details["port"] = port
    except Exception as exc:
        status = ServiceHealth.UNHEALTHY
        details["error"] = str(exc)[:200]
        logger.warning("idoo health probe neo4j failed: %s", exc)
    elapsed = (time.perf_counter() - start) * 1000.0
    return HealthProbeResult(
        service="neo4j",
        status=status,
        endpoint=endpoint,
        latency_ms=elapsed,
        details=details,
    )


def probe_celery(endpoint: str) -> HealthProbeResult:
    start = time.perf_counter()
    details: dict[str, Any] = {"mode": "real", "check": "broker_ping"}
    broker = os.getenv("CELERY_BROKER_URL", "").strip()
    if not broker and not _redis_url():
        return HealthProbeResult(
            service="celery",
            status=ServiceHealth.DEGRADED,
            endpoint=endpoint,
            latency_ms=(time.perf_counter() - start) * 1000.0,
            details={**details, "mode": "skipped", "reason": "CELERY_BROKER_URL not configured"},
        )
    status = ServiceHealth.HEALTHY
    try:
        if broker.startswith("redis://") or broker.startswith("rediss://") or not broker:
            import redis

            url = broker or _redis_url() or ""
            client = redis.from_url(url, socket_connect_timeout=_PROBE_TIMEOUT_SEC)
            client.ping()
            details["broker"] = "redis"
        else:
            details["broker"] = broker.split("://", 1)[0]
            details["note"] = "non-redis broker; connectivity not verified"
            status = ServiceHealth.DEGRADED
    except Exception as exc:
        status = ServiceHealth.UNHEALTHY
        details["error"] = str(exc)[:200]
        logger.warning("idoo health probe celery failed: %s", exc)
    elapsed = (time.perf_counter() - start) * 1000.0
    return HealthProbeResult(
        service="celery",
        status=status,
        endpoint=endpoint,
        latency_ms=elapsed,
        details=details,
    )


def probe_api(endpoint: str) -> HealthProbeResult:
    start = time.perf_counter()
    url = _api_health_url()
    details: dict[str, Any] = {"mode": "real", "check": "http_get", "url": url}
    status = ServiceHealth.HEALTHY
    try:
        import httpx

        response = httpx.get(url, timeout=_PROBE_TIMEOUT_SEC)
        details["status_code"] = response.status_code
        if response.status_code != 200:
            status = ServiceHealth.UNHEALTHY
    except Exception as exc:
        status = ServiceHealth.DEGRADED
        details["error"] = str(exc)[:200]
        logger.warning("idoo health probe api failed: %s", exc)
    elapsed = (time.perf_counter() - start) * 1000.0
    return HealthProbeResult(
        service="api",
        status=status,
        endpoint=endpoint or url,
        latency_ms=elapsed,
        details=details,
    )


_REAL_PROBES: dict[str, Any] = {
    "api": probe_api,
    "celery": probe_celery,
    "postgres": probe_postgres,
    "redis": probe_redis,
    "neo4j": probe_neo4j,
}


def run_real_probe(service: str, endpoint: str) -> HealthProbeResult:
    fn = _REAL_PROBES.get(service)
    if fn is None:
        return HealthProbeResult(
            service=service,
            status=ServiceHealth.UNKNOWN,
            endpoint=endpoint,
            details={"mode": "real", "error": "no probe registered"},
        )
    return fn(endpoint)
