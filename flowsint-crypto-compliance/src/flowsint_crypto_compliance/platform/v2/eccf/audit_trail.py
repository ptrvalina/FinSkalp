"""RFC-0017 Ch.10 — append-only audit trail."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any

class AuditAction(str, Enum):
    """RFC-0017 Ch.10 — audit entry types."""

    CREATED = "Created"
    HASH_CALCULATED = "HashCalculated"
    VALIDATED = "Validated"
    LINKED = "Linked"
    USED_IN_REPORT = "UsedInReport"
    ARCHIVED = "Archived"
    VERSION_CREATED = "VersionCreated"


@dataclass
class AuditEntry:
    """Immutable audit log entry."""

    evidence_id: str
    action: AuditAction
    actor: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)
    entry_id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "evidence_id": self.evidence_id,
            "action": self.action.value,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class AuditTrail:
    """Append-only audit trail — no delete or modify."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._entries: list[AuditEntry] = []
        self._by_evidence: dict[str, list[int]] = {}
        self._next_id = 1

    def append(
        self,
        evidence_id: str,
        action: AuditAction,
        *,
        actor: str = "eccf.system",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        with self._lock:
            entry = AuditEntry(
                entry_id=self._next_id,
                evidence_id=evidence_id,
                action=action,
                actor=actor,
                details=details or {},
            )
            self._next_id += 1
            self._entries.append(entry)
            self._by_evidence.setdefault(evidence_id, []).append(entry.entry_id)
            return entry

    def get_trail(self, evidence_id: str) -> list[AuditEntry]:
        with self._lock:
            ids = self._by_evidence.get(evidence_id, [])
            return [e for e in self._entries if e.entry_id in ids]

    def all_entries(self) -> list[AuditEntry]:
        with self._lock:
            return list(self._entries)


_trail: AuditTrail | Any | None = None


def get_audit_trail() -> AuditTrail:
    global _trail
    if _trail is None:
        from flowsint_crypto_compliance.feature_flags import eccf_postgres_persistence_enabled

        if eccf_postgres_persistence_enabled():
            try:
                from flowsint_crypto_compliance.platform.v2.eccf.postgres_store import (
                    PostgresAuditTrail,
                )

                _trail = PostgresAuditTrail()
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "ECCF Postgres audit unavailable — falling back to in-memory"
                )
                _trail = AuditTrail()
        else:
            _trail = AuditTrail()
    return _trail


def reset_audit_trail() -> None:
    global _trail
    _trail = None
