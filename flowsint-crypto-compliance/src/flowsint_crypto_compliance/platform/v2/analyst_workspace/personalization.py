"""RFC-0010 Ch.18 — Workspace personalization (server-side preferences)."""

from __future__ import annotations

from typing import Any

DEFAULT_PREFS: dict[str, Any] = {
    "active_tab": "summary",
    "density": "comfortable",
    "theme": "system",
    "panel_layout": {},
    "pinned_panels": [],
    "locale": "ru",
}

_ALLOWED_KEYS = frozenset(DEFAULT_PREFS.keys())

_store: dict[str, dict[str, Any]] = {}


def get_personalization(user_id: str = "default") -> dict[str, Any]:
    prefs = {**DEFAULT_PREFS, **(_store.get(user_id) or {})}
    return {"ok": True, "user_id": user_id, "preferences": prefs}


def save_personalization(user_id: str, preferences: dict[str, Any]) -> dict[str, Any]:
    current = {**DEFAULT_PREFS, **(_store.get(user_id) or {})}
    for key, value in preferences.items():
        if key in _ALLOWED_KEYS:
            current[key] = value
    _store[user_id] = current
    return {"ok": True, "user_id": user_id, "preferences": current}


def reset_personalization_store() -> None:
    _store.clear()
