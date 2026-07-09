"""RFC-0010 Ch.16 — In-memory collaboration (comments + activity feed)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

_comments: dict[str, list[dict[str, Any]]] = {}
_activity: dict[str, list[dict[str, Any]]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_comment(
    *,
    case_ref: str,
    text: str,
    author: str = "analyst",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    text = (text or "").strip()
    if not case_ref:
        return {"ok": False, "message_ru": "Укажите case_ref"}
    if not text:
        return {"ok": False, "message_ru": "Текст комментария не может быть пустым"}

    comment_id = str(uuid.uuid4())
    created_at = _now_iso()
    comment = {
        "id": comment_id,
        "case_ref": case_ref,
        "text": text,
        "author": author,
        "tenant_id": tenant_id,
        "created_at": created_at,
        "type": "comment",
    }
    _comments.setdefault(case_ref, []).append(comment)

    activity = {
        "id": str(uuid.uuid4()),
        "case_ref": case_ref,
        "event_type": "collaboration_comment",
        "occurred_at": created_at,
        "actor": author,
        "payload": {"comment_id": comment_id, "text": text[:500]},
    }
    _activity.setdefault(case_ref, []).append(activity)

    return {"ok": True, "comment": comment, "activity_id": activity["id"]}


def get_comments(case_ref: str) -> list[dict[str, Any]]:
    return list(_comments.get(case_ref, []))


def get_collaboration_activity(case_ref: str, *, limit: int = 50) -> dict[str, Any]:
    comments = get_comments(case_ref)
    activity = list(_activity.get(case_ref, []))
    merged = list(activity)
    seen_ids = {a.get("id") for a in merged}
    for c in comments:
        if c["id"] in seen_ids:
            continue
        merged.append(
            {
                "id": c["id"],
                "event_type": "comment",
                "occurred_at": c["created_at"],
                "actor": c["author"],
                "payload": {"text": c["text"]},
            }
        )
    merged.sort(key=lambda e: e.get("occurred_at", ""), reverse=True)
    return {
        "ok": True,
        "case_ref": case_ref,
        "comments": comments,
        "activity": merged[:limit],
        "count": len(merged),
    }


def reset_collaboration_store() -> None:
    _comments.clear()
    _activity.clear()
