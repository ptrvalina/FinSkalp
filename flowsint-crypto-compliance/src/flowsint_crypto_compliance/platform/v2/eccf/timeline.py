"""RFC-0017 Ch.11 — evidence timeline events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass
class TimelineEvent:
    """Single timeline event for an evidence record."""

    evidence_id: str
    event_type: str
    label: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = "eccf.system"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "event_type": self.event_type,
            "label": self.label,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "metadata": self.metadata,
        }


class EvidenceTimeline:
    """Per-evidence chronological event store."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: dict[str, list[TimelineEvent]] = {}

    def add_event(
        self,
        evidence_id: str,
        event_type: str,
        label: str,
        *,
        actor: str = "eccf.system",
        metadata: dict[str, Any] | None = None,
    ) -> TimelineEvent:
        event = TimelineEvent(
            evidence_id=evidence_id,
            event_type=event_type,
            label=label,
            actor=actor,
            metadata=metadata or {},
        )
        with self._lock:
            self._events.setdefault(evidence_id, []).append(event)
        return event

    def get_timeline(self, evidence_id: str) -> list[TimelineEvent]:
        with self._lock:
            events = self._events.get(evidence_id, [])
            return sorted(events, key=lambda e: e.timestamp)


_timeline: EvidenceTimeline | None = None


def get_evidence_timeline() -> EvidenceTimeline:
    global _timeline
    if _timeline is None:
        _timeline = EvidenceTimeline()
    return _timeline


def reset_evidence_timeline() -> None:
    global _timeline
    _timeline = None
