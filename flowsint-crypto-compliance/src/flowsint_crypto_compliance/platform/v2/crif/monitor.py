"""RFC-0015 Ch.13 — periodic change detection + event publish stubs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MonitorSnapshot:
    connector_id: str
    organization_key: str
    record_hash: str
    captured_at: float = field(default_factory=time.time)


class RegistryMonitor:
    """Detect registry changes between sync cycles."""

    def __init__(self) -> None:
        self._snapshots: dict[str, MonitorSnapshot] = {}
        self._changes_detected: int = 0

    def snapshot_key(self, connector_id: str, organization_key: str) -> str:
        return f"{connector_id}:{organization_key}"

    def record_snapshot(
        self,
        connector_id: str,
        organization_key: str,
        record_hash: str,
    ) -> dict[str, Any]:
        key = self.snapshot_key(connector_id, organization_key)
        prev = self._snapshots.get(key)
        changed = prev is not None and prev.record_hash != record_hash
        if changed:
            self._changes_detected += 1
        self._snapshots[key] = MonitorSnapshot(
            connector_id=connector_id,
            organization_key=organization_key,
            record_hash=record_hash,
        )
        return {
            "changed": changed,
            "previous_hash": prev.record_hash if prev else None,
            "current_hash": record_hash,
            "event_published": changed,
        }

    def publish_change_event_stub(
        self,
        *,
        connector_id: str,
        organization_key: str,
        change: dict[str, Any],
    ) -> dict[str, Any]:
        """Stub — actual publish delegated to risk_bridge / event bus in orchestrator."""
        return {
            "stub": True,
            "connector_id": connector_id,
            "organization_key": organization_key,
            "change": change,
            "published": change.get("changed", False),
        }

    def status(self) -> dict[str, Any]:
        return {
            "snapshots": len(self._snapshots),
            "changes_detected": self._changes_detected,
        }


_monitor: RegistryMonitor | None = None


def get_registry_monitor() -> RegistryMonitor:
    global _monitor
    if _monitor is None:
        _monitor = RegistryMonitor()
    return _monitor
