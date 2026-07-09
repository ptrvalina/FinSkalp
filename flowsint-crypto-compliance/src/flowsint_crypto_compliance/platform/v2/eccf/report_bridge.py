"""RFC-0017 Ch.13 — report usage bridge."""

from __future__ import annotations

from threading import Lock
from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import AuditAction, get_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository
from flowsint_crypto_compliance.platform.v2.eccf.timeline import get_evidence_timeline
from flowsint_crypto_compliance.platform.v2.eccf.types import EvidenceLifecycle


class ReportBridge:
    """Track evidence usage in investigation reports."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._usage: dict[str, list[dict[str, Any]]] = {}

    def record_report_usage(
        self,
        evidence_id: str,
        report_id: str,
        analyst: str,
    ) -> dict[str, Any]:
        repo = get_eccf_repository()
        record = repo.get(evidence_id)
        if record is None:
            return {"ok": False, "error": "evidence_not_found"}

        entry = {
            "report_id": report_id,
            "analyst": analyst,
            "evidence_id": evidence_id,
        }
        with self._lock:
            self._usage.setdefault(evidence_id, []).append(entry)

        repo.update_metadata_only(evidence_id, lifecycle=EvidenceLifecycle.IN_REPORT)
        get_audit_trail().append(
            evidence_id,
            AuditAction.USED_IN_REPORT,
            actor=analyst,
            details={"report_id": report_id},
        )
        get_evidence_timeline().add_event(
            evidence_id,
            "report_usage",
            f"Used in report {report_id}",
            actor=analyst,
            metadata={"report_id": report_id},
        )
        return {"ok": True, **entry}

    def get_usage(self, evidence_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._usage.get(evidence_id, []))


_bridge: ReportBridge | None = None


def get_report_bridge() -> ReportBridge:
    global _bridge
    if _bridge is None:
        _bridge = ReportBridge()
    return _bridge


def record_report_usage(evidence_id: str, report_id: str, analyst: str) -> dict[str, Any]:
    return get_report_bridge().record_report_usage(evidence_id, report_id, analyst)


def reset_report_bridge() -> None:
    global _bridge
    _bridge = None
