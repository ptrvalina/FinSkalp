"""RFC-0020 ESA orchestrator — evaluate_security_request, record_security_event."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.esa.api_protection import api_protection_pipeline
from flowsint_crypto_compliance.platform.v2.esa.audit_system import get_security_audit_log
from flowsint_crypto_compliance.platform.v2.esa.authentication import admin_requires_mfa
from flowsint_crypto_compliance.platform.v2.esa.authorization import evaluate_access
from flowsint_crypto_compliance.platform.v2.esa.constraints import assert_zero_trust
from flowsint_crypto_compliance.platform.v2.esa.security_monitoring import get_security_metrics
from flowsint_crypto_compliance.platform.v2.esa.types import (
    DataClassification,
    EnterpriseRole,
    SecurityAuditEventType,
    SecurityResource,
    SecurityUser,
)
from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent


def evaluate_security_request(
    *,
    user: dict[str, Any],
    resource: dict[str, Any],
    action: str,
    attributes: dict[str, Any] | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Full security request evaluation — auth check + RBAC/ABAC + pipeline metadata."""
    metrics = get_security_metrics()
    pipeline = api_protection_pipeline()

    role = str(user.get("role", EnterpriseRole.ANALYST.value))
    mfa_verified = bool(user.get("mfa_verified", False))

    if not admin_requires_mfa(role, mfa_verified=mfa_verified):
        metrics.record_failed_auth()
        metrics.record_access_denied()
        record_security_event(
            event_type=SecurityAuditEventType.ACCESS_DENIED,
            actor=str(user.get("user_id", "unknown")),
            action=action,
            resource=str(resource.get("resource_id", "")),
            outcome="denied",
            details={"reason": "mfa_required_for_admin"},
        )
        return {
            "ok": False,
            "allowed": False,
            "reason": "mfa_required_for_admin",
            "pipeline_stages": len(pipeline),
        }

    decision = evaluate_access(user, resource, action, attributes, db=db)
    if not decision.allowed:
        metrics.record_access_denied()
        record_security_event(
            event_type=SecurityAuditEventType.ACCESS_DENIED,
            actor=str(user.get("user_id", "unknown")),
            action=action,
            resource=str(resource.get("resource_id", "")),
            outcome="denied",
            details={"reason": decision.reason},
        )

    return {
        "ok": True,
        "allowed": decision.allowed,
        "decision": decision.to_dict(),
        "pipeline_stages": len(pipeline),
        "pipeline": [s["name"] for s in pipeline],
    }


def record_security_event(
    *,
    event_type: SecurityAuditEventType | str,
    actor: str,
    action: str,
    resource: str = "",
    outcome: str = "success",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record append-only security audit event + update metrics + platform event bus."""
    metrics = get_security_metrics()
    log = get_security_audit_log()

    if isinstance(event_type, str):
        event_type = SecurityAuditEventType(event_type)

    entry = log.append(
        event_type,
        actor=actor,
        action=action,
        resource=resource,
        outcome=outcome,
        details=details,
    )

    if event_type == SecurityAuditEventType.LOGIN and outcome != "success":
        metrics.record_failed_auth()
    elif event_type == SecurityAuditEventType.ROLE_CHANGE:
        metrics.record_role_change()
    elif event_type == SecurityAuditEventType.EXPORT:
        metrics.record_export()
    elif event_type == SecurityAuditEventType.ADMIN_ACTION:
        metrics.record_admin_action()
    elif event_type == SecurityAuditEventType.AI_INTERACTION:
        metrics.record_ai_interaction()
    elif event_type == SecurityAuditEventType.INTEGRITY_VIOLATION:
        metrics.record_integrity_violation()
    elif event_type == SecurityAuditEventType.ACCESS_DENIED:
        metrics.record_access_denied()
    elif event_type == SecurityAuditEventType.API_ACCESS and outcome == "anomaly":
        metrics.record_api_anomaly(action)

    try:
        bus = get_platform_event_bus()
        bus.publish(
            PlatformEvent(
                event_type=EventType.AI_COMPLETED,
                source="esa.security",
                actor=actor,
                payload={
                    "security_event_type": event_type.value,
                    "action": action,
                    "resource": resource,
                    "outcome": outcome,
                    **(details or {}),
                },
            )
        )
    except Exception:
        pass

    return {"ok": True, "entry": entry.to_dict()}


def run_security_scan() -> dict[str, Any]:
    """Stub integrity scan for Celery beat — evidence + constraints check."""
    from flowsint_crypto_compliance.platform.v2.esa.evidence_security import verify_evidence_security
    from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository

    metrics = get_security_metrics()
    metrics.record_security_scan()

    results: list[dict[str, Any]] = []
    violations = 0
    for record in get_eccf_repository().list_all():
        check = verify_evidence_security(record.evidence_id)
        if not check.get("integrity_ok"):
            violations += 1
            metrics.record_integrity_violation()
            record_security_event(
                event_type=SecurityAuditEventType.INTEGRITY_VIOLATION,
                actor="esa.scan",
                action="integrity_check",
                resource=record.evidence_id,
                outcome="violation",
            )
        results.append(check)

    return {
        "ok": True,
        "scanned": len(results),
        "violations": violations,
        "results": results,
    }
