"""RFC-0017 Ch.14 — evidence archive and search."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import AuditAction, get_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.constraints import assert_not_forbidden
from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository
from flowsint_crypto_compliance.platform.v2.eccf.timeline import get_evidence_timeline
from flowsint_crypto_compliance.platform.v2.eccf.types import EvidenceLifecycle


class EvidenceArchive:
    """Archive store — evidence content remains immutable."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._archived: dict[str, dict[str, Any]] = {}

    def archive_evidence(
        self,
        evidence_id: str,
        *,
        actor: str = "eccf.archive",
        reason: str | None = None,
    ) -> dict[str, Any]:
        assert_not_forbidden("delete_evidence")
        repo = get_eccf_repository()
        record = repo.get(evidence_id)
        if record is None:
            return {"ok": False, "error": "evidence_not_found"}

        archived_at = datetime.now(timezone.utc)
        archive_meta = {
            "evidence_id": evidence_id,
            "archived_at": archived_at.isoformat(),
            "archived_by": actor,
            "reason": reason or "case_closed",
            "content_hash": record.content_hash,
            "version": record.version,
        }
        with self._lock:
            self._archived[evidence_id] = archive_meta

        repo.update_metadata_only(
            evidence_id,
            lifecycle=EvidenceLifecycle.ARCHIVED,
            archived=True,
        )
        get_audit_trail().append(
            evidence_id,
            AuditAction.ARCHIVED,
            actor=actor,
            details=archive_meta,
        )
        get_evidence_timeline().add_event(
            evidence_id,
            "archived",
            "Evidence archived",
            actor=actor,
            metadata=archive_meta,
        )
        return {"ok": True, **archive_meta}

    def search_archive(
        self,
        *,
        case_ref: str | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        repo = get_eccf_repository()
        results: list[dict[str, Any]] = []
        for rec in repo.list_all():
            if not rec.archived:
                continue
            if case_ref and rec.case_ref != case_ref:
                continue
            if category and rec.category.value != category:
                continue
            if query:
                q = query.lower()
                if q not in rec.entity_value.lower() and q not in rec.evidence_id.lower():
                    continue
            meta = self._archived.get(rec.evidence_id, {})
            results.append({**rec.to_dict(), "archive": meta})
        return results

    def is_archived(self, evidence_id: str) -> bool:
        with self._lock:
            return evidence_id in self._archived


_archive: EvidenceArchive | None = None


def get_evidence_archive() -> EvidenceArchive:
    global _archive
    if _archive is None:
        _archive = EvidenceArchive()
    return _archive


def archive_evidence(evidence_id: str, *, actor: str = "eccf.archive", reason: str | None = None) -> dict[str, Any]:
    return get_evidence_archive().archive_evidence(evidence_id, actor=actor, reason=reason)


def search_archive(**kwargs: Any) -> list[dict[str, Any]]:
    return get_evidence_archive().search_archive(**kwargs)


def reset_evidence_archive() -> None:
    global _archive
    _archive = None
