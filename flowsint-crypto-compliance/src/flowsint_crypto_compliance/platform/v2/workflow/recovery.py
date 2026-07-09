"""RFC-0011 Ch.16 — recovery workflow state."""

from __future__ import annotations

from typing import Any

_store: dict[str, dict[str, Any]] = {}


def save_recovery_state(user_id: str, state: dict[str, Any]) -> dict[str, Any]:
    _store[user_id] = {**state, "ok": True}
    return {"ok": True, "user_id": user_id, "state": _store[user_id]}


def get_recovery_state(user_id: str) -> dict[str, Any]:
    state = _store.get(user_id)
    if not state:
        return {"ok": True, "user_id": user_id, "state": None}
    return {"ok": True, "user_id": user_id, "state": state}


def reset_recovery_store() -> None:
    _store.clear()
