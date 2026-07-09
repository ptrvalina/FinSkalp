"""RFC-0015 Ch.11 — risk bridge emitting compliance events (no direct risk score mutation)."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent


def emit_risk_compliance_events(
    records: list[dict[str, Any]],
    *,
    tenant_id: uuid.UUID,
    case_ref: str | None = None,
    connector_id: str,
    compliance_checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Emit compliance events for Risk Engine consumption.
    Does NOT mutate risk scores directly — events only.
    """
    bus = get_platform_event_bus()
    emitted = 0
    event_types: list[str] = []

    for rec in records:
        et = str(rec.get("entity_type") or "")
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        if et == "SanctionEntry" or payload.get("sanctioned"):
            event_type = EventType.SANCTION_HIT_DETECTED
        elif et == "License":
            event_type = EventType.REGISTRY_RECORD_IMPORTED
        else:
            event_type = EventType.REGISTRY_RECORD_IMPORTED

        bus.publish(
            PlatformEvent(
                event_type=event_type,
                source=f"crif.risk_bridge.{connector_id}",
                tenant_id=tenant_id,
                correlation_id=case_ref,
                payload={
                    "case_ref": case_ref,
                    "connector_id": connector_id,
                    "entity_type": et,
                    "entity_value": rec.get("entity_value"),
                    "compliance_signal": True,
                    "risk_mutation": False,
                    "stage": "risk_engine",
                    **(payload or {}),
                },
            )
        )
        emitted += 1
        event_types.append(event_type.value)

    for check in compliance_checks or []:
        if not check.get("passed", True):
            bus.publish(
                PlatformEvent(
                    event_type=EventType.PATTERN_DETECTED,
                    source=f"crif.risk_bridge.{connector_id}",
                    tenant_id=tenant_id,
                    correlation_id=case_ref,
                    payload={
                        "case_ref": case_ref,
                        "check_id": check.get("check_id"),
                        "check_type": check.get("check_type"),
                        "severity": check.get("severity", "medium"),
                        "risk_mutation": False,
                        "compliance_event": True,
                        "message_ru": check.get("message_ru"),
                    },
                )
            )
            emitted += 1
            event_types.append(EventType.PATTERN_DETECTED.value)

    return {"events_emitted": emitted, "event_types": event_types, "ok": True, "risk_mutation": False}
