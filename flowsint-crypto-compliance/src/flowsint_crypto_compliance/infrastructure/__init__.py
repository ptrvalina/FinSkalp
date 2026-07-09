"""FinSkalp production infrastructure — events, CQRS, resilience."""

from flowsint_crypto_compliance.infrastructure.circuit_breaker import CollectorCircuitBreaker, get_breaker
from flowsint_crypto_compliance.infrastructure.compliance_events import ComplianceEventBus, get_event_bus
from flowsint_crypto_compliance.infrastructure.idempotency import IdempotencyStore

__all__ = [
    "CollectorCircuitBreaker",
    "ComplianceEventBus",
    "IdempotencyStore",
    "get_breaker",
    "get_event_bus",
]

def __getattr__(name: str):
    if name == "ComplianceDashboardReadModel":
        from flowsint_crypto_compliance.infrastructure.read_models import ComplianceDashboardReadModel
        return ComplianceDashboardReadModel
    raise AttributeError(name)
