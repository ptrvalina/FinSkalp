"""RFC-0021 IDOO v2.0 — core infrastructure types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InfraPrinciple(str, Enum):
    """RFC-0021 Ch.1 — infrastructure & DevOps principles."""

    INFRASTRUCTURE_AS_CODE = "infrastructure_as_code"
    GITOPS_SINGLE_SOURCE = "gitops_single_source"
    IMMUTABLE_ARTIFACTS = "immutable_artifacts"
    OBSERVABILITY_BY_DEFAULT = "observability_by_default"
    AUTOMATED_RECOVERY = "automated_recovery"
    LEAST_PRIVILEGE_ACCESS = "least_privilege_access"
    SECRETS_NEVER_IN_CODE = "secrets_never_in_code"
    ENVIRONMENT_PARITY = "environment_parity"


class Environment(str, Enum):
    """RFC-0021 Ch.7 — deployment environments."""

    DEV = "dev"
    TEST = "test"
    STAGE = "stage"
    PROD = "prod"


class ObservabilitySignal(str, Enum):
    """RFC-0021 Ch.8 — three pillars of observability."""

    METRICS = "metrics"
    LOGS = "logs"
    TRACES = "traces"


class ServiceHealth(str, Enum):
    """RFC-0021 Ch.9 — service health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthProbeResult:
    """Result of a single service health probe."""

    service: str
    status: ServiceHealth
    endpoint: str = ""
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "status": self.status.value,
            "endpoint": self.endpoint,
            "latency_ms": round(self.latency_ms, 2),
            "details": dict(self.details),
        }
