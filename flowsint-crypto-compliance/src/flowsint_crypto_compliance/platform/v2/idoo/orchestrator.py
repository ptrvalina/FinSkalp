"""RFC-0021 IDOO orchestrator — platform health and observability snapshots."""

from __future__ import annotations

import time
from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.monitoring import get_idoo_metrics, monitoring_manifest
from flowsint_crypto_compliance.platform.v2.idoo.observability import observability_manifest
from flowsint_crypto_compliance.platform.v2.idoo.types import HealthProbeResult, ServiceHealth


def _probe_service(service: str, endpoint: str) -> HealthProbeResult:
    """Stub health probe — returns healthy in dev/test; records metrics."""
    start = time.perf_counter()
    metrics = get_idoo_metrics()

    status = ServiceHealth.HEALTHY
    details: dict[str, Any] = {"mode": "stub"}

    if service == "api":
        details["path"] = "/health"
    elif service == "celery":
        details["check"] = "celery inspect ping"
    elif service in ("postgres", "redis", "neo4j"):
        details["check"] = endpoint

    elapsed = (time.perf_counter() - start) * 1000.0
    metrics.record_probe(service=service, status=status)

    return HealthProbeResult(
        service=service,
        status=status,
        endpoint=endpoint,
        latency_ms=elapsed,
        details=details,
    )


def get_platform_health() -> dict[str, Any]:
    """Aggregate health snapshot for all catalogued services."""
    catalog = monitoring_manifest()["health_checks"]
    probes = [
        _probe_service(
            str(check["service"]),
            str(check.get("endpoint", "")),
        )
        for check in catalog
    ]

    statuses = [p.status for p in probes]
    if all(s == ServiceHealth.HEALTHY for s in statuses):
        overall = ServiceHealth.HEALTHY
    elif any(s == ServiceHealth.UNHEALTHY for s in statuses):
        overall = ServiceHealth.UNHEALTHY
    elif any(s == ServiceHealth.DEGRADED for s in statuses):
        overall = ServiceHealth.DEGRADED
    else:
        overall = ServiceHealth.UNKNOWN

    return {
        "ok": overall in (ServiceHealth.HEALTHY, ServiceHealth.DEGRADED),
        "overall_status": overall.value,
        "service_count": len(probes),
        "healthy_count": sum(1 for p in probes if p.status == ServiceHealth.HEALTHY),
        "probes": [p.to_dict() for p in probes],
        "metrics": get_idoo_metrics().get_metrics(),
    }


def collect_observability_snapshot() -> dict[str, Any]:
    """Unified observability snapshot — metrics, logs, traces pillars."""
    obs = observability_manifest()
    health = get_platform_health()
    return {
        "ok": True,
        "pillars": obs["pillars"],
        "metrics": {
            "backend": obs["metrics"]["backend"],
            "health_probes": health["metrics"],
        },
        "logs": {
            "backend": obs["logs"]["backend"],
            "format": obs["logs"]["format"],
        },
        "traces": {
            "backend": obs["traces"]["backend"],
            "correlation_header": obs["traces"]["propagation"],
        },
        "platform_health": health,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def run_health_probe_batch() -> dict[str, Any]:
    """Celery beat entry — periodic health probe for all services."""
    result = get_platform_health()
    return {
        "ok": True,
        "task": "idoo_health_probe_batch",
        **result,
    }
