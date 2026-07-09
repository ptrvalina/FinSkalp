"""Case management workflow — 115-ФЗ investigation lifecycle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

WORKFLOW_STATUSES = (
    "new",
    "triage",
    "investigating",
    "pending_filing",
    "internal_review",
    "filed",
    "archived",
)

VALID_TRANSITIONS: dict[str, set[str]] = {
    "new": {"triage", "archived"},
    "triage": {"investigating", "archived", "new"},
    "investigating": {"pending_filing", "internal_review", "triage", "archived"},
    "pending_filing": {"internal_review", "filed", "investigating"},
    "internal_review": {"filed", "pending_filing", "investigating"},
    "filed": {"archived"},
    "archived": set(),
}

DEFAULT_SLA_HOURS = {
    "new": 24,
    "triage": 48,
    "investigating": 72,
    "pending_filing": 24,
    "internal_review": 48,
    "filed": 168,
    "archived": 0,
}

# RFC-0005 Ch.2 lifecycle (maps to workflow_status codes)
RFC_0005_LIFECYCLE: dict[str, dict[str, str]] = {
    "new": {"code": "new", "label_ru": "Новое дело"},
    "triage": {"code": "triage", "label_ru": "Предварительный анализ"},
    "investigating": {"code": "investigating", "label_ru": "Активное расследование"},
    "pending_filing": {"code": "pending_filing", "label_ru": "Дополнительная проверка"},
    "internal_review": {"code": "internal_review", "label_ru": "Внутреннее согласование"},
    "filed": {"code": "filed", "label_ru": "Завершено"},
    "archived": {"code": "archived", "label_ru": "Архив"},
}


def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


def sla_due_at(workflow_status: str, *, from_time: datetime | None = None) -> datetime | None:
    hours = DEFAULT_SLA_HOURS.get(workflow_status, 72)
    if hours <= 0:
        return None
    base = from_time or datetime.now(timezone.utc)
    return base + timedelta(hours=hours)


def is_sla_breached(due_at: datetime | None, workflow_status: str) -> bool:
    if workflow_status in ("filed", "archived") or due_at is None:
        return False
    now = datetime.now(timezone.utc)
    due = due_at if due_at.tzinfo else due_at.replace(tzinfo=timezone.utc)
    return now > due


def legacy_status_to_workflow(status: str) -> str:
    mapping = {
        "draft": "new",
        "ingesting": "triage",
        "fused": "investigating",
        "reported": "filed",
    }
    return mapping.get(status, status if status in WORKFLOW_STATUSES else "new")


def workflow_payload(case: Any) -> dict[str, Any]:
    ws = getattr(case, "workflow_status", None) or legacy_status_to_workflow(case.status)
    due = getattr(case, "due_at", None)
    breached = getattr(case, "sla_breached", False) or is_sla_breached(due, ws)
    return {
        "workflow_status": ws,
        "assignee_id": str(case.assignee_id) if getattr(case, "assignee_id", None) else None,
        "priority": getattr(case, "priority", "normal") or "normal",
        "due_at": due.isoformat() if due else None,
        "sla_breached": breached,
        "sla_hours": getattr(case, "sla_hours", None),
    }
