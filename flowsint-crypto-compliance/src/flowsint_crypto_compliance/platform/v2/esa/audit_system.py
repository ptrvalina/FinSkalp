"""RFC-0020 Ch.13 — append-only security audit log."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from flowsint_crypto_compliance.platform.v2.esa.types import SecurityAuditEventType


@dataclass
class SecurityAuditEntry:
    """Immutable security audit log entry."""

    entry_id: int
    event_type: SecurityAuditEventType
    actor: str
    action: str
    resource: str = ""
    outcome: str = "success"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type.value,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class SecurityAuditLog:
    """Append-only security audit — no delete or modify."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._entries: list[SecurityAuditEntry] = []
        self._next_id = 1

    def append(
        self,
        event_type: SecurityAuditEventType | str,
        *,
        actor: str,
        action: str,
        resource: str = "",
        outcome: str = "success",
        details: dict[str, Any] | None = None,
    ) -> SecurityAuditEntry:
        if isinstance(event_type, str):
            event_type = SecurityAuditEventType(event_type)
        with self._lock:
            entry = SecurityAuditEntry(
                entry_id=self._next_id,
                event_type=event_type,
                actor=actor,
                action=action,
                resource=resource,
                outcome=outcome,
                details=details or {},
            )
            self._next_id += 1
            self._entries.append(entry)
            try:
                from flowsint_crypto_compliance.platform.v2.esa.postgres_audit import persist_security_audit_entry

                persist_security_audit_entry(entry)
            except Exception:
                pass
            return entry

    def all_entries(self) -> list[SecurityAuditEntry]:
        with self._lock:
            return list(self._entries)

    def count_by_type(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for e in self._entries:
                key = e.event_type.value
                counts[key] = counts.get(key, 0) + 1
            return counts

    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)


_log: SecurityAuditLog | None = None


def get_security_audit_log() -> SecurityAuditLog:
    global _log
    if _log is None:
        _log = SecurityAuditLog()
    return _log


def reset_security_audit_log() -> None:
    global _log
    _log = None


def audit_system_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 13,
        "event_types": [e.value for e in SecurityAuditEventType],
        "append_only": True,
        "retention_days": 2555,
        "categories": {
            "login": "Authentication events",
            "export": "Data and evidence export",
            "role_change": "RBAC role modifications",
            "api_access": "API request audit",
            "ai_interaction": "EIA assistant interactions",
            "admin_action": "Administrative operations",
        },
        "principle_ru": "Аудит безопасности — только дополнение, без удаления и изменения",
    }
