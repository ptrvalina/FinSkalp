"""RFC-0017 Ch.6/10 — Postgres-backed ECCF repository and hash-chained audit trail.

Enabled via ``FINSKALP_ECCF_POSTGRES_PERSISTENCE``. When the flag is off (default)
callers use the legacy in-memory implementations — no behaviour change.

Rollback: unset the env var. The in-memory store resumes immediately on the next
process start (or after ``reset_eccf_repository()`` / ``reset_audit_trail()``).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import Evidence, TrustLevel
from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import AuditAction, AuditEntry
from flowsint_crypto_compliance.platform.v2.eccf.constraints import assert_not_forbidden
from flowsint_crypto_compliance.platform.v2.eccf.hash_chain import (
    compute_entry_hash,
    genesis_hash,
    verify_chain,
)
from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFRecord, EvidenceCategory, EvidenceLifecycle
from flowsint_crypto_compliance.platform.v2.knowledge_store import get_knowledge_graph_store

logger = logging.getLogger(__name__)

_MUTABLE_METADATA = frozenset(
    {"lifecycle", "archived", "kg_evidence_id", "provenance", "updated_at"}
)
_IMMUTABLE_FIELDS = frozenset({"content_hash", "payload", "size_bytes", "mime_type"})


def _session():
    from flowsint_core.core.postgre_db import SessionLocal

    return SessionLocal()


def _row_to_record(row: Any) -> ECCFRecord:
    return ECCFRecord(
        evidence_id=row.evidence_id,
        tenant_id=row.tenant_id,
        category=EvidenceCategory(row.category),
        version=row.version,
        content_hash=row.content_hash,
        size_bytes=row.size_bytes,
        mime_type=row.mime_type,
        lifecycle=EvidenceLifecycle(row.lifecycle),
        source_type=row.source_type,
        entity_type=row.entity_type,
        entity_value=row.entity_value,
        case_ref=row.case_ref,
        kg_evidence_id=row.kg_evidence_id,
        payload=dict(row.payload or {}),
        provenance=dict(row.provenance or {}),
        created_at=row.created_at or datetime.now(timezone.utc),
        updated_at=row.updated_at or datetime.now(timezone.utc),
        prior_version_id=row.prior_version_id,
        immutable=bool(row.immutable),
        archived=bool(row.archived),
    )


def _record_to_row(record: ECCFRecord) -> Any:
    from flowsint_crypto_compliance.storage.db_models import EccfEvidenceRecord

    return EccfEvidenceRecord(
        evidence_id=record.evidence_id,
        tenant_id=record.tenant_id,
        category=record.category.value,
        version=record.version,
        content_hash=record.content_hash,
        size_bytes=record.size_bytes,
        mime_type=record.mime_type,
        lifecycle=record.lifecycle.value,
        source_type=record.source_type,
        entity_type=record.entity_type,
        entity_value=record.entity_value,
        case_ref=record.case_ref,
        kg_evidence_id=record.kg_evidence_id,
        payload=record.payload,
        provenance=record.provenance,
        prior_version_id=record.prior_version_id,
        immutable=record.immutable,
        archived=record.archived,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class PostgresECCFRepository:
    """Persistent ECCF store — same public surface as :class:`ECCFRepository`."""

    def get(self, evidence_id: str) -> ECCFRecord | None:
        from flowsint_crypto_compliance.storage.db_models import EccfEvidenceRecord

        db = _session()
        try:
            row = db.query(EccfEvidenceRecord).filter(EccfEvidenceRecord.evidence_id == evidence_id).first()
            return _row_to_record(row) if row else None
        finally:
            db.close()

    def find_by_hash(self, content_hash: str, tenant_id: str) -> ECCFRecord | None:
        from flowsint_crypto_compliance.storage.db_models import EccfEvidenceRecord

        db = _session()
        try:
            row = (
                db.query(EccfEvidenceRecord)
                .filter(
                    EccfEvidenceRecord.tenant_id == tenant_id,
                    EccfEvidenceRecord.content_hash == content_hash,
                )
                .first()
            )
            return _row_to_record(row) if row else None
        finally:
            db.close()

    def store(
        self,
        record: ECCFRecord,
        *,
        bridge_kg: bool = True,
    ) -> tuple[ECCFRecord, bool]:
        existing = self.find_by_hash(record.content_hash, record.tenant_id)
        if existing:
            return existing, True

        record.lifecycle = EvidenceLifecycle.REGISTERED
        record.immutable = True
        record.updated_at = datetime.now(timezone.utc)

        if bridge_kg:
            kg_id = self._bridge_to_kg(record)
            if kg_id:
                record.kg_evidence_id = kg_id

        from flowsint_crypto_compliance.storage.db_models import EccfEvidenceRecord

        db = _session()
        try:
            db.add(_record_to_row(record))
            db.commit()
            logger.info(
                "eccf.postgres.store evidence_id=%s tenant=%s hash=%s",
                record.evidence_id,
                record.tenant_id,
                record.content_hash[:16],
            )
        except Exception:
            db.rollback()
            logger.exception("eccf.postgres.store failed evidence_id=%s", record.evidence_id)
            raise
        finally:
            db.close()
        return record, False

    def _bridge_to_kg(self, record: ECCFRecord) -> str | None:
        try:
            store = get_knowledge_graph_store()
            evidence = Evidence(
                tenant_id=uuid.UUID(record.tenant_id),
                source_type=record.source_type,
                content_hash=record.content_hash,
                trust=TrustLevel(
                    source_reliability=0.7,
                    information_credibility=0.7,
                    sample_size=1,
                ),
                payload={
                    **record.payload,
                    "eccf_evidence_id": record.evidence_id,
                    "eccf_category": record.category.value,
                    "entity_type": record.entity_type,
                    "entity_value": record.entity_value,
                    "case_ref": record.case_ref,
                },
            )
            stored = store.store_evidence(evidence)
            return str(stored.id)
        except Exception:
            logger.debug("eccf.postgres.kg_bridge skipped", exc_info=True)
            return None

    def list_all(self) -> list[ECCFRecord]:
        from flowsint_crypto_compliance.storage.db_models import EccfEvidenceRecord

        db = _session()
        try:
            rows = db.query(EccfEvidenceRecord).all()
            return [_row_to_record(r) for r in rows]
        finally:
            db.close()

    def update_metadata_only(self, evidence_id: str, **fields: Any) -> ECCFRecord:
        if _IMMUTABLE_FIELDS & set(fields):
            assert_not_forbidden("modify_content")
        disallowed = set(fields) - _MUTABLE_METADATA - {"lifecycle"}
        if disallowed - {"lifecycle"}:
            # lifecycle handled separately; reject unknown keys touching content
            for key in disallowed:
                if key in _IMMUTABLE_FIELDS:
                    assert_not_forbidden("modify_content")

        from flowsint_crypto_compliance.storage.db_models import EccfEvidenceRecord

        db = _session()
        try:
            row = db.query(EccfEvidenceRecord).filter(EccfEvidenceRecord.evidence_id == evidence_id).first()
            if row is None:
                raise KeyError(evidence_id)
            if row.immutable and _IMMUTABLE_FIELDS & set(fields):
                raise ValueError("Cannot modify immutable evidence content")
            for key, val in fields.items():
                if key == "lifecycle":
                    row.lifecycle = val.value if isinstance(val, EvidenceLifecycle) else str(val)
                elif key in _MUTABLE_METADATA or key == "archived":
                    setattr(row, key, val)
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(row)
            logger.info("eccf.postgres.metadata_update evidence_id=%s fields=%s", evidence_id, list(fields))
            return _row_to_record(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


class PostgresAuditTrail:
    """Append-only Postgres audit trail with tamper-evident hash chain."""

    def append(
        self,
        evidence_id: str,
        action: AuditAction,
        *,
        actor: str = "eccf.system",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        from flowsint_crypto_compliance.storage.db_models import EccfAuditLogEntry

        details = details or {}
        ts = datetime.now(timezone.utc)
        db = _session()
        try:
            last = db.query(EccfAuditLogEntry).order_by(EccfAuditLogEntry.entry_id.desc()).first()
            prev_hash = last.entry_hash if last else genesis_hash()
            entry_hash = compute_entry_hash(
                evidence_id=evidence_id,
                action=action.value,
                actor=actor,
                timestamp=ts,
                details=details,
                prev_hash=prev_hash,
            )
            row = EccfAuditLogEntry(
                evidence_id=evidence_id,
                action=action.value,
                actor=actor,
                timestamp=ts,
                details=details,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info(
                "eccf.postgres.audit evidence_id=%s action=%s entry_id=%s",
                evidence_id,
                action.value,
                row.entry_id,
            )
            return AuditEntry(
                entry_id=row.entry_id,
                evidence_id=evidence_id,
                action=action,
                actor=actor,
                timestamp=ts,
                details=details,
            )
        except Exception:
            db.rollback()
            logger.exception("eccf.postgres.audit failed evidence_id=%s", evidence_id)
            raise
        finally:
            db.close()

    def get_trail(self, evidence_id: str) -> list[AuditEntry]:
        from flowsint_crypto_compliance.storage.db_models import EccfAuditLogEntry

        db = _session()
        try:
            rows = (
                db.query(EccfAuditLogEntry)
                .filter(EccfAuditLogEntry.evidence_id == evidence_id)
                .order_by(EccfAuditLogEntry.entry_id.asc())
                .all()
            )
            return [
                AuditEntry(
                    entry_id=r.entry_id,
                    evidence_id=r.evidence_id,
                    action=AuditAction(r.action),
                    actor=r.actor,
                    timestamp=r.timestamp or datetime.now(timezone.utc),
                    details=dict(r.details or {}),
                )
                for r in rows
            ]
        finally:
            db.close()

    def all_entries(self) -> list[AuditEntry]:
        from flowsint_crypto_compliance.storage.db_models import EccfAuditLogEntry

        db = _session()
        try:
            rows = db.query(EccfAuditLogEntry).order_by(EccfAuditLogEntry.entry_id.asc()).all()
            return [
                AuditEntry(
                    entry_id=r.entry_id,
                    evidence_id=r.evidence_id,
                    action=AuditAction(r.action),
                    actor=r.actor,
                    timestamp=r.timestamp or datetime.now(timezone.utc),
                    details=dict(r.details or {}),
                )
                for r in rows
            ]
        finally:
            db.close()

    def verify_integrity(self, evidence_id: str | None = None) -> dict[str, Any]:
        """Verify hash chain for one evidence_id or the global chain."""
        from flowsint_crypto_compliance.storage.db_models import EccfAuditLogEntry

        db = _session()
        try:
            q = db.query(EccfAuditLogEntry).order_by(EccfAuditLogEntry.entry_id.asc())
            if evidence_id:
                q = q.filter(EccfAuditLogEntry.evidence_id == evidence_id)
            rows = q.all()
            entries = [
                {
                    "evidence_id": r.evidence_id,
                    "action": r.action,
                    "actor": r.actor,
                    "timestamp": r.timestamp,
                    "details": r.details or {},
                    "prev_hash": r.prev_hash,
                    "entry_hash": r.entry_hash,
                }
                for r in rows
            ]
            return verify_chain(entries)
        finally:
            db.close()
