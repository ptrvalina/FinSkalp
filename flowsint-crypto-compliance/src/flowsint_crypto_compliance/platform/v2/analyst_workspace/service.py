"""RFC-0010 Analyst Workspace service — aggregated workspace state."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.analyst_workspace.collaboration import (
    get_collaboration_activity,
    get_comments,
)
from flowsint_crypto_compliance.platform.v2.analyst_workspace.manifest import (
    NOTIFICATION_TYPES,
    WorkspaceTab,
)
from flowsint_crypto_compliance.platform.v2.analyst_workspace.personalization import get_personalization
from flowsint_crypto_compliance.platform.v2.analyst_workspace.timing import with_latency_ms
from flowsint_crypto_compliance.platform.v2.gateway import (
    get_intelligence_manifest,
    get_investigation_workspace,
    list_case_evidence,
)
from flowsint_crypto_compliance.platform.v2.investigation_platform import get_investigation_platform_service

_EVENT_NOTIFICATION_MAP: dict[str, str] = {
    "CaseOpened": "workflow_changed",
    "EvidenceRegistered": "evidence_registered",
    "OsintCollectComplete": "osint_complete",
    "RiskAlert": "risk_alert",
    "collaboration_comment": "collaboration_mention",
    "comment": "collaboration_mention",
}

_NOTIFICATION_LABELS = {n["id"]: n["label_ru"] for n in NOTIFICATION_TYPES}


class AnalystWorkspaceService:
    """Unified analyst workspace state aggregator (RFC-0010)."""

    def _build_notifications(
        self,
        *,
        case_ref: str,
        timeline_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        notifications: list[dict[str, Any]] = []
        for event in timeline_events[:15]:
            event_type = str(event.get("event_type") or "")
            notif_type = _EVENT_NOTIFICATION_MAP.get(event_type, "workflow_changed")
            notifications.append(
                {
                    "id": event.get("id"),
                    "type": notif_type,
                    "label_ru": _NOTIFICATION_LABELS.get(notif_type, event_type),
                    "occurred_at": event.get("occurred_at"),
                    "actor": event.get("actor"),
                    "read": False,
                    "payload": event.get("payload") or {},
                }
            )
        collab = get_collaboration_activity(case_ref, limit=10)
        for comment in collab.get("comments") or []:
            notifications.append(
                {
                    "id": comment.get("id"),
                    "type": "collaboration_mention",
                    "label_ru": _NOTIFICATION_LABELS.get("collaboration_mention", "Комментарий"),
                    "occurred_at": comment.get("created_at"),
                    "actor": comment.get("author"),
                    "read": False,
                    "payload": {"text": comment.get("text")},
                }
            )
        notifications.sort(key=lambda n: n.get("occurred_at") or "", reverse=True)
        return notifications[:25]

    def get_workspace_state(
        self,
        *,
        case_ref: str | None = None,
        investigation_id: uuid.UUID | str | None = None,
        case: Any | None = None,
        user_id: str = "default",
    ) -> dict[str, Any]:
        resolved_ref = case_ref
        resolved_inv_id = investigation_id
        compliance_case_id = None

        if case is not None:
            resolved_ref = resolved_ref or getattr(case, "case_ref", None)
            compliance_case_id = getattr(case, "id", None)
            if resolved_inv_id is None:
                resolved_inv_id = getattr(case, "investigation_id", None)

        if not resolved_ref:
            return {
                "ok": False,
                "message_ru": "Укажите case_ref или investigation_id со связанным кейсом",
                "case_ref": None,
                "investigation_id": str(resolved_inv_id) if resolved_inv_id else None,
                "active_tab": WorkspaceTab.SUMMARY.value,
                "tabs": [t.value for t in WorkspaceTab],
            }

        inv_uuid = None
        if resolved_inv_id is not None:
            inv_uuid = (
                resolved_inv_id
                if isinstance(resolved_inv_id, uuid.UUID)
                else uuid.UUID(str(resolved_inv_id))
            )

        workspace = get_investigation_workspace(resolved_ref, case=case)
        evidence = list_case_evidence(case_ref=resolved_ref, case_id=compliance_case_id)
        timeline = get_investigation_platform_service().get_timeline(
            case_ref=resolved_ref,
            investigation_id=inv_uuid,
        )
        intel = get_intelligence_manifest()

        intel_snippet = {
            "engines_count": len(intel.get("engines") or []),
            "osint_categories": intel.get("osint_categories") or [],
            "supported_chains": intel.get("supported_chains") or [],
            "rule_ru": intel.get("rule_ru"),
        }

        timeline_events = (timeline.get("events") or [])[:30]
        collab = get_collaboration_activity(resolved_ref, limit=30)
        comments = collab.get("comments") or get_comments(resolved_ref)
        prefs = get_personalization(user_id)
        notifications = self._build_notifications(
            case_ref=resolved_ref,
            timeline_events=timeline_events,
        )

        return {
            "ok": True,
            "rfc": "RFC-0010",
            "case_ref": resolved_ref,
            "investigation_id": str(inv_uuid) if inv_uuid else None,
            "compliance_case_id": str(compliance_case_id) if compliance_case_id else None,
            "active_tab": prefs.get("preferences", {}).get("active_tab", WorkspaceTab.SUMMARY.value),
            "tabs": [t.value for t in WorkspaceTab],
            "workspace": workspace,
            "evidence": {
                "count": evidence.get("count", 0),
                "items": (evidence.get("items") or [])[:20],
                "delete_forbidden": evidence.get("delete_forbidden", True),
            },
            "timeline": {
                "count": timeline.get("count", 0),
                "events": timeline_events,
            },
            "intelligence": intel_snippet,
            "collaboration": {
                "comments": comments,
                "activity": collab.get("activity") or [],
                "comments_count": len(comments),
            },
            "notifications": notifications,
            "personalization": prefs.get("preferences") or {},
            "sync": {
                "fields": [
                    "investigation_id",
                    "case_ref",
                    "active_tab",
                    "selected_entity_id",
                    "filters",
                    "date_range",
                    "graph_zoom",
                    "panel_layout",
                ],
                "investigation_id": str(inv_uuid) if inv_uuid else None,
                "case_ref": resolved_ref,
                "selected_entity_id": str(workspace.get("entity_id")) if workspace.get("entity_id") else None,
            },
            "counts": {
                "evidence": evidence.get("count", 0),
                "timeline": timeline.get("count", 0),
                "panels": len(workspace.get("panels") or []),
                "notifications_unread": sum(1 for n in notifications if not n.get("read")),
            },
        }


_service: AnalystWorkspaceService | None = None


def get_analyst_workspace_service() -> AnalystWorkspaceService:
    global _service
    if _service is None:
        _service = AnalystWorkspaceService()
    return _service


def get_workspace_state_timed(**kwargs: Any) -> dict[str, Any]:
    return with_latency_ms(get_analyst_workspace_service().get_workspace_state, **kwargs)
