"""RFC-0017 Ch.6 — evidence repository with dedup and optional KG bridge."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import Evidence, TrustLevel
from flowsint_crypto_compliance.platform.v2.eccf.constraints import assert_not_forbidden
from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFRecord, EvidenceLifecycle
from flowsint_crypto_compliance.platform.v2.knowledge_store import get_knowledge_graph_store


class ECCFRepository:
    """In-memory ECCF store with optional KnowledgeGraphStore bridge."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_id: dict[str, ECCFRecord] = {}
        self._by_hash: dict[str, str] = {}

    def get(self, evidence_id: str) -> ECCFRecord | None:
        with self._lock:
            return self._by_id.get(evidence_id)

    def find_by_hash(self, content_hash: str, tenant_id: str) -> ECCFRecord | None:
        with self._lock:
            eid = self._by_hash.get(f"{tenant_id}:{content_hash}")
            if eid:
                return self._by_id.get(eid)
        return None

    def store(
        self,
        record: ECCFRecord,
        *,
        bridge_kg: bool = True,
    ) -> tuple[ECCFRecord, bool]:
        """
        Store evidence record. Returns (record, deduplicated).
        Deduplicates by (tenant_id, content_hash).
        """
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

        with self._lock:
            self._by_id[record.evidence_id] = record
            self._by_hash[f"{record.tenant_id}:{record.content_hash}"] = record.evidence_id

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
            return None

    def list_all(self) -> list[ECCFRecord]:
        with self._lock:
            return list(self._by_id.values())

    def update_metadata_only(self, evidence_id: str, **fields: Any) -> ECCFRecord:
        """Update non-content metadata (lifecycle, archived) — content is immutable."""
        immutable_fields = {"content_hash", "payload", "size_bytes", "mime_type"}
        if immutable_fields & set(fields):
            assert_not_forbidden("modify_content")
        with self._lock:
            rec = self._by_id.get(evidence_id)
            if rec is None:
                raise KeyError(evidence_id)
            if rec.immutable and immutable_fields & set(fields):
                raise ValueError("Cannot modify immutable evidence content")
            for key, val in fields.items():
                if key == "lifecycle" and isinstance(val, EvidenceLifecycle):
                    setattr(rec, key, val)
                elif key == "lifecycle" and isinstance(val, str):
                    rec.lifecycle = EvidenceLifecycle(val)
                elif hasattr(rec, key) and key not in ("content_hash", "payload", "size_bytes", "mime_type"):
                    setattr(rec, key, val)
            rec.updated_at = datetime.now(timezone.utc)
            return rec


_repo: ECCFRepository | Any | None = None


def get_eccf_repository() -> ECCFRepository:
    global _repo
    if _repo is None:
        from flowsint_crypto_compliance.feature_flags import eccf_postgres_persistence_enabled

        if eccf_postgres_persistence_enabled():
            try:
                from flowsint_crypto_compliance.platform.v2.eccf.postgres_store import (
                    PostgresECCFRepository,
                )

                _repo = PostgresECCFRepository()
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "ECCF Postgres persistence unavailable — falling back to in-memory"
                )
                _repo = ECCFRepository()
        else:
            _repo = ECCFRepository()
    return _repo


def reset_eccf_repository() -> None:
    """Test helper."""
    global _repo
    _repo = None
