"""RFC-0015 Ch.8 — in-memory change history timeline per organization key."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChangeEvent:
    organization_key: str
    event_type: str
    field: str
    old_value: Any
    new_value: Any
    source: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_key": self.organization_key,
            "event_type": self.event_type,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class ChangeHistoryStore:
    """In-memory timeline per organization key."""

    def __init__(self) -> None:
        self._timelines: dict[str, list[ChangeEvent]] = {}

    def record_change(
        self,
        organization_key: str,
        *,
        event_type: str,
        field: str,
        old_value: Any,
        new_value: Any,
        source: str,
    ) -> ChangeEvent:
        event = ChangeEvent(
            organization_key=organization_key,
            event_type=event_type,
            field=field,
            old_value=old_value,
            new_value=new_value,
            source=source,
        )
        self._timelines.setdefault(organization_key, []).append(event)
        return event

    def record_from_records(
        self,
        organization_key: str,
        records: list[dict[str, Any]],
        *,
        source: str,
    ) -> list[ChangeEvent]:
        events: list[ChangeEvent] = []
        for rec in records:
            payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
            inner = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
            merged = {**inner, **{k: v for k, v in payload.items() if k != "payload"}}
            for field_name in ("status", "registration_number", "jurisdiction"):
                val = merged.get(field_name)
                if val is not None:
                    events.append(
                        self.record_change(
                            organization_key,
                            event_type="registry_update",
                            field=field_name,
                            old_value=None,
                            new_value=val,
                            source=source,
                        )
                    )
        return events

    def get_timeline(self, organization_key: str) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._timelines.get(organization_key, [])]

    def clear(self) -> None:
        self._timelines.clear()


_store: ChangeHistoryStore | None = None


def get_change_history_store() -> ChangeHistoryStore:
    global _store
    if _store is None:
        _store = ChangeHistoryStore()
    return _store
