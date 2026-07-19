"""RFC-18 Ch.7 — operator-facing event catalog over existing ComplianceEventBus / SSE."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent, SCHEMA_VERSION


class OperatorEventType(str, Enum):
    """Stable webhook-friendly names for bank-client integrations."""

    INVESTIGATION_CREATED = "InvestigationCreated"
    ENTITY_MERGED = "EntityMerged"
    EVIDENCE_ADDED = "EvidenceAdded"
    GRAPH_UPDATED = "GraphUpdated"
    RISK_RECALCULATED = "RiskRecalculated"
    ATTRIBUTION_CONFIRMED = "AttributionConfirmed"
    ATTRIBUTION_REJECTED = "AttributionRejected"
    REPORT_GENERATED = "ReportGenerated"


OPERATOR_EVENT_SCHEMA_VERSION = "1.0.0"

_OPERATOR_TO_PLATFORM: dict[OperatorEventType, EventType] = {
    OperatorEventType.INVESTIGATION_CREATED: EventType.CASE_OPENED,
    OperatorEventType.ENTITY_MERGED: EventType.ENTITY_MERGED,
    OperatorEventType.EVIDENCE_ADDED: EventType.EVIDENCE_CREATED,
    OperatorEventType.GRAPH_UPDATED: EventType.GRAPH_EXPANDED,
    OperatorEventType.RISK_RECALCULATED: EventType.RISK_UPDATED,
    OperatorEventType.ATTRIBUTION_CONFIRMED: EventType.ATTRIBUTION_APPLIED,
    OperatorEventType.ATTRIBUTION_REJECTED: EventType.ATTRIBUTION_APPLIED,
    OperatorEventType.REPORT_GENERATED: EventType.REPORT_GENERATED,
}


def operator_event_catalog() -> dict[str, Any]:
    return {
        "schema_version": OPERATOR_EVENT_SCHEMA_VERSION,
        "platform_schema_version": SCHEMA_VERSION,
        "events": [
            {
                "type": t.value,
                "platform_event": _OPERATOR_TO_PLATFORM[t].value,
                "versioned": True,
            }
            for t in OperatorEventType
        ],
    }


def publish_operator_event(
    event_type: OperatorEventType,
    *,
    payload: dict[str, Any] | None = None,
    source: str = "flowsint-api",
    actor: str = "system",
    investigation_id: UUID | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Publish versioned operator event via PlatformEventBus (SSE + legacy bus)."""
    body = dict(payload or {})
    body["operator_event_type"] = event_type.value
    body["operator_schema_version"] = OPERATOR_EVENT_SCHEMA_VERSION
    platform_type = _OPERATOR_TO_PLATFORM[event_type]
    event = PlatformEvent(
        event_type=platform_type,
        schema_version=SCHEMA_VERSION,
        source=source,
        actor=actor,
        investigation_id=investigation_id,
        correlation_id=correlation_id,
        payload=body,
    )
    result = get_platform_event_bus().publish(event)
    try:
        from flowsint_crypto_compliance.platform.v2.aspp.orchestrator import dispatch_webhook

        dispatch_webhook(
            event_type=event_type.value,
            payload={
                "operator_event_type": event_type.value,
                "platform_event": platform_type.value,
                "operator_schema_version": OPERATOR_EVENT_SCHEMA_VERSION,
                **body,
            },
        )
    except Exception:
        pass
    return result
