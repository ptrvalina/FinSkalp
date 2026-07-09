"""RFC-0020 ESA service facade."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.esa.data_classification import data_classification_manifest
from flowsint_crypto_compliance.platform.v2.esa.manifest import esa_manifest
from flowsint_crypto_compliance.platform.v2.esa.orchestrator import (
    evaluate_security_request,
    record_security_event,
)
from flowsint_crypto_compliance.platform.v2.esa.security_monitoring import get_security_metrics
from flowsint_crypto_compliance.platform.v2.esa.siem import siem_manifest
from flowsint_crypto_compliance.platform.v2.esa.threat_model import threat_model_manifest
from flowsint_crypto_compliance.platform.v2.esa.types import SecurityAuditEventType


class ESAService:
    """Enterprise Security Architecture service."""

    def manifest(self) -> dict[str, Any]:
        return esa_manifest()

    def evaluate_access(
        self,
        *,
        user: dict[str, Any],
        resource: dict[str, Any],
        action: str,
        attributes: dict[str, Any] | None = None,
        db: Any = None,
    ) -> dict[str, Any]:
        return evaluate_security_request(
            user=user,
            resource=resource,
            action=action,
            attributes=attributes,
            db=db,
        )

    def record_audit(
        self,
        *,
        event_type: str,
        actor: str,
        action: str,
        resource: str = "",
        outcome: str = "success",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return record_security_event(
            event_type=SecurityAuditEventType(event_type),
            actor=actor,
            action=action,
            resource=resource,
            outcome=outcome,
            details=details,
        )

    def threat_model(self) -> dict[str, Any]:
        return threat_model_manifest()

    def monitoring(self) -> dict[str, Any]:
        return {"ok": True, **get_security_metrics().get_metrics()}

    def siem_config(self) -> dict[str, Any]:
        return siem_manifest()

    def data_classification(self) -> dict[str, Any]:
        return data_classification_manifest()


_service: ESAService | None = None


def get_esa_service() -> ESAService:
    global _service
    if _service is None:
        _service = ESAService()
    return _service
